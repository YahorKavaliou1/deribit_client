import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import DatabaseSettings
from app.db import models  # noqa: F401  # registers models on Base.metadata
from app.db.base import Base

target_metadata = Base.metadata


def run_migrations_offline(url: URL) -> None:
    """Emit migration SQL to stdout without connecting to the database."""
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online(url: URL) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def main() -> None:
    if context.config.config_file_name is not None:
        fileConfig(context.config.config_file_name)

    url = DatabaseSettings().url
    if context.is_offline_mode():
        run_migrations_offline(url)
    else:
        asyncio.run(run_migrations_online(url))


main()
