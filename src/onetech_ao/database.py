"""Accès PostgreSQL et UPSERT idempotents."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import Settings
from .haicop import DocumentRecord, TenderRecord


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(**self.settings.database_kwargs, row_factory=dict_row)

    def check_connection(self) -> dict[str, Any]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database() AS database,
                    current_user AS utilisateur,
                    current_setting('server_version') AS version
                """
            )
            result = cursor.fetchone()
            if result is None:
                raise RuntimeError("PostgreSQL n'a retourné aucun état")
            return result

    def counts(self) -> dict[str, int]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT count(*) FROM appels_offres)::integer AS appels_offres,
                    (SELECT count(*) FROM documents_ao)::integer AS documents_ao,
                    (SELECT count(*) FROM collectes_haicop)::integer AS collectes_haicop
                """
            )
            row = cursor.fetchone()
            return dict(row or {})

    def start_collection(self, parameters: dict[str, Any]) -> int:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO collectes_haicop (source, statut, parametres)
                VALUES ('haicop', 'en_cours', %s)
                RETURNING id
                """,
                (Jsonb(parameters),),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Impossible de créer le journal de collecte")
            return int(row["id"])

    def finish_collection(
        self,
        collection_id: int,
        received: int,
        inserted: int,
        updated: int,
        warning: str | None = None,
    ) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE collectes_haicop
                SET statut = 'terminee',
                    terminee_le = clock_timestamp(),
                    nb_recus = %s,
                    nb_inseres = %s,
                    nb_mis_a_jour = %s,
                    erreur = %s
                WHERE id = %s
                """,
                (received, inserted, updated, warning, collection_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Journal de collecte introuvable à la clôture")

    def fail_collection(self, collection_id: int, error: str) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE collectes_haicop
                SET statut = 'echec',
                    terminee_le = clock_timestamp(),
                    erreur = %s
                WHERE id = %s
                """,
                (error, collection_id),
            )

    @staticmethod
    def upsert_tender(
        connection: psycopg.Connection[dict[str, Any]],
        tender: TenderRecord,
        collection_id: int,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO appels_offres (
                    tender_id,
                    source,
                    plan_id,
                    organisme,
                    titre,
                    date_publication,
                    date_limite,
                    reserve_pme,
                    url_detail,
                    champs_details,
                    donnees_brutes,
                    collecte_id
                ) VALUES (
                    %s, 'haicop', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (tender_id) DO UPDATE SET
                    source = EXCLUDED.source,
                    plan_id = EXCLUDED.plan_id,
                    organisme = EXCLUDED.organisme,
                    titre = EXCLUDED.titre,
                    date_publication = EXCLUDED.date_publication,
                    date_limite = EXCLUDED.date_limite,
                    reserve_pme = EXCLUDED.reserve_pme,
                    url_detail = EXCLUDED.url_detail,
                    champs_details = CASE
                        WHEN EXCLUDED.champs_details = '{}'::jsonb
                            THEN appels_offres.champs_details
                        ELSE EXCLUDED.champs_details
                    END,
                    donnees_brutes = EXCLUDED.donnees_brutes,
                    collecte_id = EXCLUDED.collecte_id,
                    derniere_collecte_le = clock_timestamp()
                RETURNING (xmax = 0) AS insere
                """,
                (
                    tender.tender_id,
                    tender.plan_id,
                    tender.organization,
                    tender.title,
                    tender.publication_date,
                    tender.deadline,
                    tender.reserved_sme,
                    tender.detail_url,
                    Jsonb(tender.detail_fields),
                    Jsonb(tender.raw_payload),
                    collection_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"UPSERT sans résultat pour {tender.tender_id}")
            return bool(row["insere"])

    @staticmethod
    def upsert_document(
        connection: psycopg.Connection[dict[str, Any]],
        document: DocumentRecord,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents_ao (
                    tender_id,
                    libelle,
                    type_document,
                    url,
                    metadonnees_brutes
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tender_id, url) DO UPDATE SET
                    libelle = EXCLUDED.libelle,
                    type_document = EXCLUDED.type_document,
                    metadonnees_brutes = EXCLUDED.metadonnees_brutes,
                    derniere_collecte_le = clock_timestamp()
                RETURNING (xmax = 0) AS insere
                """,
                (
                    document.tender_id,
                    document.label,
                    document.document_type,
                    document.url,
                    Jsonb(document.raw_metadata),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"UPSERT document sans résultat pour {document.tender_id}")
            return bool(row["insere"])

    def recent_collections(self, limit: int = 5) -> list[dict[str, Any]]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    statut,
                    demarree_le,
                    terminee_le,
                    nb_recus,
                    nb_inseres,
                    nb_mis_a_jour,
                    erreur,
                    parametres
                FROM collectes_haicop
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())

    def list_open(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    tender_id,
                    organisme,
                    titre,
                    date_publication,
                    date_limite,
                    reserve_pme,
                    url_detail,
                    statut_echeance
                FROM v_appels_offres_ouverts
                ORDER BY date_publication DESC NULLS LAST, tender_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())

    def integrity_report(self) -> dict[str, int]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (
                        SELECT count(*)
                        FROM (
                            SELECT tender_id
                            FROM appels_offres
                            GROUP BY tender_id
                            HAVING count(*) > 1
                        ) AS doublons_ao
                    )::integer AS doublons_appels_offres,
                    (
                        SELECT count(*)
                        FROM (
                            SELECT tender_id, url
                            FROM documents_ao
                            GROUP BY tender_id, url
                            HAVING count(*) > 1
                        ) AS doublons_documents
                    )::integer AS doublons_documents,
                    (
                        SELECT count(*)
                        FROM appels_offres
                        WHERE donnees_brutes = '{}'::jsonb
                    )::integer AS payloads_bruts_vides
                """
            )
            return dict(cursor.fetchone() or {})
