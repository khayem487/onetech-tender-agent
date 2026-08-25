from __future__ import annotations

import asyncio
import copy
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError

from onetech_ao.config import Settings
from onetech_ao.database import Database
from onetech_ao.mcp_server import McpOperationError, TenderOperations, create_server


def _settings(tmp_path: Path) -> Settings:
    config = tmp_path / "config"
    config.mkdir()
    (config / "profil_entreprise.md").write_text(
        "# OneTech\n<!-- ONETECH_PROFILE_STATUS: VALIDATED_V1 -->\n",
        encoding="utf-8",
    )
    return Settings(
        postgres_db="test",
        postgres_user="test",
        postgres_password="secret",
        project_root=tmp_path,
        document_root=tmp_path / "data" / "documents",
    )


class _Database:
    def __init__(self) -> None:
        self.checked = False

    def check_connection(self) -> dict[str, str]:
        self.checked = True
        return {"database": "test", "utilisateur": "test", "version": "16"}

    def list_open(self, limit: int) -> list[dict[str, Any]]:
        return [
            {
                "tender_id": "Tender-42",
                "organisme": "Agence numérique",
                "titre": "Plateforme data cloud",
                "date_publication": datetime(2026, 8, 1, tzinfo=timezone.utc),
                "date_limite": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "reserve_pme": True,
                "url_detail": "https://example.test/Tender-42",
                "statut_echeance": "ouverte",
            },
            {
                "tender_id": "Tender-43",
                "organisme": "Ville",
                "titre": "Travaux de construction",
                "date_publication": datetime(2026, 8, 2, tzinfo=timezone.utc),
                "date_limite": datetime(2026, 9, 2, tzinfo=timezone.utc),
                "reserve_pme": False,
                "url_detail": "https://example.test/Tender-43",
                "statut_echeance": "ouverte",
            },
        ][:limit]

    def get_analysis_context(self, tender_id: str) -> dict[str, Any] | None:
        if tender_id != "Tender-42":
            return None
        return {
            "appel_offres": {
                "tender_id": "Tender-42",
                "source": "haicop",
                "plan_id": None,
                "organisme": "Agence numérique",
                "titre": "Plateforme data cloud",
                "date_publication": datetime(2026, 8, 1, tzinfo=timezone.utc),
                "date_limite": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "reserve_pme": True,
                "url_detail": "https://example.test/Tender-42",
                "champs_details": {},
                "donnees_brutes": {"id": 42},
            },
            "documents": [
                {
                    "id": 1,
                    "tender_id": "Tender-42",
                    "libelle": "Cahier des charges",
                    "type_document": "pdf",
                    "url": "https://example.test/cdc.pdf",
                    "chemin_local": "data/documents/Tender-42/cdc.pdf",
                    "texte_extrait": "Exigence technique importante.",
                    "empreinte_sha256": "a" * 64,
                    "mime_type": "application/pdf",
                    "taille_octets": 42,
                    "statut_traitement": "extrait",
                    "erreur_traitement": None,
                }
            ],
        }

    def latest_analysis(self, tender_id: str) -> dict[str, Any] | None:
        if tender_id == "Tender-42":
            return {"id": 9, "tender_id": tender_id, "decision": "A_DISCUTER", "score_total": 55}
        return None

    def analysis_digest(self, limit: int, include_expired: bool) -> list[dict[str, Any]]:
        return [
            {
                "id": 9,
                "tender_id": "Tender-42",
                "organisme": "Agence numérique",
                "titre": "Plateforme data cloud",
                "date_limite": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "url_detail": "https://example.test/Tender-42",
                "statut": "complete",
                "score_total": 55,
                "decision": "A_DISCUTER",
                "fiche_chemin": "fiches/test.md",
            }
        ][:limit]


class _CollectionResult:
    def to_dict(self) -> dict[str, Any]:
        return {"statut": "terminee", "nb_recus": 1, "nb_inseres": 1}


class _Collector:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def collect(self, **kwargs: Any) -> _CollectionResult:
        self.collect_kwargs = kwargs
        return _CollectionResult()


class _ProcessingResult:
    def to_dict(self) -> dict[str, Any]:
        return {"statut": "terminee", "nb_traites": 1}


class _DocumentProcessor:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def process(self, **kwargs: Any) -> _ProcessingResult:
        self.process_kwargs = kwargs
        return _ProcessingResult()


