from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from onetech_ao.analysis import (
    AnalysisContextError,
    build_analysis_context,
    classify_document,
    context_fingerprint,
    export_analysis_context,
    normalize_tender_id,
    record_analysis,
)
from onetech_ao.config import Settings


class FakeDatabase:
    def __init__(self, bundle: dict[str, Any] | None) -> None:
        self.bundle = bundle
        self.requested: str | None = None
        self.saved: dict[str, Any] | None = None

    def get_analysis_context(self, tender_id: str) -> dict[str, Any] | None:
        self.requested = tender_id
        return self.bundle

    def save_analysis(self, **kwargs: Any) -> dict[str, Any]:
        self.saved = kwargs
        return {
            "id": 7,
            "tender_id": kwargs["tender_id"],
            "score_total": sum(kwargs["scores"].values()),
            "decision": kwargs["decision"],
            "fiche_chemin": kwargs["fiche_path"],
            "inseree": True,
        }


def _settings(tmp_path: Path, *, incomplete_profile: bool = True) -> Settings:
    profile_dir = tmp_path / "config"
    profile_dir.mkdir()
    profile_suffix = (
        "- [à compléter avec Makram]\n"
        if incomplete_profile
        else "- Profil validé avec l'encadrant\n"
    )
    (profile_dir / "profil_entreprise.md").write_text(
        "# One Tech\n\n- Développement logiciel\n" + profile_suffix,
        encoding="utf-8",
    )
    return Settings(
        postgres_db="test",
        postgres_user="test",
        postgres_password="secret",
        project_root=tmp_path,
        document_root=tmp_path / "data" / "documents",
    )


def _bundle(status: str = "extrait") -> dict[str, Any]:
    return {
        "appel_offres": {
            "tender_id": "Tender-42",
            "source": "haicop",
            "organisme": "Agence numérique",
            "titre": "Plateforme de données",
            "date_limite": datetime(2026, 9, 1, 10, tzinfo=timezone.utc),
            "url_detail": "https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-42",
            "champs_details": {"Procédure": "ouverte"},
            "donnees_brutes": {"id": 42},
        },
        "documents": [
            {
                "id": 9,
                "libelle": "Cahier des charges",
                "type_document": "pdf",
                "statut_traitement": status,
                "url": "https://www.marchespublics.gov.tn/storage/tender/cdc.pdf",
                "chemin_local": "data/documents/Tender-42/9-cdc.pdf",
                "empreinte_sha256": "a" * 64,
                "taille_octets": 1234,
                "texte_extrait": (
                    "--- PAGE 1 ---\nDate limite : 1 septembre 2026"
                    if status == "extrait"
                    else None
                ),
                "erreur_traitement": None,
            }
        ],
    }


def test_normalize_tender_id_accepts_id_and_public_url() -> None:
    assert normalize_tender_id("Tender-103283") == "Tender-103283"
    assert (
        normalize_tender_id(
            "https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-103283/"
        )
        == "Tender-103283"
    )
    with pytest.raises(AnalysisContextError):
        normalize_tender_id("103283")


def test_context_contains_database_text_profile_and_complete_coverage(
    tmp_path: Path,
) -> None:
    database = FakeDatabase(_bundle())
    context = build_analysis_context(_settings(tmp_path), database, "Tender-42")

    assert database.requested == "Tender-42"
    assert context["appel_offres"]["titre"] == "Plateforme de données"
    assert "--- PAGE 1 ---" in context["documents"][0]["texte_extrait"]
    assert context["couverture_documents"]["analyse_partielle"] is False
    assert context["profil_entreprise"]["empreinte_sha256"]
    assert context["profil_entreprise"]["avertissement"]


def test_context_marks_unreadable_document_as_partial(tmp_path: Path) -> None:
    context = build_analysis_context(
        _settings(tmp_path),
        FakeDatabase(_bundle("sans_texte")),
        "Tender-42",
    )
    coverage = context["couverture_documents"]
    assert coverage["analyse_partielle"] is True
    assert coverage["extraits"] == 0
    assert any("scanné" in reason for reason in coverage["raisons"])
    assert any("Aucun document" in reason for reason in coverage["raisons"])


