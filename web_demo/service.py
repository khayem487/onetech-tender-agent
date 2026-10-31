"""Bounded subprocess dispatch; never load the internship runtime configuration."""

from __future__ import annotations

import json
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_DOCX_EXPANDED_BYTES = 8 * 1024 * 1024
MAX_DOCX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_DOCX_MEMBERS = 200
MAX_TEXT_CHARS = 40_000
WORKER_TIMEOUT = 10
WORKER_SLOTS = threading.BoundedSemaphore(2)
WORKER_PATH = Path(__file__).with_name("worker.py").resolve()
KEYWORD_RE = re.compile(r"^[\wÀ-ÖØ-öø-ÿ '’\-]+$", re.UNICODE)


class DemoError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def resource_limits_supported() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        import resource

        return all(hasattr(resource, name) for name in (
            "RLIMIT_CPU", "RLIMIT_AS", "RLIMIT_FSIZE", "RLIMIT_NOFILE", "RLIMIT_CORE"
        ))
    except ImportError:
        return False


def capabilities() -> dict[str, Any]:
    return {
        "uploads_enabled": resource_limits_supported(),
        "samples": ["pdf", "docx"],
        "ai": False,
        "storage": "temporary-request-only",
        "engine": "original-onetech",
        "ocr": False,
        "limits": {
            "file_bytes": MAX_FILE_BYTES,
            "pdf_pages": MAX_PDF_PAGES,
            "docx_expanded_bytes": MAX_DOCX_EXPANDED_BYTES,
            "docx_members": MAX_DOCX_MEMBERS,
            "text_chars": MAX_TEXT_CHARS,
            "timeout_seconds": WORKER_TIMEOUT,
        },
    }


def parse_keywords(raw: str | None) -> list[str] | None:
    if raw is None or raw == "":
        return None
    if len(raw) > 2048:
        raise DemoError("invalid_keywords", "Liste de mots-clés invalide.", 400)
    try:
        values = json.loads(raw)
    except (ValueError, TypeError):
        raise DemoError("invalid_keywords", "Les mots-clés doivent être une liste JSON.", 400) from None
    if not isinstance(values, list) or len(values) > 12:
        raise DemoError("invalid_keywords", "Utilisez au maximum 12 mots-clés.", 400)
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 40 or not KEYWORD_RE.fullmatch(value.strip()):
            raise DemoError("invalid_keywords", "Chaque mot-clé doit contenir entre 1 et 40 caractères simples.", 400)
        if value.strip().casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(value.strip())
    return cleaned


def validate_upload_name(name: str, content_type: str) -> tuple[str, str]:
    if not isinstance(name, str) or not name or len(name) > 140:
        raise DemoError("invalid_filename", "Nom de fichier invalide.", 400)
    if any(char in name for char in ("/", "\\", ":", "\x00")) or any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise DemoError("invalid_filename", "Utilisez un nom de fichier simple.", 400)
    extension = Path(name).suffix.lower()
    expected = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    }
    if extension not in expected or content_type.lower() not in expected[extension]:
        raise DemoError("unsupported_type", "Seuls les fichiers PDF et DOCX sont acceptés.", 415)
    return name, extension[1:]


def _worker_environment() -> dict[str, str]:
    # Do not pass DB, AI provider, email, Vercel or other application secrets.
    allowed = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL", "TZ", "LD_LIBRARY_PATH")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _dependency_roots() -> list[str]:
    """Locate trusted installed packages, including Vercel's vendored layout.

    Isolated Python intentionally ignores PYTHONPATH. These roots come from
    server-side package discovery, never a request field or inherited env var.
    """
    roots: set[str] = set()
    for module in ("flask", "pypdf", "docx", "psycopg", "requests", "dotenv", "bs4", "tzdata"):
        spec = importlib.util.find_spec(module)
        if spec is not None and spec.origin:
            origin = Path(spec.origin).resolve()
            root = origin.parent.parent if spec.submodule_search_locations is not None else origin.parent
            if root.is_dir():
                roots.add(str(root))
    return sorted(roots)