def _operations(tmp_path: Path) -> TenderOperations:
    return TenderOperations(
        settings=_settings(tmp_path),
        database=_Database(),  # type: ignore[arg-type]
        collector_factory=_Collector,  # type: ignore[arg-type]
        document_processor_factory=_DocumentProcessor,  # type: ignore[arg-type]
    )


def test_list_open_tenders_filters_and_serializes_dates(tmp_path: Path) -> None:
    result = _operations(tmp_path).list_open_tenders(query="data")

    assert result["schema_version"] == "1.0"
    assert result["operation"] == "list_open_tenders"
    assert result["nb_resultats"] == 1
    assert result["appels_offres"][0]["tender_id"] == "Tender-42"
    assert result["appels_offres"][0]["date_limite"].startswith("2026-09-01")


def test_get_and_analyze_tender_return_safe_context(tmp_path: Path) -> None:
    operations = _operations(tmp_path)
    tender = operations.get_tender(
        tender_id="Tender-42",
        include_document_text=True,
        document_text_chars=10,
    )
    analysis = operations.analyze_tender(tender_id="Tender-42", document_text_chars=20)

    assert tender["documents"][0]["texte_extrait"] == "Exigence t"
    assert tender["documents"][0]["texte_tronque"] is True
    assert "donnees_brutes" not in tender["appel_offres"]
    assert tender["texte_documents"]["caracteres_retournes"] == 10
    assert tender["derniere_analyse"]["decision"] == "A_DISCUTER"
    assert analysis["statut"] == "analyse_existante"
    assert analysis["modele_local"]["nom"] == "ollama/phi4-mini:latest"
    assert analysis["analyse_generee"] is False
    assert analysis["analyse_persistee"] is False
    assert analysis["semantique"]["mode"] == "lecture_ou_preparation_de_contexte"
    assert analysis["semantique"]["nouvelle_analyse_generee"] is False


def test_collect_and_digest_expose_existing_operations(tmp_path: Path) -> None:
    operations = _operations(tmp_path)
    collected = operations.collect_tenders(process_documents=True)
    digest = operations.generate_digest()

    assert collected["nb_inseres"] == 1
    assert collected["operation"] == "collect_tenders"
    assert collected["effets"]["postgres_ecrit"] is True
    assert collected["traitement_documents"]["nb_traites"] == 1
    assert digest["diffusion_externe"] is False
    assert digest["source"] == "analyses_postgresql_deja_enregistrees"
    assert "Tender-42" in digest["markdown"]
    json.dumps(digest, ensure_ascii=False, allow_nan=False, sort_keys=True)


def test_limits_are_validated(tmp_path: Path) -> None:
    operations = _operations(tmp_path)
    with pytest.raises(McpOperationError):
        operations.list_open_tenders(limit=0)
    with pytest.raises(McpOperationError):
        operations.list_open_tenders(limit=True)  # type: ignore[arg-type]
    with pytest.raises(McpOperationError):
        operations.list_open_tenders(query="x" * 201)
    with pytest.raises(McpOperationError):
        operations.list_open_tenders(query="data\ncloud")
    with pytest.raises(McpOperationError):
        operations.get_tender(tender_id="Tender-42", document_text_chars=20_000)
    with pytest.raises(McpOperationError):
        operations.get_tender(tender_id="Tender-" + "x" * 300)
    with pytest.raises(McpOperationError):
        operations.collect_tenders(since_days=True)  # type: ignore[arg-type]


def test_document_text_has_a_global_response_budget(tmp_path: Path) -> None:
    database = _Database()
    original = database.get_analysis_context

    def many_documents(tender_id: str) -> dict[str, Any] | None:
        bundle = original(tender_id)
        assert bundle is not None
        template = bundle["documents"][0]
        bundle = copy.deepcopy(bundle)
        bundle["documents"] = [
            {
                **template,
                "id": index,
                "url": f"https://example.test/{index}.pdf",
                "texte_extrait": "x" * 20_000,
            }
            for index in range(1, 6)
        ]
        return bundle

    database.get_analysis_context = many_documents  # type: ignore[method-assign]
    operations = TenderOperations(
        settings=_settings(tmp_path),
        database=database,  # type: ignore[arg-type]
        collector_factory=_Collector,  # type: ignore[arg-type]
        document_processor_factory=_DocumentProcessor,  # type: ignore[arg-type]
    )
    result = operations.get_tender(
        tender_id="Tender-42",
        include_document_text=True,
        document_text_chars=12_000,
        include_raw_data=True,
    )

    assert result["texte_documents"]["caracteres_retournes"] == 48_000
    assert result["texte_documents"]["budget_epuise"] is True
    assert result["documents"][-1]["texte_extrait"] is None
    assert result["appel_offres"]["donnees_brutes"] == {"id": 42}


