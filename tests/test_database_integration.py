from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from onetech_ao.config import Settings
from onetech_ao.database import Database
from onetech_ao.haicop import DocumentRecord, TenderRecord


TEST_TENDER_ID = "Tender-999999999"
TEST_DOCUMENT_URL = "https://www.marchespublics.gov.tn/storage/tender/test-python-upsert.pdf"


@pytest.mark.integration
def test_terminal_daily_run_keeps_its_first_completion_timestamp() -> None:
    settings = Settings.load()
    database = Database(settings)
    run = database.start_daily_run(
        run_key=f"pytest:terminal-daily-run:{uuid4().hex}",
        trigger="test",
        parameters={"test": "completion_timestamp"},
    )
    run_id = int(run["id"])

    try:
        first = database.update_daily_run(run_id, status="terminee", terminal=True)
        second = database.update_daily_run(run_id, status="terminee", terminal=True)

        assert first["terminee_le"] is not None
        assert second["terminee_le"] == first["terminee_le"]
    finally:
        with database.connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM executions_quotidiennes WHERE id = %s", (run_id,))


@pytest.mark.integration
def test_daily_delivery_reservation_allows_one_send_per_recipient() -> None:
    settings = Settings.load()
    database = Database(settings)
    run = database.start_daily_run(
        run_key=f"pytest:daily-delivery:{uuid4().hex}",
        trigger="test",
        parameters={"test": "delivery_reservation"},
    )
    run_id = int(run["id"])
    recipient_hash = "a" * 64
    first_digest = "b" * 64
    changed_digest = "c" * 64

    try:
        first = database.reserve_delivery(
            run_id=run_id,
            channel="mailpit",
            recipient_hash=recipient_hash,
            digest_sha256=first_digest,
        )
        assert first["claimed"] is True
        sent = database.finish_delivery(int(first["id"]), status="envoyee")

        retried = database.reserve_delivery(
            run_id=run_id,
            channel="mailpit",
            recipient_hash=recipient_hash,
            digest_sha256=changed_digest,
        )
        assert retried["claimed"] is False
        assert retried["id"] == sent["id"]
        assert retried["statut"] == "envoyee"
        assert retried["digest_sha256"] == first_digest
    finally:
        with database.connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM executions_quotidiennes WHERE id = %s", (run_id,))