def _execute_worker(payload: dict[str, Any], temporary: str) -> bytes:
    # File-backed stdout prevents a parser/library print from filling parent
    # memory. Linux RLIMIT_FSIZE also caps this disposable file in the child.
    with tempfile.TemporaryFile(dir=temporary) as worker_output:
        command = [sys.executable, "-I", "-B", str(WORKER_PATH)]
        for root in _dependency_roots():
            command.extend(("--dependency-root", root))
        try:
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=worker_output,
                stderr=subprocess.DEVNULL, cwd=temporary,
                env=_worker_environment(),
            )
        except OSError:
            raise DemoError("worker_unavailable", "Le service de traitement est indisponible.", 503) from None
        try:
            process.communicate(json.dumps(payload).encode("utf-8"), timeout=WORKER_TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise DemoError("processing_timeout", "Le document dépasse le temps de traitement autorisé.", 422) from None
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        worker_output.seek(0)
        output = worker_output.read(400_001)
        if process.returncode or not output or len(output) > 400_000:
            raise DemoError("processing_failed", "Ce document n’a pas pu être traité dans les limites du service.", 422)
        return output


def process_document(*, body: bytes | None = None, name: str | None = None,
                     document_type: str | None = None, sample: str | None = None,
                     keywords: list[str] | None = None) -> dict[str, Any]:
    if sample not in (None, "pdf", "docx"):
        raise DemoError("invalid_sample", "Exemple inconnu.", 400)
    upload = sample is None
    if upload and not resource_limits_supported():
        raise DemoError("uploads_unavailable", "Les fichiers personnels nécessitent le serveur isolé Linux. Les exemples restent disponibles.", 503)
    if upload and (not body or len(body) > MAX_FILE_BYTES):
        raise DemoError("file_size", "Le fichier doit être non vide et faire au maximum 2 Mio.", 413)
    if not WORKER_SLOTS.acquire(blocking=False):
        raise DemoError("busy", "Deux documents sont déjà en cours de traitement. Réessayez bientôt.", 429)
    try:
        with tempfile.TemporaryDirectory(prefix="onetech-public-") as temporary:
            payload: dict[str, Any] = {
                "sample": sample, "name": name, "type": document_type,
                "keywords": keywords, "require_limits": upload,
            }
            if upload:
                path = Path(temporary) / f"input.{document_type}"
                path.write_bytes(body)
                payload["path"] = str(path)
            output = _execute_worker(payload, temporary)
            try:
                result = json.loads(output)
            except (ValueError, UnicodeError):
                raise DemoError("processing_failed", "Le document n’a pas pu être traité.", 422) from None
            if not isinstance(result, dict):
                raise DemoError("processing_failed", "Le document n’a pas pu être traité.", 422)
            if "error" in result:
                code = result.get("error")
                status = 503 if code == "limits_unavailable" else 422
                raise DemoError(str(code), "Les protections de traitement sont indisponibles." if status == 503 else "Document invalide, non pris en charge ou trop complexe.", status)
            return result
    finally:
        WORKER_SLOTS.release()


def manual_decision(payload: Any) -> dict[str, Any]:
    fields = ("adequation", "delai", "administratif", "risque")
    if not isinstance(payload, dict) or set(payload) != {*fields, "partial"}:
        raise DemoError("invalid_scores", "Fournissez les quatre notes et l’état de couverture documentaire.", 400)
    if not isinstance(payload["partial"], bool) or any(type(payload[field]) is not int or not 0 <= payload[field] <= 25 for field in fields):
        raise DemoError("invalid_scores", "Les quatre notes doivent être des entiers de 0 à 25.", 400)
    source_path = str(Path(__file__).resolve().parents[1] / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    from onetech_ao.analysis import expected_decision

    total = sum(payload[field] for field in fields)
    decision = expected_decision(total)
    if payload["partial"] and decision == "GO":
        raise DemoError("partial_go_forbidden", "Un dossier partiel ne permet pas de valider un GO. Complétez la revue documentaire.", 409)
    return {"scores": {field: payload[field] for field in fields}, "total": total,
            "decision": decision, "partial": payload["partial"], "method": "manual-rubric", "ai": False}
