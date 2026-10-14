# 0009. Layered architecture with protocol-based dependencies

- **Status:** Proposed
- **Date:** 2026-10-14

## Context

The same business logic is used by two entry points (Celery task and FastAPI) and must be
unit-testable without a database or network.

## Decision

Split the code into layers, with dependencies pointing inwards:

- `domain` — framework-free core: `Ticker` enum and the `PriceRecord` value object with its
  invariants (positive finite price, non-negative timestamp);
- `clients` — Deribit HTTP client (aiohttp);
- `db` — ORM models, engine and session management;
- `repositories` — data access;
- `services` — business logic (`PriceCollector`, price queries);
- `api` and `worker` — thin entry points that wire dependencies.

Services depend on `typing.Protocol` interfaces of the client and repository, and on an
injected clock, rather than on concrete classes. Services exchange domain dataclasses, not
ORM models.

## Alternatives considered

- **Logic directly in routes/tasks** — less code, but duplicated between entry points and
  hard to test.

## Consequences

- Unit tests use simple fakes instead of mocks of SQLAlchemy/aiohttp internals.
- Slightly more files and indirection.
