"""Configuration du collecteur, chargée depuis le fichier .env local."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(RuntimeError):
    """Configuration locale absente ou invalide."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Paramètres nécessaires au collecteur.

    Le mot de passe est exclu de la représentation de l'objet pour éviter une
    fuite accidentelle dans les logs ou les erreurs interactives.
    """

    postgres_db: str
    postgres_user: str
    postgres_password: str = field(repr=False)
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    haicop_base_url: str = "https://www.marchespublics.gov.tn"
    http_connect_timeout: float = 5.0
    http_read_timeout: float = 30.0
    user_agent: str = "OneTechTenderAgent/0.1 (+public HAICOP collector)"
    project_root: Path = PROJECT_ROOT
    document_root: Path = PROJECT_ROOT / "data" / "documents"
    document_max_bytes: int = 25 * 1024 * 1024
    document_max_uncompressed_bytes: int = 100 * 1024 * 1024
    document_max_text_chars: int = 5_000_000
    document_max_pdf_pages: int = 500
    document_ocr_enabled: bool = True
    document_ocr_languages: str = "fra+ara+eng"
    document_ocr_max_pages: int = 50
    document_ocr_dpi: int = 200
    document_ocr_max_render_bytes: int = 150 * 1024 * 1024
    document_ocr_timeout_seconds: int = 90
    document_conversion_timeout_seconds: int = 120
    tesseract_command: str = "tesseract"
    pdftoppm_command: str = "pdftoppm"
    libreoffice_command: str = "libreoffice"

    @classmethod
    def load(
        cls,
        env_file: Path | None = None,
        *,
        project_root: Path | None = None,
    ) -> "Settings":
        """Load local ``.env`` settings or an explicitly enabled container env.

        Local development deliberately keeps requiring ``.env``.  The worker
        container receives the same required values through Docker Compose, so
        it opts in with ``ONETECH_AO_ALLOW_ENV_ONLY=true`` instead of mounting
        secrets into the image.  ``project_root`` also makes paths deterministic
        when the package is installed in site-packages rather than editable.
        """

        configured_root = os.getenv("ONETECH_AO_PROJECT_ROOT", "").strip()
        root_source = project_root or (Path(configured_root) if configured_root else PROJECT_ROOT)
        root = root_source.expanduser().resolve()

        if env_file is not None:
            target = env_file.expanduser()
            if not target.is_absolute():
                target = root / target
            target = target.resolve()
            root = target.parent
        else:
            target = root / ".env"

        file_values: dict[str, str] = {}
        if target.is_file():
            file_values = {
                key: value
                for key, value in dotenv_values(target).items()
                if value is not None
            }
        else:
            allow_env_only = os.getenv("ONETECH_AO_ALLOW_ENV_ONLY", "").strip().casefold()
            if allow_env_only not in {"1", "true", "yes", "on"}:
                raise ConfigurationError(f"Fichier de configuration introuvable: {target}")

        # Explicit process/container variables override the file without
        # mutating ``os.environ``.  This keeps repeated Settings.load() calls
        # isolated (notably the unit + integration test suite).
        def env(name: str, default: str | None = None) -> str | None:
            if name in os.environ:
                return os.environ[name]
            return file_values.get(name, default)

        required = {}
        for name in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
            value = env(name)
            if value is None or not value.strip():
                raise ConfigurationError(f"Variable requise absente dans .env: {name}")
            required[name] = value.strip()

        try:
            port = int(env("POSTGRES_PORT", "5432") or "5432")
        except ValueError as exc:
            raise ConfigurationError("POSTGRES_PORT doit être un entier") from exc

        if not 1 <= port <= 65535:
            raise ConfigurationError("POSTGRES_PORT doit être compris entre 1 et 65535")

        document_root_raw = (env("DOCUMENT_ROOT", "data/documents") or "data/documents").strip()
        document_root = Path(document_root_raw)
        if not document_root.is_absolute():
            document_root = root / document_root
        document_root = document_root.resolve()
        if not document_root.is_relative_to(root):
            raise ConfigurationError("DOCUMENT_ROOT doit rester dans le workspace")

        def positive_int(name: str, default: int) -> int:
            try:
                value = int(env(name, str(default)) or str(default))
            except ValueError as exc:
                raise ConfigurationError(f"{name} doit être un entier") from exc
            if value < 1:
                raise ConfigurationError(f"{name} doit être supérieur à zéro")
            return value

        def boolean(name: str, default: bool) -> bool:
            raw = (env(name, "true" if default else "false") or "").strip().casefold()
            if raw in {"1", "true", "yes", "on"}:
                return True
            if raw in {"0", "false", "no", "off"}:
                return False
            raise ConfigurationError(
                f"{name} doit etre un booleen (true/false, yes/no, 1/0)"
            )

        ocr_languages = (env("DOCUMENT_OCR_LANGUAGES", "fra+ara+eng") or "").strip()
        if not ocr_languages or not re.fullmatch(r"[A-Za-z0-9_+-]+", ocr_languages):
            raise ConfigurationError("DOCUMENT_OCR_LANGUAGES est invalide")

        def command(name: str, default: str) -> str:
            value = (env(name, default) or "").strip()
            if not value or "\x00" in value:
                raise ConfigurationError(f"{name} est invalide")
            return value

        document_max_pdf_pages = positive_int("DOCUMENT_MAX_PDF_PAGES", 500)
        document_ocr_max_pages = positive_int("DOCUMENT_OCR_MAX_PAGES", 50)
        if document_ocr_max_pages > document_max_pdf_pages:
            raise ConfigurationError(
                "DOCUMENT_OCR_MAX_PAGES ne peut pas depasser DOCUMENT_MAX_PDF_PAGES"
            )
        document_ocr_dpi = positive_int("DOCUMENT_OCR_DPI", 200)
        if not 72 <= document_ocr_dpi <= 600:
            raise ConfigurationError("DOCUMENT_OCR_DPI doit etre compris entre 72 et 600")

        return cls(
            postgres_db=required["POSTGRES_DB"],
            postgres_user=required["POSTGRES_USER"],
            postgres_password=required["POSTGRES_PASSWORD"],
            postgres_host=(env("POSTGRES_HOST", "127.0.0.1") or "").strip() or "127.0.0.1",
            postgres_port=port,
            project_root=root,
            document_root=document_root,
            document_max_bytes=positive_int("DOCUMENT_MAX_BYTES", 25 * 1024 * 1024),
            document_max_uncompressed_bytes=positive_int(
                "DOCUMENT_MAX_UNCOMPRESSED_BYTES", 100 * 1024 * 1024
            ),
            document_max_text_chars=positive_int(
                "DOCUMENT_MAX_TEXT_CHARS", 5_000_000
            ),
            document_max_pdf_pages=document_max_pdf_pages,
            document_ocr_enabled=boolean("DOCUMENT_OCR_ENABLED", True),
            document_ocr_languages=ocr_languages,
            document_ocr_max_pages=document_ocr_max_pages,
            document_ocr_dpi=document_ocr_dpi,
            document_ocr_max_render_bytes=positive_int(
                "DOCUMENT_OCR_MAX_RENDER_BYTES", 150 * 1024 * 1024
            ),
            document_ocr_timeout_seconds=positive_int(
                "DOCUMENT_OCR_TIMEOUT_SECONDS", 90
            ),
            document_conversion_timeout_seconds=positive_int(
                "DOCUMENT_CONVERSION_TIMEOUT_SECONDS", 120
            ),
            tesseract_command=command("TESSERACT_COMMAND", "tesseract"),
            pdftoppm_command=command("PDFTOPPM_COMMAND", "pdftoppm"),
            libreoffice_command=command("LIBREOFFICE_COMMAND", "libreoffice"),
        )

    @property
    def database_kwargs(self) -> dict[str, Any]:
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "connect_timeout": 5,
            "application_name": "onetech_ao",
        }

    @property
    def http_timeout(self) -> tuple[float, float]:
        return (self.http_connect_timeout, self.http_read_timeout)

    def redact(self, message: object, max_length: int = 500) -> str:
        text = " ".join(str(message).split())
        secrets = [
            self.postgres_password,
            os.getenv("OPENCLAW_GATEWAY_TOKEN", ""),
            os.getenv("AUTOMATION_API_TOKEN", ""),
            os.getenv("N8N_ENCRYPTION_KEY", ""),
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
        ]
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[SECRET MASQUÉ]")
        return text[:max_length]
