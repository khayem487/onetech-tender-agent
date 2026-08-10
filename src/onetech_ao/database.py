"""Accès PostgreSQL et UPSERT idempotents."""

from __future__ import annotations

from datetime import date
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
                    (SELECT count(*) FROM collectes_haicop)::integer AS collectes_haicop,
                    (SELECT count(*) FROM analyses_ao)::integer AS analyses_ao
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

    def documents_to_process(
        self,
        limit: int = 50,
        retry_errors: bool = False,
        reprocess_extracted: bool = False,
        tender_id: str | None = None,
    ) -> list[dict[str, Any]]:
        statuses = ["a_traiter"]
        if retry_errors:
            statuses.append("echec")
        if reprocess_extracted:
            statuses.append("extrait")
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    tender_id,
                    url,
                    type_document,
                    chemin_local,
                    empreinte_sha256
                FROM documents_ao
                WHERE statut_traitement = ANY(%s)
                  AND (%s::text IS NULL OR tender_id = %s::text)
                ORDER BY id
                LIMIT %s
                """,
                (statuses, tender_id, tender_id, limit),
            )
            return list(cursor.fetchall())

    def save_document_processing(
        self,
        document_id: int,
        relative_path: str,
        sha256: str,
        size_bytes: int,
        mime_type: str | None,
        detected_type: str,
        extracted_text: str | None,
        status: str,
    ) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents_ao
                SET chemin_local = %s,
                    empreinte_sha256 = %s,
                    taille_octets = %s,
                    mime_type = %s,
                    type_document = %s,
                    texte_extrait = %s,
                    statut_traitement = %s,
                    erreur_traitement = NULL,
                    traite_le = clock_timestamp()
                WHERE id = %s
                """,
                (
                    relative_path,
                    sha256,
                    size_bytes,
                    mime_type,
                    detected_type,
                    extracted_text,
                    status,
                    document_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Document introuvable pendant la sauvegarde")

    def fail_document_processing(
        self,
        document_id: int,
        error: str,
        relative_path: str | None = None,
        sha256: str | None = None,
        size_bytes: int | None = None,
        mime_type: str | None = None,
        detected_type: str | None = None,
    ) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents_ao
                SET chemin_local = COALESCE(%s, chemin_local),
                    empreinte_sha256 = COALESCE(%s, empreinte_sha256),
                    taille_octets = COALESCE(%s, taille_octets),
                    mime_type = COALESCE(%s, mime_type),
                    type_document = COALESCE(%s, type_document),
                    statut_traitement = 'echec',
                    erreur_traitement = %s,
                    traite_le = clock_timestamp()
                WHERE id = %s
                """,
                (
                    relative_path,
                    sha256,
                    size_bytes,
                    mime_type,
                    detected_type,
                    error,
                    document_id,
                ),
            )

    def document_processing_counts(self) -> dict[str, int]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    count(*)::integer AS total,
                    count(*) FILTER (WHERE statut_traitement = 'a_traiter')::integer
                        AS a_traiter,
                    count(*) FILTER (WHERE statut_traitement = 'extrait')::integer
                        AS extraits,
                    count(*) FILTER (WHERE statut_traitement = 'sans_texte')::integer
                        AS sans_texte,
                    count(*) FILTER (WHERE statut_traitement = 'non_supporte')::integer
                        AS non_supportes,
                    count(*) FILTER (WHERE statut_traitement = 'echec')::integer
                        AS echecs
                FROM documents_ao
                """
            )
            return dict(cursor.fetchone() or {})

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

    def get_analysis_context(self, tender_id: str) -> dict[str, Any] | None:
        """Retourne les faits officiels et tous les documents d'un AO."""
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
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
                    premiere_collecte_le,
                    derniere_collecte_le,
                    mise_a_jour_le
                FROM appels_offres
                WHERE tender_id = %s
                """,
                (tender_id,),
            )
            tender = cursor.fetchone()
            if tender is None:
                return None

            cursor.execute(
                """
                SELECT
                    id,
                    tender_id,
                    libelle,
                    type_document,
                    url,
                    chemin_local,
                    texte_extrait,
                    empreinte_sha256,
                    mime_type,
                    taille_octets,
                    statut_traitement,
                    erreur_traitement,
                    traite_le,
                    premiere_collecte_le,
                    derniere_collecte_le
                FROM documents_ao
                WHERE tender_id = %s
                ORDER BY id
                """,
                (tender_id,),
            )
            return {
                "appel_offres": dict(tender),
                "documents": list(cursor.fetchall()),
            }

    def save_analysis(
        self,
        *,
        tender_id: str,
        status: str,
        scores: dict[str, int],
        decision: str,
        engine: str,
        model: str | None,
        fiche_path: str,
        fiche_markdown: str,
        fiche_sha256: str,
        context_sha256: str,
        profile_sha256: str | None,
        sources: dict[str, Any],
        context_snapshot: dict[str, Any],
        rubric_version: str,
        evaluation_date: date,
    ) -> dict[str, Any]:
        """Enregistre une fiche idempotente sans modifier les faits HAICOP."""
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analyses_ao (
                    tender_id,
                    statut,
                    score_adequation,
                    score_delai,
                    score_administratif,
                    score_risque,
                    decision,
                    moteur,
                    modele,
                    fiche_chemin,
                    fiche_markdown,
                    fiche_sha256,
                    contexte_sha256,
                    profil_sha256,
                    sources,
                    contexte_snapshot,
                    bareme_version,
                    date_evaluation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (tender_id, contexte_sha256)
                DO UPDATE SET
                    statut = EXCLUDED.statut,
                    score_adequation = EXCLUDED.score_adequation,
                    score_delai = EXCLUDED.score_delai,
                    score_administratif = EXCLUDED.score_administratif,
                    score_risque = EXCLUDED.score_risque,
                    decision = EXCLUDED.decision,
                    moteur = EXCLUDED.moteur,
                    modele = EXCLUDED.modele,
                    fiche_chemin = EXCLUDED.fiche_chemin,
                    fiche_markdown = EXCLUDED.fiche_markdown,
                    fiche_sha256 = EXCLUDED.fiche_sha256,
                    profil_sha256 = EXCLUDED.profil_sha256,
                    sources = EXCLUDED.sources,
                    contexte_snapshot = EXCLUDED.contexte_snapshot,
                    bareme_version = EXCLUDED.bareme_version,
                    date_evaluation = EXCLUDED.date_evaluation,
                    generee_le = clock_timestamp()
                RETURNING
                    id,
                    tender_id,
                    statut,
                    score_adequation,
                    score_delai,
                    score_administratif,
                    score_risque,
                    score_total,
                    decision,
                    fiche_chemin,
                    fiche_sha256,
                    contexte_sha256,
                    profil_sha256,
                    bareme_version,
                    date_evaluation,
                    generee_le,
                    (xmax = 0) AS inseree
                """,
                (
                    tender_id,
                    status,
                    scores["adequation"],
                    scores["delai"],
                    scores["administratif"],
                    scores["risque"],
                    decision,
                    engine,
                    model,
                    fiche_path,
                    fiche_markdown,
                    fiche_sha256,
                    context_sha256,
                    profile_sha256,
                    Jsonb(sources),
                    Jsonb(context_snapshot),
                    rubric_version,
                    evaluation_date,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("PostgreSQL n'a retourné aucune analyse")
            return dict(row)

    def latest_analysis(self, tender_id: str) -> dict[str, Any] | None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM v_dernieres_analyses_ao
                WHERE tender_id = %s
                """,
                (tender_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def analysis_digest(
        self,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    tender_id,
                    organisme,
                    titre,
                    date_limite,
                    url_detail,
                    statut,
                    score_adequation,
                    score_delai,
                    score_administratif,
                    score_risque,
                    score_total,
                    decision,
                    fiche_chemin,
                    fiche_sha256,
                    generee_le
                FROM v_dernieres_analyses_ao
                WHERE (%s OR date_limite IS NULL OR date_limite >= clock_timestamp())
                ORDER BY
                    CASE decision
                        WHEN 'GO' THEN 3
                        WHEN 'A_DISCUTER' THEN 2
                        ELSE 1
                    END DESC,
                    score_total DESC,
                    date_limite ASC NULLS LAST,
                    generee_le DESC
                LIMIT %s
                """,
                (include_expired, limit),
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
