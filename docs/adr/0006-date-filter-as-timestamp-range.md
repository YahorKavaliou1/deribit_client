# 0006. Date filter as a UNIX timestamp range

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The API must return currency prices filtered by date. Prices are stored with a UNIX
timestamp.

## Decision

The filter endpoint accepts a range: `date_from` and `date_to`, both UNIX timestamps
(seconds), matching the storage format.

- Both bounds are inclusive.
- Either bound may be omitted (open-ended range).
- `date_from > date_to` is rejected with `422`.
- Results are paginated as described in [0007](0007-limit-offset-pagination.md).

## Alternatives considered

- **Single calendar date (`date=2026-10-14`)** — cannot express arbitrary periods and
  requires choosing a time zone.
- **ISO 8601 datetimes** — more readable, but inconsistent with the stored UNIX timestamps.

## Consequences

- One endpoint covers a single day, any period and open-ended ranges.
- Served by the `(ticker, timestamp)` index.
