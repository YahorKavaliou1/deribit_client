# 0010. Price storage schema

- **Status:** Proposed
- **Date:** 2026-10-14

## Context

For every fetch we store the ticker, the index price and the time as a UNIX timestamp.
All API queries filter by ticker and order or filter by time.

## Decision

Single table `prices`:

| Column      | Type         | Notes                                 |
|-------------|--------------|---------------------------------------|
| `id`        | `BIGINT` PK  | identity                              |
| `ticker`    | `VARCHAR`    | value of the `Ticker` enum            |
| `price`     | `NUMERIC`    | exact decimal; no float rounding      |
| `timestamp` | `BIGINT`     | UNIX time, seconds                    |

Composite index on `(ticker, timestamp)`, which serves all three API queries.
The schema is managed by Alembic migrations.

## Open questions

- Timestamp source: the collector's clock at fetch time vs. the Deribit response time
  (`usOut`).
- Whether to add a unique constraint on `(ticker, timestamp)` to make retries idempotent.

## Consequences

- Prices keep the exact precision returned by Deribit (`Decimal` end to end).
