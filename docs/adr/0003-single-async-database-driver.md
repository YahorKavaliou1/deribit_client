# 0003. Single async database driver (asyncpg)

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The FastAPI application is asynchronous. The Deribit client uses aiohttp, so price
collection is asynchronous as well. Celery workers, however, execute tasks synchronously.

## Decision

Use **SQLAlchemy 2 (asyncio) + asyncpg** as the only database driver for both the API and
the Celery worker. A Celery task bridges into async code with `asyncio.run(...)`, creating
the HTTP client and database engine per run. Alembic uses its async template.

## Alternatives considered

- **Sync driver (psycopg) in the worker + asyncpg in the API** — two drivers, two session
  setups and duplicated repository code (sync and async variants).
- **Sync everywhere** — contradicts the aiohttp requirement and blocks the API event loop.

## Consequences

- One repository implementation shared by the API and the worker.
- Each task run creates and disposes its own event loop and connections; negligible
  overhead at one task per minute, and no state shared between runs.