def test_notice_only_context_is_partial_even_when_text_is_extracted(tmp_path: Path) -> None:
    bundle = _bundle()
    bundle["documents"][0]["libelle"] = "Avis d’appel d’offres"
    context = build_analysis_context(_settings(tmp_path), FakeDatabase(bundle), "Tender-42")

    assert context["documents"][0]["role_document"] == "avis"
    assert context["couverture_documents"]["analyse_partielle"] is True
    assert context["couverture_documents"]["documents_de_fond_extraits"] == 0
    assert any("Aucun cahier" in reason for reason in context["couverture_documents"]["raisons"])


def test_document_classification_does_not_mistake_notice_mentions_for_cahier() -> None:
    assert classify_document("Avis d’appel d’offres", "Consulter le cahier des charges") == "avis"
    assert classify_document("cahier des charges", "contenu") == "dossier_de_fond"


def test_export_is_stable_and_stays_in_workspace(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    database = FakeDatabase(_bundle())
    first, context = export_analysis_context(settings, database, "Tender-42")
    second, _ = export_analysis_context(settings, database, "Tender-42")

    exported = tmp_path / first.fichier_contexte
    assert exported.is_file()
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["appel_offres"]["tender_id"] == "Tender-42"
    assert first.empreinte_sha256 == second.empreinte_sha256
    assert first.empreinte_sha256 == context_fingerprint(context)

    with pytest.raises(AnalysisContextError):
        export_analysis_context(
            settings,
            database,
            "Tender-42",
            output=tmp_path.parent / "outside.json",
        )


def test_fingerprint_ignores_operational_metadata_but_detects_source_change(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    first_bundle = _bundle()
    first_bundle["appel_offres"].update(
        {
            "derniere_collecte_le": "2026-08-08T07:00:00Z",
            "mise_a_jour_le": "2026-08-08T07:00:00Z",
        }
    )
    first_bundle["documents"][0].update(
        {
            "id": 9,
            "chemin_local": "data/documents/old.pdf",
            "derniere_collecte_le": "2026-08-08T07:00:00Z",
        }
    )
    second_bundle = copy.deepcopy(first_bundle)
    second_bundle["appel_offres"]["derniere_collecte_le"] = "2026-08-10T09:00:00Z"
    second_bundle["appel_offres"]["mise_a_jour_le"] = "2026-08-10T09:00:00Z"
    second_bundle["documents"][0]["id"] = 999
    second_bundle["documents"][0]["chemin_local"] = "D:/moved/document.pdf"

    first = build_analysis_context(settings, FakeDatabase(first_bundle), "Tender-42")
    second = build_analysis_context(settings, FakeDatabase(second_bundle), "Tender-42")
    assert context_fingerprint(first) == context_fingerprint(second)

    second["documents"][0]["texte_extrait"] += "\nNouvelle clause"
    assert context_fingerprint(first) != context_fingerprint(second)


def test_missing_tender_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(AnalysisContextError, match="absent de PostgreSQL"):
        build_analysis_context(_settings(tmp_path), FakeDatabase(None), "Tender-404")


def _fiche(
    tmp_path: Path,
    complete: bool = True,
    score: int = 70,
    decision: str = "GO",
    partial_header: bool = False,
) -> Path:
    component_scores = (20, 20, 15, 15) if score == 70 else (10, 10, 10, 10)
    sections = [
        "# 📋 FICHE D'ANALYSE — Test Tender-42",
        (
            "*Source : Tender-42 · ⚠️ Analyse partielle*"
            if partial_header
            else "*Source : Tender-42*"
        ),
        f"**Décision recommandée : {decision}**",
        "| Critère | Note /25 |",
        "|---|---:|",
        f"| Adéquation compétences | {component_scores[0]} |",
        f"| Faisabilité délai | {component_scores[1]} |",
        f"| Charge administrative | {component_scores[2]} |",
        f"| Niveau de risque | {component_scores[3]} |",
        f"| **TOTAL** | **{score}/100** |",
    ]
    last = 10 if complete else 9
    sections.extend(f"## {number}. Section {number}" for number in range(1, last))
    path = tmp_path / "fiches" / "test.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return path


def test_record_analysis_validates_and_saves_separately(tmp_path: Path) -> None:
    settings = _settings(tmp_path, incomplete_profile=False)
    database = FakeDatabase(_bundle())
    context_hash = context_fingerprint(build_analysis_context(settings, database, "Tender-42"))
    result = record_analysis(
        settings,
        database,  # type: ignore[arg-type]
        reference="Tender-42",
        fiche=_fiche(tmp_path),
        status="complete",
        adequation=20,
        deadline=20,
        administrative=15,
        risk=15,
        decision="GO",
        context_sha256=context_hash,
        model="test-model",
    )

    assert result["scores"]["total"] == 70
    assert result["decision"] == "GO"
    assert database.saved is not None
    assert database.saved["context_sha256"]
    assert database.saved["fiche_sha256"]
    assert database.saved["sources"]["documents"][0]["id"] == 9


def test_record_analysis_blocks_go_with_uncalibrated_profile(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    database = FakeDatabase(_bundle())
    context_hash = context_fingerprint(build_analysis_context(settings, database, "Tender-42"))

    with pytest.raises(AnalysisContextError, match="profil One Tech incomplet"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(tmp_path),
            status="complete",
            adequation=20,
            deadline=20,
            administrative=15,
            risk=15,
            decision="GO",
            context_sha256=context_hash,
        )


def test_record_analysis_blocks_go_when_analysis_is_partial(tmp_path: Path) -> None:
    settings = _settings(tmp_path, incomplete_profile=False)
    database = FakeDatabase(_bundle())
    context_hash = context_fingerprint(build_analysis_context(settings, database, "Tender-42"))

    with pytest.raises(AnalysisContextError, match="analyse partielle.*GO définitif"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(tmp_path, partial_header=True),
            status="partielle",
            adequation=20,
            deadline=20,
            administrative=15,
            risk=15,
            decision="GO",
            context_sha256=context_hash,
        )


def test_record_analysis_rejects_incomplete_fiche_and_wrong_decision(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    database = FakeDatabase(_bundle())
    with pytest.raises(AnalysisContextError, match="Décision incohérente"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(tmp_path, score=40, decision="NO-GO"),
            status="complete",
            adequation=10,
            deadline=10,
            administrative=10,
            risk=10,
            decision="GO",
            context_sha256=context_fingerprint(
                build_analysis_context(settings, database, "Tender-42")
            ),
        )

    with pytest.raises(AnalysisContextError, match="sections obligatoires"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(
                tmp_path,
                complete=False,
                score=40,
                decision="NO-GO",
                partial_header=True,
            ),
            status="partielle",
            adequation=10,
            deadline=10,
            administrative=10,
            risk=10,
            decision="NO_GO",
            context_sha256=context_fingerprint(
                build_analysis_context(settings, database, "Tender-42")
            ),
        )


def test_record_analysis_requires_partial_status_for_incomplete_context(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    database = FakeDatabase(_bundle("sans_texte"))
    context_hash = context_fingerprint(build_analysis_context(settings, database, "Tender-42"))
    with pytest.raises(AnalysisContextError, match="contexte documentaire est partiel"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(tmp_path),
            status="complete",
            adequation=20,
            deadline=20,
            administrative=15,
            risk=15,
            decision="GO",
            context_sha256=context_hash,
        )


def test_record_analysis_rejects_stale_context_and_score_mismatch(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    database = FakeDatabase(_bundle())
    valid_hash = context_fingerprint(build_analysis_context(settings, database, "Tender-42"))

    with pytest.raises(AnalysisContextError, match="contexte PostgreSQL a changé"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=_fiche(tmp_path),
            status="complete",
            adequation=20,
            deadline=20,
            administrative=15,
            risk=15,
            decision="GO",
            context_sha256="0" * 64,
        )

    fiche = _fiche(tmp_path)
    fiche.write_text(
        fiche.read_text(encoding="utf-8").replace(
            "| Adéquation compétences | 20 |",
            "| Adéquation compétences | 19 |",
        ),
        encoding="utf-8",
    )
    with pytest.raises(AnalysisContextError, match="quatre notes"):
        record_analysis(
            settings,
            database,  # type: ignore[arg-type]
            reference="Tender-42",
            fiche=fiche,
            status="complete",
            adequation=20,
            deadline=20,
            administrative=15,
            risk=15,
            decision="GO",
            context_sha256=valid_hash,
        )
