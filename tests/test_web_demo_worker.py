from __future__ import annotations

import io
import json
import sys
import types
import zipfile
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from web_demo import worker


def parse_fixture(tmp_path, body, document_type="pdf", **fields):
    path = tmp_path / f"fixture.{document_type}"
    path.write_bytes(body)
    # Unit-level parsing tests pass this flag without claiming an OS sandbox.
    # Actual upload dispatch independently refuses unsupported operating systems.
    return worker.run({"path": str(path), "type": document_type,
                       "name": path.name, "sample": None, **fields}, limits_active=True)


def docx_bytes(text):
    buffer = io.BytesIO()
    document = Document()
    document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def test_original_functions_used_without_runtime_db_profile_or_network(tmp_path, monkeypatch):
    from onetech_ao import analysis, config, database, documents
    import requests

    def forbidden(*_args, **_kwargs):
        pytest.fail("public native path must not access runtime configuration, database or network")

    monkeypatch.setattr(config.Settings, "load", forbidden)
    monkeypatch.setattr(database.Database, "connect", forbidden)
    monkeypatch.setattr(analysis, "_profile", forbidden)
    monkeypatch.setattr(requests.Session, "request", forbidden)
    original = documents.extract_text
    calls = []

    def tracked(*args, **kwargs):
        calls.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(documents, "extract_text", tracked)
    result = parse_fixture(tmp_path, docx_bytes("Cahier des charges\nLogiciel de gestion du cloud."), "docx")
    assert calls == ["docx"]
    assert result["relevance"]["score"] >= 6
    assert result["classification"] == "dossier_de_fond"


@pytest.mark.parametrize("document_type,body", [("pdf", b"PK\x03\x04notpdf"), ("docx", b"%PDF-notdocx")])
def test_declared_type_cannot_override_file_signature(tmp_path, document_type, body):
    with pytest.raises(worker.RejectedDocument):
        parse_fixture(tmp_path, body, document_type)


def test_too_many_pages_and_encrypted_pdf_are_rejected(tmp_path):
    for pages, encrypted in [(21, False), (1, True)]:
        output = io.BytesIO()
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=100, height=100)
        if encrypted:
            writer.encrypt("not-a-real-password")
        writer.write(output)
        with pytest.raises(worker.RejectedDocument):
            parse_fixture(tmp_path, output.getvalue())


def test_scanned_pdf_is_honestly_partial_without_ocr(tmp_path):
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    result = parse_fixture(tmp_path, output.getvalue())
    assert result["document"]["text"] == ""
    assert result["sources"] == []
    assert result["partial"] is True
    assert any("OCR" in value for value in result["warnings"])


def test_long_native_text_is_bounded_and_partial(tmp_path):
    text = "Cahier des charges\n" + "Information distincte. " * 3_000
    result = parse_fixture(tmp_path, docx_bytes(text), "docx")
    assert len(result["document"]["text"]) == 40_000
    assert result["partial"] is True
    assert any("40 000" in item for item in result["warnings"])


def test_filename_does_not_establish_documentary_coverage(tmp_path):
    result = parse_fixture(tmp_path, docx_bytes("Une facture de démonstration."), "docx", name="Cahier des charges.docx")
    assert result["classification"] == "autre"
    assert result["partial"] is True


def archive_with_extra(name, content, *, entries=1):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        for index in range(entries):
            raw_name = name if entries == 1 else f"{name}{index}"
            entry = zipfile.ZipInfo(raw_name)
            entry.filename = raw_name  # Preserve hostile wire spelling on Windows.
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content)
    return output.getvalue()


@pytest.mark.parametrize("name,content,entries", [
    ("../escape.xml", "x", 1), ("word/./ambiguous.xml", "x", 1),
    ("C:/absolute.xml", "x", 1), ("word\\ambiguous.xml", "x", 1),
    ("word/embeddings/object.bin", "x", 1), ("word/vbaProject.bin", "x", 1),
    ("word/unsafe.xml", '<!DOCTYPE doc [<!ENTITY x "expanded">]><doc>&x;</doc>', 1),
    ("word/utf16.xml", '<!DOCTYPE doc [<!ENTITY x "expanded">]><doc>&x;</doc>'.encode("utf-16"), 1),
    ("word/entry", "x", 199), ("word/bomb.xml", "x" * (4 * 1024 * 1024 + 1), 1),
])
def test_docx_resource_paths_entities_and_embedded_code_are_rejected(tmp_path, name, content, entries):
    with pytest.raises(worker.RejectedDocument):
        parse_fixture(tmp_path, archive_with_extra(name, content, entries=entries), "docx")


def test_docx_total_expansion_is_bounded(tmp_path):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        for index in range(3):
            archive.writestr(f"word/part{index}.xml", b"x" * (3 * 1024 * 1024))
    path = tmp_path / "expanded.docx"
    path.write_bytes(output.getvalue())
    with pytest.raises(worker.RejectedDocument):
        worker.validate_docx_archive(path)


def test_upload_worker_itself_refuses_missing_resource_guards(tmp_path):
    result = worker.run({"sample": None, "path": "/must/not/read"}, limits_active=False)
    assert result == {"error": "limits_unavailable"}


def test_linux_limits_lower_all_required_resources_and_fail_closed(monkeypatch):
    settings = {}
    fake = types.SimpleNamespace(RLIM_INFINITY=-1)
    for index, name in enumerate(("RLIMIT_CPU", "RLIMIT_AS", "RLIMIT_FSIZE", "RLIMIT_NOFILE", "RLIMIT_CORE")):
        setattr(fake, name, index)
    fake.getrlimit = lambda key: settings.get(key, (-1, -1))
    fake.setrlimit = lambda key, value: settings.__setitem__(key, value)
    monkeypatch.setitem(sys.modules, "resource", fake)
    monkeypatch.setattr(worker.sys, "platform", "linux")
    assert worker.apply_resource_limits() is True
    assert settings == {0: (6, 6), 1: (384 * 1024 * 1024,) * 2,
                        2: (16 * 1024 * 1024,) * 2, 3: (64, 64), 4: (0, 0)}

    def denied(*_args):
        raise OSError("denied")

    fake.setrlimit = denied
    assert worker.apply_resource_limits() is False