def test_fastmcp_server_advertises_honest_tools_and_annotations(tmp_path: Path) -> None:
    server = create_server(_operations(tmp_path))
    tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in tools} == {
        "collect_tenders",
        "list_open_tenders",
        "get_tender",
        "analyze_tender",
        "generate_digest",
    }
    by_name = {tool.name: tool for tool in tools}
    assert by_name["collect_tenders"].annotations.readOnlyHint is False
    assert by_name["collect_tenders"].annotations.openWorldHint is True
    assert by_name["get_tender"].annotations.readOnlyHint is True
    assert "Ne lance aucun modèle" in by_name["analyze_tender"].description


def test_fastmcp_redacts_internal_errors(tmp_path: Path) -> None:
    operations = _operations(tmp_path)

    def fail(_limit: int) -> list[dict[str, Any]]:
        raise RuntimeError("secret: connection failure")

    operations.database.list_open = fail  # type: ignore[method-assign]
    server = create_server(operations)

    with pytest.raises(ToolError) as captured:
        asyncio.run(server.call_tool("list_open_tenders", {"limit": 1}))

    assert "secret" not in str(captured.value)
    assert "[SECRET MASQUÉ]" in str(captured.value)


@pytest.mark.integration
def test_stdio_server_reads_real_postgresql() -> None:
    """Handshake MCP réel puis appels read-only via un sous-processus stdio."""
    try:
        settings = Settings.load()
        Database(settings).check_connection()
    except Exception as exc:
        pytest.skip(f"PostgreSQL local indisponible: {exc}")

    async def smoke() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "onetech_ao.mcp_server"],
            cwd=settings.project_root,
        )
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
            async with asyncio.timeout(30):
                async with stdio_client(parameters, errlog=errors) as (read, write):
                    async with ClientSession(read, write) as session:
                        initialized = await session.initialize()
                        assert initialized.serverInfo.name == "OneTech Tender Agent"

                        listed = await session.list_tools()
                        names = {tool.name for tool in listed.tools}
                        assert {
                            "collect_tenders",
                            "list_open_tenders",
                            "get_tender",
                        "analyze_tender",
                            "generate_digest",
                        } <= names

                        open_result = await session.call_tool(
                            "list_open_tenders",
                            {"limit": 1},
                        )
                        assert open_result.isError is False
                        payload = open_result.structuredContent
                        assert payload is not None
                        assert payload["schema_version"] == "1.0"
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                            allow_nan=False,
                            sort_keys=True,
                        )

                        tenders = payload["appels_offres"]
                        if tenders:
                            tender_id = tenders[0]["tender_id"]
                            tender_result = await session.call_tool(
                                "get_tender",
                                {"tender_id": tender_id, "include_document_text": False},
                            )
                            assert tender_result.isError is False
                            tender_payload = tender_result.structuredContent
                            assert tender_payload is not None
                            assert tender_payload["tender_id"] == tender_id
                            assert "donnees_brutes" not in tender_payload["appel_offres"]

                            alias_result = await session.call_tool(
                                "analyze_tender",
                                {"tender_id": tender_id, "document_text_chars": 500},
                            )
                            assert alias_result.isError is False
                            alias_payload = alias_result.structuredContent
                            assert alias_payload is not None
                            assert alias_payload["analyse_generee"] is False
                            assert alias_payload["analyse_persistee"] is False
                            assert alias_payload["semantique"]["mode"] == (
                                "lecture_ou_preparation_de_contexte"
                            )

                        digest_result = await session.call_tool(
                            "generate_digest",
                            {"limit": 1, "include_expired": False},
                        )
                        assert digest_result.isError is False
                        assert digest_result.structuredContent["diffusion_externe"] is False

    asyncio.run(smoke())