@pytest.mark.integration
def test_connection_and_idempotent_upserts_leave_no_test_data() -> None:
    settings = Settings.load()
    database = Database(settings)
    state = database.check_connection()
    assert state["database"] == settings.postgres_db

    collection_id = database.start_collection({"test": "pytest_upsert"})
    tunis = ZoneInfo("Africa/Tunis")
    first = TenderRecord(
        tender_id=TEST_TENDER_ID,
        plan_id="PLAN-PYTEST",
        organization="Organisme test Python",
        title="Version initiale",
        publication_date=datetime(2026, 8, 8, 9, 0, tzinfo=tunis),
        deadline=datetime(2026, 9, 8, 10, 0, tzinfo=tunis),
        reserved_sme=False,
        detail_url=(
            "https://www.marchespublics.gov.tn/fr/appels-doffres/"
            f"{TEST_TENDER_ID}"
        ),
        raw_payload={"version": 1},
    )
    second = TenderRecord(
        tender_id=TEST_TENDER_ID,
        plan_id="PLAN-PYTEST",
        organization="Organisme test Python mis à jour",
        title="Version mise à jour",
        publication_date=datetime(2026, 8, 8, 9, 0, tzinfo=tunis),
        deadline=datetime(2026, 9, 9, 10, 0, tzinfo=tunis),
        reserved_sme=True,
        detail_url=first.detail_url,
        raw_payload={"version": 2, "champ_non_modele": "conservé"},
        detail_fields={"Procédure": "ouverte"},
    )
    first_document = DocumentRecord(
        tender_id=TEST_TENDER_ID,
        label="Document initial",
        document_type="pdf",
        url=TEST_DOCUMENT_URL,
        raw_metadata={"version": 1},
    )
    second_document = DocumentRecord(
        tender_id=TEST_TENDER_ID,
        label="Document mis à jour",
        document_type="pdf",
        url=TEST_DOCUMENT_URL,
        raw_metadata={"version": 2},
    )

    try:
        with database.connect() as connection:
            assert database.upsert_tender(connection, first, collection_id) is True
            assert database.upsert_tender(connection, second, collection_id) is False
            assert database.upsert_document(connection, first_document) is True
            assert database.upsert_document(connection, second_document) is False

        database.finish_collection(collection_id, received=2, inserted=1, updated=1)

        targeted_documents = database.documents_to_process(
            limit=10,
            tender_id=TEST_TENDER_ID,
        )
        assert len(targeted_documents) == 1
        assert targeted_documents[0]["tender_id"] == TEST_TENDER_ID
        assert database.documents_to_process(
            limit=10,
            tender_id="Tender-DOES-NOT-EXIST",
        ) == []

        first_analysis = database.save_analysis(
            tender_id=TEST_TENDER_ID,
            status="complete",
            scores={
                "adequation": 20,
                "delai": 20,
                "administratif": 15,
                "risque": 15,
            },
            decision="GO",
            engine="pytest",
            model="fake-model",
            fiche_path="fiches/pytest.md",
            fiche_markdown="# fiche pytest",
            fiche_sha256="a" * 64,
            context_sha256="b" * 64,
            profile_sha256="c" * 64,
            sources={"test": True},
            context_snapshot={"test": True},
            rubric_version="pytest-v1",
            evaluation_date=date(2026, 8, 10),
        )
        second_analysis = database.save_analysis(
            tender_id=TEST_TENDER_ID,
            status="complete",
            scores={
                "adequation": 20,
                "delai": 20,
                "administratif": 15,
                "risque": 15,
            },
            decision="GO",
            engine="pytest",
            model="fake-model",
            fiche_path="fiches/pytest.md",
            fiche_markdown="# fiche pytest",
            fiche_sha256="a" * 64,
            context_sha256="b" * 64,
            profile_sha256="c" * 64,
            sources={"test": True},
            context_snapshot={"test": True},
            rubric_version="pytest-v1",
            evaluation_date=date(2026, 8, 10),
        )
        assert first_analysis["id"] == second_analysis["id"]
        assert first_analysis["score_total"] == 70

        with database.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    titre,
                    donnees_brutes ->> 'champ_non_modele' AS champ_brut,
                    champs_details ->> 'Procédure' AS procedure
                FROM appels_offres
                WHERE tender_id = %s
                """,
                (TEST_TENDER_ID,),
            )
            tender_row = cursor.fetchone()
            assert tender_row == {
                "titre": "Version mise à jour",
                "champ_brut": "conservé",
                "procedure": "ouverte",
            }

            cursor.execute(
                "SELECT count(*) AS total, max(libelle) AS libelle "
                "FROM documents_ao WHERE tender_id = %s",
                (TEST_TENDER_ID,),
            )
            assert cursor.fetchone() == {"total": 1, "libelle": "Document mis à jour"}

            cursor.execute(
                """
                SELECT statut, nb_recus, nb_inseres, nb_mis_a_jour
                FROM collectes_haicop
                WHERE id = %s
                """,
                (collection_id,),
            )
            assert cursor.fetchone() == {
                "statut": "terminee",
                "nb_recus": 2,
                "nb_inseres": 1,
                "nb_mis_a_jour": 1,
            }

            cursor.execute(
                "SELECT count(*) AS total FROM analyses_ao WHERE tender_id = %s",
                (TEST_TENDER_ID,),
            )
            assert cursor.fetchone() == {"total": 1}
    finally:
        with database.connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM appels_offres WHERE tender_id = %s", (TEST_TENDER_ID,))
            cursor.execute("DELETE FROM collectes_haicop WHERE id = %s", (collection_id,))
