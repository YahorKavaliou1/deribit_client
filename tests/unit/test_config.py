import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import CelerySettings, DatabaseSettings, DeribitSettings


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep a developer's local .env and shell variables out of the tests."""
    monkeypatch.chdir(tmp_path)
    for prefix in ("POSTGRES_", "CELERY_", "DERIBIT_"):
        for name in [key for key in os.environ if key.startswith(prefix)]:
            monkeypatch.delenv(name)


def test_database_settings_build_asyncpg_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/word")
    monkeypatch.setenv("POSTGRES_DB", "prices")
    monkeypatch.setenv("POSTGRES_HOST", "db")

    url = DatabaseSettings().url

    assert url.drivername == "postgresql+asyncpg"
    assert url.password == "p@ss/word"
    assert url.render_as_string(hide_password=False) == (
        "postgresql+asyncpg://user:p%40ss%2Fword@db:5432/prices"
    )


def test_database_settings_require_credentials() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings()


def test_celery_settings_reject_non_amqp_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    with pytest.raises(ValidationError):
        CelerySettings()


def test_deribit_settings_defaults() -> None:
    settings = DeribitSettings()

    assert str(settings.base_url) == "https://www.deribit.com/api/v2"
    assert settings.request_timeout_seconds == 10.0
