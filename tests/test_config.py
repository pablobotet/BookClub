from pathlib import Path

from pytest import MonkeyPatch

from reading_club.config import Settings


def test_settings_use_local_database_by_default(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.database_url == (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/reading_club"
    )


def test_settings_read_database_url_from_environment(monkeypatch: MonkeyPatch) -> None:
    database_url = "postgresql+asyncpg://reader:secret@localhost:5432/test_club"
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = Settings()

    assert settings.database_url == database_url
