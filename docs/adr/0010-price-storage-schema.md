# 0010. Price storage schema

- **Status:** Accepted
- **Date:** 2026-10-14
- **Amended by:** [0015](0015-partial-failures-in-price-collection.md) (idempotency of retries)

## Context

For every fetch we store the ticker, the index price and the time as a UNIX timestamp.
All API queries filter by ticker and order or filter by time. Celery delivers tasks
at least once, so the same collection run may be executed more than once.

## Decision

Single table `prices`:

| Column      | Type                 | Notes                                        |
|-------------|----------------------|----------------------------------------------|
| `id`        | `BIGINT` identity PK |                                              |
| `ticker`    | `VARCHAR(16)`        | value of the `Ticker` enum (non-native enum) |
| `price`     | `NUMERIC`            | exact decimal; no float rounding             |
| `timestamp` | `BIGINT`             | UNIX time, seconds                           |

- **Unique constraint `(ticker, timestamp)`.** Inserts use `ON CONFLICT DO NOTHING`, so a
  redelivered or retried task does not create duplicates. The constraint's index also
  serves all three API queries, so no separate index is needed.
- **Timestamp source: the collector's clock**, captured once per collection run. All
  tickers fetched in one run share the same timestamp, which makes the unique constraint
  meaningful and keeps rows of one run aligned.
- **Ticker as `VARCHAR`, not a native PostgreSQL enum.** Adding a ticker requires no
  `ALTER TYPE` migration; validation happens in the application via the `Ticker` enum.
- Constraint names follow a SQLAlchemy naming convention, so migrations are deterministic.
- The schema is managed by Alembic (async template). `migrations/env.py` reads the URL
  from `DatabaseSettings`, so there is a single source of connection settings.

## Alternatives considered

- **Deribit response time (`usOut`) as the timestamp** — exchange time, but it differs per
  ticker and per retry, so duplicates would not be detected.
- **Separate non-unique index `(ticker, timestamp)`** — redundant once the unique
  constraint exists.
- **`DOUBLE PRECISION` for price** — loses precision; `Decimal` is used end to end.

## Consequences

- Retries are idempotent at the database level.
- The stored time is when the price was collected, not the exchange's internal time;
  the difference is the HTTP round trip.
