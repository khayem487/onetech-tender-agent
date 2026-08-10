"""Configuration du collecteur, chargée depuis le fichier .env local."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


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

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        target = env_file or (PROJECT_ROOT / ".env")
        if not target.is_file():
            raise ConfigurationError(f"Fichier de configuration introuvable: {target}")

        load_dotenv(target, override=False)

        required = {}
        for name in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
            value = os.getenv(name)
            if value is None or not value.strip():
                raise ConfigurationError(f"Variable requise absente dans .env: {name}")
            required[name] = value.strip()

        try:
            port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError as exc:
            raise ConfigurationError("POSTGRES_PORT doit être un entier") from exc

        if not 1 <= port <= 65535:
            raise ConfigurationError("POSTGRES_PORT doit être compris entre 1 et 65535")

        document_root_raw = os.getenv("DOCUMENT_ROOT", "data/documents").strip()
        document_root = Path(document_root_raw)
        if not document_root.is_absolute():
            document_root = target.resolve().parent / document_root
        document_root = document_root.resolve()
        project_root = target.resolve().parent
        if not document_root.is_relative_to(project_root):
            raise ConfigurationError("DOCUMENT_ROOT doit rester dans le workspace")

        def positive_int(name: str, default: int) -> int:
            try:
                value = int(os.getenv(name, str(default)))
            except ValueError as exc:
                raise ConfigurationError(f"{name} doit être un entier") from exc
            if value < 1:
                raise ConfigurationError(f"{name} doit être supérieur à zéro")
            return value

        return cls(
            postgres_db=required["POSTGRES_DB"],
            postgres_user=required["POSTGRES_USER"],
            postgres_password=required["POSTGRES_PASSWORD"],
            postgres_port=port,
            project_root=project_root,
            document_root=document_root,
            document_max_bytes=positive_int("DOCUMENT_MAX_BYTES", 25 * 1024 * 1024),
            document_max_uncompressed_bytes=positive_int(
                "DOCUMENT_MAX_UNCOMPRESSED_BYTES", 100 * 1024 * 1024
            ),
            document_max_text_chars=positive_int(
                "DOCUMENT_MAX_TEXT_CHARS", 5_000_000
            ),
            document_max_pdf_pages=positive_int("DOCUMENT_MAX_PDF_PAGES", 500),
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
        if self.postgres_password:
            text = text.replace(self.postgres_password, "[SECRET MASQUÉ]")
        return text[:max_length]
