from __future__ import annotations

from pathlib import Path

import pytest

from onetech_ao.config import Settings


def _clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def test_settings_supports_explicit_container_environment_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker can run the CLI without mounting a secret .env file."""

    _clear_database_environment(monkeypatch)
    monkeypatch.setenv("ONETECH_AO_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ONETECH_AO_ALLOW_ENV_ONLY", "true")
    monkeypatch.setenv("POSTGRES_DB", "container_db")
    monkeypatch.setenv("POSTGRES_USER", "container_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "container_secret")

    settings = Settings.load()

    assert settings.project_root == tmp_path.resolve()
    assert settings.document_root == (tmp_path / "data" / "documents").resolve()
    assert settings.postgres_db == "container_db"
    assert settings.postgres_host == "127.0.0.1"


def test_settings_uses_explicit_config_file_parent_as_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_database_environment(monkeypatch)
    monkeypatch.delenv("ONETECH_AO_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("ONETECH_AO_ALLOW_ENV_ONLY", raising=False)
    env_file = tmp_path / "worker.env"
    env_file.write_text(
        "\n".join(
            (
                "POSTGRES_DB=explicit_db",
                "POSTGRES_USER=explicit_user",
                "POSTGRES_PASSWORD=explicit_secret",
                "DOCUMENT_ROOT=data/custom-documents",
            )
        ),
        encoding="utf-8",
    )

    settings = Settings.load(env_file=env_file)

    assert settings.project_root == tmp_path.resolve()
    assert settings.document_root == (tmp_path / "data" / "custom-documents").resolve()
    assert settings.postgres_db == "explicit_db"
