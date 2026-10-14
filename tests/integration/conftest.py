from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.core.config import DatabaseSettings

# Keep in sync with the db service in docker-compose.yml.
POSTGRES_IMAGE = "postgres:17-alpine"
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def database_settings() -> Iterator[DatabaseSettings]:
    """Start a throwaway PostgreSQL and apply the real Alembic migrations to it."""
    with PostgresContainer(
        POSTGRES_IMAGE, username="test", password="test", dbname="test"
    ) as container:
        environment = {
            "POSTGRES_USER": container.username,
            "POSTGRES_PASSWORD": container.password,
            "POSTGRES_DB": container.dbname,
            "POSTGRES_HOST": container.get_container_host_ip(),
            "POSTGRES_PORT": str(container.get_exposed_port(container.port)),
        }
        with pytest.MonkeyPatch.context() as monkeypatch:
            for name, value in environment.items():
                monkeypatch.setenv(name, value)
            # migrations/env.py reads the same POSTGRES_* variables as the application.
            command.upgrade(Config(ALEMBIC_INI), "head")
            settings = DatabaseSettings(_env_file=None)
        yield settings


@pytest.fixture
async def session(database_settings: DatabaseSettings) -> AsyncIterator[AsyncSession]:
    """Session inside an outer transaction that is rolled back after each test."""
    engine = create_async_engine(database_settings.url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()
