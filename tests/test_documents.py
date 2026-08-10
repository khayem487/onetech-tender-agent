from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document

from onetech_ao.config import Settings
from onetech_ao.documents import DocumentProcessor, validate_public_document_url


class FakeResponse:
    def __init__(self, body: bytes, url: str, content_type: str) -> None:
        self.body = body
        self.url = url
        self.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": content_type,
        }

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [
            self.body[index : index + chunk_size]
            for index in range(0, len(self.body), chunk_size)
        ]


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers: dict[str, str] = {}
        self.calls = 0
        self.closed = False

    def mount(self, prefix: str, adapter: object) -> None:
        return None

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls += 1
        return self.response

    def close(self) -> None:
        self.closed = True


class FakeDatabase:
    def __init__(self, task: dict[str, Any]) -> None:
        self.task = task
        self.saved: dict[str, Any] | None = None
        self.failed: tuple[int, str] | None = None

    def check_connection(self) -> dict[str, str]:
        return {"database": "test"}

    def documents_to_process(
        self, limit: int, retry_errors: bool
    ) -> list[dict[str, Any]]:
        return [self.task]

    def save_document_processing(self, **kwargs: Any) -> None:
        self.saved = kwargs

    def fail_document_processing(
        self, document_id: int, error: str, **kwargs: Any
    ) -> None:
        self.failed = (document_id, error)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        postgres_db="test",
        postgres_user="test",
        postgres_password="secret",
        project_root=tmp_path,
        document_root=tmp_path / "data" / "documents",
    )


def _docx_bytes() -> bytes:
    output = BytesIO()
    document = Document()
    document.add_heading("Cahier des charges", level=1)
    document.add_paragraph("Date limite : 30 septembre 2026 à 10h00")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Caution"
    table.rows[0].cells[1].text = "5 000 TND"
    document.save(output)
    return output.getvalue()


def test_processor_downloads_hashes_and_extracts_docx(tmp_path: Path) -> None:
    url = "https://www.marchespublics.gov.tn/storage/tender/test/cdc.docx"
    task = {
        "id": 42,
        "tender_id": "Tender-42",
        "url": url,
        "type_document": "docx",
        "chemin_local": None,
        "empreinte_sha256": None,
    }
    database = FakeDatabase(task)
    session = FakeSession(
        FakeResponse(
            body=_docx_bytes(),
            url=url,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )
    )

    result = DocumentProcessor(
        settings=_settings(tmp_path),
        database=database,  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
    ).process(limit=1)

    assert result.extraits == 1
    assert result.echecs == 0
    assert database.failed is None
    assert database.saved is not None
    assert database.saved["status"] == "extrait"
    assert database.saved["detected_type"] == "docx"
    assert len(database.saved["sha256"]) == 64
    assert "Date limite" in database.saved["extracted_text"]
    assert "5 000 TND" in database.saved["extracted_text"]
    assert (tmp_path / database.saved["relative_path"]).is_file()
    assert session.closed is True


def test_processor_rejects_non_haicop_url_without_downloading(tmp_path: Path) -> None:
    url = "https://example.com/storage/tender/evil.pdf"
    task = {
        "id": 7,
        "tender_id": "Tender-7",
        "url": url,
        "type_document": "pdf",
        "chemin_local": None,
        "empreinte_sha256": None,
    }
    database = FakeDatabase(task)
    session = FakeSession(FakeResponse(b"%PDF-test", url, "application/pdf"))

    result = DocumentProcessor(
        settings=_settings(tmp_path),
        database=database,  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
    ).process(limit=1)

    assert result.echecs == 1
    assert database.saved is None
    assert database.failed is not None
    assert "hôte non autorisé" in database.failed[1]
    assert session.calls == 0


def test_validate_public_document_url_accepts_only_public_storage() -> None:
    validate_public_document_url(
        "https://www.marchespublics.gov.tn/storage/tender/2026/08/test.pdf"
    )
