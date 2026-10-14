# 0013. Integration tests against real PostgreSQL via Testcontainers

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The repository relies on PostgreSQL-specific behaviour (`INSERT ... ON CONFLICT DO
NOTHING ... RETURNING`, `NUMERIC` precision, inclusive range filters, ordering and
pagination). Unit tests with fakes cannot verify the SQL itself, and SQLite behaves
differently.

## Decision

- Integration tests live in `tests/integration` and are marked `integration`.
- A session-scoped fixture starts a throwaway PostgreSQL container with **Testcontainers**,
  using the same image as Docker Compose (`postgres:17-alpine`), and applies the real
  **Alembic migrations** (so migrations are tested too).
- Each test runs inside an outer transaction that is rolled back afterwards, keeping tests
  isolated and fast. `Database` session commit/rollback behaviour is tested separately
  with explicit cleanup.
- CI runs them in the regular test job: GitHub-hosted Ubuntu runners provide Docker.
- Locally, `pytest -m "not integration"` runs only unit tests when Docker is unavailable.

## Alternatives considered

- **Postgres service container in CI + env variables** — works in CI, but local runs need a
  manually started database and configuration.
- **SQLite in-memory** — fast, but no `ON CONFLICT ... RETURNING` parity, different
  `NUMERIC` semantics; tests would not reflect production.
- **Mocking `AsyncSession`** — tests the calls, not the queries.

## Consequences

- Docker is required for the full test suite.
- The first run pulls the image; subsequent runs start the container in a couple of
  seconds.
