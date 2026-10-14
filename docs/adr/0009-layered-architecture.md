# 0009. Layered architecture with protocol-based dependencies

- **Status:** Proposed
- **Date:** 2026-10-14

## Context

The same business logic is used by two entry points (Celery task and FastAPI) and must be
unit-testable without a database or network.

## Decision

Split the code into layers, with dependencies pointing inwards:

- `domain` — framework-free core: `Ticker` enum, the `PriceRecord` value object and query
  value objects (`TimeRange`, `Pagination`), each validating its own invariants;
- `clients` — Deribit HTTP client (aiohttp);
- `db` — ORM models, engine and session management;
- `repositories` — data access;
- `services` — business logic (`PriceCollector`, price queries); the clock is injected
  as a plain `Callable[[], float]` (default `time.time`), which is enough for deterministic
  tests without a dedicated protocol;
- `api` and `worker` — thin entry points that wire dependencies.

Services depend on `typing.Protocol` interfaces of the client and repository, and on an
injected clock, rather than on concrete classes. Services exchange domain dataclasses, not
ORM models.

- The protocols live in `app/services/ports.py`: the consumer owns the interface, so the
  service layer does not import SQLAlchemy or aiohttp.
- Repositories work inside a session passed by the caller and never commit; transaction
  boundaries are owned by the entry point (one `Database.session()` per request or task
  run).
- The repository exposes a single `find(ticker, pagination, time_range=None)` instead of
  separate "all" and "by period" methods: "all data" is a query with an open time range.

## Alternatives considered

- **Logic directly in routes/tasks** — less code, but duplicated between entry points and
  hard to test.

## Consequences

- Unit tests use simple fakes instead of mocks of SQLAlchemy/aiohttp internals.
- Slightly more files and indirection.
