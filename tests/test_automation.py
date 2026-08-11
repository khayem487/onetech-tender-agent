from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from onetech_ao.analysis import _profile
from onetech_ao.automation import DailyAutomation, relevance, render_digest
from onetech_ao.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        postgres_db="test",
        postgres_user="test",
        postgres_password="secret",
        project_root=tmp_path,
        document_root=tmp_path / "data" / "documents",
    )


def test_validated_v1_profile_is_accepted_without_inventing_unknowns(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "profil_entreprise.md").write_text(
        "# OneTech\n<!-- ONETECH_PROFILE_STATUS: VALIDATED_V1 -->\n"
        "Effectif: Non renseigné\n",
        encoding="utf-8",
    )

    profile = _profile(_settings(tmp_path))

    assert profile["complet"] is True
    assert profile["validation"] == "VALIDATED_V1"
    assert "Non renseigné" in profile["contenu"]
    assert "avant une soumission réelle" in profile["avertissement"]


def test_relevance_prefers_it_and_penalizes_out_of_scope() -> None:
    config = {
        "positive_keywords": ["informatique", "data", "cloud"],
        "negative_keywords": ["construction", "matériel médical"],
    }
    score, reasons = relevance(
        {
            "organisme": "Agence numérique",
            "titre": "Plateforme data cloud informatique",
            "champs_details": {},
            "extrait_documents": "",
        },
        config,
    )
    out_score, _ = relevance(
        {
            "organisme": "Hôpital",
            "titre": "Construction et matériel médical",
            "champs_details": {},
            "extrait_documents": "",
        },
        config,
    )

    assert score == 9
    assert "+ informatique" in reasons
    assert out_score < 0


def test_relevance_rejects_pure_equipment_without_digital_evidence() -> None:
    score, reasons = relevance(
        {
            "organisme": "Agence de formation",
            "titre": "Acquisition d'équipements pour réseau de gaz naturel",
            "champs_details": {},
            "extrait_documents": "Fourniture de matériels de formation.",
        },
        {"positive_keywords": ["réseau"], "negative_keywords": ["gaz naturel"]},
    )

    assert score < 0
    assert "- fourniture/matériel sans composante numérique explicite" in reasons


def test_render_digest_is_stable_when_the_run_is_terminal() -> None:
    run = {
        "id": 8,
        "cle_execution": "daily:2026-08-11",
        "terminee_le": datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc),
    }

    first = render_digest(run, [], [])
    second = render_digest(run, [], [])

    assert first == second


class _DailyRunDatabase:
    def __init__(self) -> None:
        self.run = {
            "id": 9,
            "cle_execution": "daily:2026-08-11",
            "statut": "analyse",
            "demarree_le": datetime(2026, 8, 11, 7, 59, tzinfo=timezone.utc),
            "terminee_le": None,
        }

    def get_daily_run(self, run_id: int) -> dict[str, object] | None:
        assert run_id == 9
        return dict(self.run)

    def reconcile_daily_candidates(self, run_id: int) -> list[dict[str, object]]:
        assert run_id == 9
        return []

    def update_daily_run(self, run_id: int, **changes: object) -> dict[str, object]:
        assert run_id == 9
        self.run["statut"] = changes["status"]
        if changes.get("terminal") and self.run["terminee_le"] is None:
            self.run["terminee_le"] = datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc)
        return dict(self.run)


def test_daily_finish_reuses_the_same_digest_hash_on_retry(tmp_path: Path) -> None:
    database = _DailyRunDatabase()
    automation = DailyAutomation(_settings(tmp_path), database=database)  # type: ignore[arg-type]

    first = automation.finish(9)
    second = automation.finish(9)

    assert first["digest"]["sha256"] == second["digest"]["sha256"]
    assert first["execution"]["terminee_le"] == second["execution"]["terminee_le"]


def test_render_digest_contains_decision_and_failure() -> None:
    run = {"id": 7, "cle_execution": "daily:2026-08-10"}
    successful = [
        {
            "tender_id": "Tender-42",
            "titre": "Plateforme data",
            "organisme": "Agence",
            "decision": "GO",
            "score_total": 78,
            "date_limite": datetime(2026, 9, 1, tzinfo=timezone.utc),
            "fiche_chemin": "fiches/tender-42.md",
            "url_detail": "https://example.test/Tender-42",
        }
    ]
    failed = [{"tender_id": "Tender-43", "erreur": "document illisible"}]

    digest = render_digest(run, successful, failed)

    assert "Tender-42" in digest
    assert "**GO** — 78/100" in digest
    assert "Tender-43 : document illisible" in digest
