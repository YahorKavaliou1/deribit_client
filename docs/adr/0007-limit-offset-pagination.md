# 0007. Limit/offset pagination

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Two tickers collected once a minute produce about 2 880 rows per day. Returning
"all saved data" for a ticker without pagination grows unbounded.

## Decision

List endpoints ("all data" and the date filter) accept `limit` and `offset` query
parameters:

- `limit`: default `100`, maximum `1000`;
- `offset`: default `0`;
- results are ordered by timestamp, newest first.

## Alternatives considered

- **No pagination** — simplest, but responses grow without bound.
- **Cursor (keyset) pagination** — stable and efficient at deep offsets, but more complex
  than needed for this data volume.

## Consequences

- Bounded response size and query cost.
- Deep offsets are less efficient than keyset pagination; acceptable at this scale and can
  be revisited in a superseding ADR.
