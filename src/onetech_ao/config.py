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

        return cls(
            postgres_db=required["POSTGRES_DB"],
            postgres_user=required["POSTGRES_USER"],
            postgres_password=required["POSTGRES_PASSWORD"],
            postgres_port=port,
            project_root=target.resolve().parent,
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
