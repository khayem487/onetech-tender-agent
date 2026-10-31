"""One-request parser process. No credentials, network collection or database use.

Executed with ``python -I -B worker.py``. Linux resource limits are installed
before importing document libraries. Windows runs trusted synthetic examples only.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_EXPANDED = 8 * 1024 * 1024
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_MEMBERS = 200
MAX_TEXT = 40_000
MAX_PAGES = 20
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"


class RejectedDocument(Exception):
    pass


def apply_resource_limits() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        import resource

        for name, maximum in (
            ("RLIMIT_CPU", 6), ("RLIMIT_AS", 384 * 1024 * 1024),
            ("RLIMIT_FSIZE", 16 * 1024 * 1024), ("RLIMIT_NOFILE", 64), ("RLIMIT_CORE", 0),
        ):
            kind = getattr(resource, name)
            _, hard = resource.getrlimit(kind)
            limit = maximum if hard == resource.RLIM_INFINITY else min(maximum, hard)
            resource.setrlimit(kind, (limit, limit))
            soft_after, hard_after = resource.getrlimit(kind)
            if soft_after > maximum or hard_after > maximum:
                return False
        return True
    except (ImportError, AttributeError, OSError, ValueError):
        return False


def validate_docx_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_MEMBERS or len({entry.filename for entry in entries}) != len(entries):
                raise RejectedDocument()
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise RejectedDocument()
            total = 0
            for entry in entries:
                name = entry.orig_filename
                parts = name.rstrip("/").split("/")
                mode = entry.external_attr >> 16
                if (not name or name != entry.filename or len(name) > 200 or "\\" in name or ":" in name
                        or name.startswith("/") or any(part in {"..", "."} for part in parts)
                        or any(ord(char) < 32 or ord(char) == 127 for char in name)
                        or stat.S_ISLNK(mode) or entry.flag_bits & 1
                        or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                    raise RejectedDocument()
                total += entry.file_size
                if entry.file_size > MAX_MEMBER_BYTES or total > MAX_EXPANDED:
                    raise RejectedDocument()
                if entry.file_size > max(1, entry.compress_size) * 200:
                    raise RejectedDocument()
                folded = name.casefold()
                if ("vbaproject" in folded or "/embeddings/" in folded or "/activex/" in folded
                        or folded.endswith((".exe", ".dll", ".com", ".bat", ".js"))):
                    raise RejectedDocument()
                if folded.endswith((".xml", ".rels")):
                    data = archive.read(entry)
                    upper = data.upper()
                    # This public subset accepts ordinary UTF-8/ASCII OOXML.
                    # Refuse NUL-bearing UTF-16/32 parts so alternate encodings
                    # cannot bypass the explicit DTD/entity prohibition.
                    if b"\x00" in data or b"<!DOCTYPE" in upper or b"<!ENTITY" in upper or b"MACROENABLED" in upper:
                        raise RejectedDocument()
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError):
        raise RejectedDocument() from None


SAMPLE_LINES = (
    "Cahier des charges - EXEMPLE FICTIF",
    "Projet : plateforme web de suivi des demandes informatiques.",
    "Objet : concevoir un logiciel de gestion documentaire et un tableau de bord data.",
    "Prestations : application web, stockage de donnees et formation des utilisateurs.",
    "Livrables : code source, tests, documentation et guide utilisateur.",
    "Delai indicatif : 90 jours apres notification.",
    "Budget : non renseigne. Aucun engagement reel ni appel d'offres officiel.",
    "Conditions administratives detaillees : non renseignees.",
)


def synthetic_pdf() -> bytes:
    # A small, valid PDF generated from this public, synthetic text; never a
    # cached result. It will be parsed through the original extract_text path.
    commands = ["BT /F1 11 Tf 45 790 Td 16 TL"]
    for index, line in enumerate(SAMPLE_LINES):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(("T* " if index else "") + f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def synthetic_docx() -> bytes:
    from docx import Document

    output = io.BytesIO()
    document = Document()
    document.add_heading(SAMPLE_LINES[0], level=1)
    for line in SAMPLE_LINES[1:]:
        document.add_paragraph(line)
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Critere de demonstration"
    table.rows[0].cells[1].text = "Extraction native des tableaux"
    document.save(output)
    return output.getvalue()


def _source_quote(text: str) -> str:
    return " ".join(text.split())[:320]


def run(payload: dict[str, Any], limits_active: bool) -> dict[str, Any]:
    # Only this repository's trusted code is added to the isolated interpreter.
    sys.path.insert(0, str(SOURCE_ROOT))
    from onetech_ao.analysis import classify_document
    from onetech_ao.automation import relevance
    from onetech_ao.collector import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS
    from onetech_ao.documents import extract_text
    from pypdf import PdfReader

    sample = payload.get("sample")
    if sample not in (None, "pdf", "docx"):
        raise RejectedDocument()
    if sample is None and not limits_active:
        return {"error": "limits_unavailable"}
    with tempfile.TemporaryDirectory(prefix="native-") as temporary:
        if sample:
            document_type = sample
            name = f"exemple-fictif.{sample}"
            body = synthetic_pdf() if sample == "pdf" else synthetic_docx()
            path = Path(temporary) / name
            path.write_bytes(body)
        else:
            document_type = payload.get("type")
            path = Path(payload["path"])
            name = payload["name"]
            if document_type not in {"pdf", "docx"} or path.stat().st_size > MAX_FILE_BYTES:
                raise RejectedDocument()
            body = path.read_bytes()
        if not body or len(body) > MAX_FILE_BYTES:
            raise RejectedDocument()
        if document_type == "pdf" and not body.startswith(b"%PDF-"):
            raise RejectedDocument()
        if document_type == "docx":
            if not body.startswith(b"PK\x03\x04"):
                raise RejectedDocument()
            validate_docx_archive(path)
        settings = SimpleNamespace(
            document_max_bytes=MAX_FILE_BYTES,
            document_max_uncompressed_bytes=MAX_EXPANDED,
            document_max_text_chars=MAX_TEXT,
            document_max_pdf_pages=MAX_PAGES,
            document_ocr_enabled=False,
        )
        # No Settings.load(), DocumentProcessor, Database, profile or gateway.
        page_count: int | None = None
        reader = None
        if document_type == "pdf":
            reader = PdfReader(str(path))
            if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
                raise RejectedDocument()
            page_count = len(reader.pages)
        text = extract_text(path, document_type, settings) or ""
        warnings: list[str] = []
        if sample:
            warnings.append("Exemple entièrement fictif, généré et extrait à chaque requête.")
        sources: list[dict[str, Any]] = []
        unreadable_pages = 0
        if reader is not None:
            # Obtain quotes from actual page objects rather than trusting page
            # markers that an uploaded document could itself contain.
            for number, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    unreadable_pages += 1
                elif len(sources) < 8:
                    sources.append({"page": number, "quote": _source_quote(page_text)})
            if unreadable_pages:
                warnings.append(f"{unreadable_pages} page(s) sans texte natif. L’OCR est désactivé ; extraction partielle.")
        elif text:
            sources = [{"page": None, "quote": _source_quote(text)}]
        if not text.strip():
            warnings.append("Aucun texte natif exploitable. Un document scanné peut nécessiter un OCR.")
        truncated = len(text) >= MAX_TEXT
        if truncated:
            warnings.append("Le texte a atteint la limite de 40 000 caractères ; la revue est partielle.")
        # Filenames are not evidence of document role. The original classifier's
        # 'Autres' path examines strong headings in the extracted content.
        classification = classify_document("Autres", text)
        partial = unreadable_pages > 0 or truncated or not text.strip() or classification != "dossier_de_fond"
        if classification != "dossier_de_fond":
            warnings.append("Aucun cahier des charges ou dossier de fond identifié par le classement lexical.")
        keywords = payload.get("keywords")
        if keywords is None:
            keywords = list(POSITIVE_KEYWORDS)
        score, reasons = relevance(
            {"titre": "", "organisme": "", "champs_details": {}, "extrait_documents": text},
            {"positive_keywords": keywords, "negative_keywords": list(NEGATIVE_KEYWORDS)},
        )
        return {
            "document": {"name": name, "type": document_type,
                         "sha256": hashlib.sha256(body).hexdigest(), "text": text[:MAX_TEXT], "pages": page_count},
            "classification": classification,
            "relevance": {"score": score, "reasons": reasons,
                          "method": "lexical-shortlist", "keywords": keywords, "ranking_only": True},
            "sources": sources, "warnings": warnings, "partial": bool(partial),
            "processing": {"engine": "original-onetech", "ai": False,
                           "resource_limits": limits_active, "ocr": False},
        }


def main() -> None:
    limits_active = apply_resource_limits()
    try:
        # Generated by the parent from installed package specs. Public request
        # fields cannot alter argv. Keep -I and the stripped child environment.
        arguments = sys.argv[1:]
        if len(arguments) % 2 or len(arguments) > 32:
            raise RejectedDocument()
        for index in range(0, len(arguments), 2):
            root = Path(arguments[index + 1])
            if arguments[index] != "--dependency-root" or not root.is_absolute() or not root.is_dir():
                raise RejectedDocument()
            sys.path.append(str(root.resolve()))
        raw = sys.stdin.buffer.read(8193)
        if len(raw) > 8192:
            raise RejectedDocument()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RejectedDocument()
        if payload.get("require_limits") and not limits_active:
            result = {"error": "limits_unavailable"}
        else:
            result = run(payload, limits_active)
    except Exception:
        result = {"error": "invalid_document"}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
