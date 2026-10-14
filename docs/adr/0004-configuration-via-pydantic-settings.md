# 0004. Configuration via pydantic-settings without a global instance

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The application has three configurable concerns (database, Celery, Deribit) and runs as
several processes (API, worker, beat). The assignment explicitly penalises global
variables.

## Decision

- Settings are typed `pydantic-settings` classes grouped by concern, each with its own
  environment prefix: `POSTGRES_*`, `CELERY_*`, `DERIBIT_*`.
- `DatabaseSettings` reuses the variable names of the official postgres image, so one
  `.env` file configures both the container and the application.
- A frozen root `Settings` model aggregates the groups.
- There is **no module-level settings instance**: application factories
  (`create_app`, `create_celery_app`) create `Settings` and pass it down explicitly.
- Values are validated at startup (`SecretStr` for passwords, `AmqpDsn` for the broker,
  `HttpUrl`, positive timeouts and intervals).

## Alternatives considered

- **`get_settings()` with `lru_cache`** — idiomatic in FastAPI docs, but effectively a
  hidden global and harder to override in tests.
- **A single flat settings class / nested delimiter (`DATABASE__USER`)** — would not reuse
  the postgres image variables.

## Consequences

- Misconfiguration fails fast at process start.
- Tests construct settings explicitly and do not depend on a developer's `.env`.
