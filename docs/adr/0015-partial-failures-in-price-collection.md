# 0015. Partial failures in price collection

- **Status:** Accepted
- **Date:** 2026-10-14
- **Amends:** [0010](0010-price-storage-schema.md) (idempotency of retries)

## Context

One collection run fetches several tickers. Any of them can fail independently: a network
error, a JSON-RPC error, or a value rejected by the domain (e.g. a zero price).

[0010](0010-price-storage-schema.md) claims that the `(ticker, timestamp)` unique constraint
makes retried runs idempotent. That only holds if a retry reuses the same timestamp. The
timestamp is captured from the clock when a run starts, so a re-executed run gets a new
timestamp, and re-fetching an already stored ticker would create a second row.

## Decision

- `PriceCollector.collect(tickers)` fetches the tickers **concurrently**
  (`asyncio.gather(..., return_exceptions=True)`) and stores **every price that succeeded**,
  all with the timestamp captured once at the start of the run.
- Failures are **returned, not raised**: `CollectionResult` contains the stored records,
  the number of inserted rows and a `failures` mapping `ticker → exception`. Raising would
  roll back the caller's transaction and lose the successful prices.
- Cancellation (`CancelledError` and other non-`Exception` errors) is always propagated.
- The service does not know Deribit exceptions; the Celery task (step 7) inspects
  `failures` and **retries only the failed tickers whose error is retryable**. A ticker
  that was stored is never re-fetched, so retries do not create duplicates.
- The unique constraint stays as a safety net for overlapping runs within the same
  second and as the query index.

## Alternatives considered

- **All-or-nothing run** — one permanently failing ticker would block storing the others.
- **Raise after storing** — the exception would roll back the caller's transaction.
- **Timestamps floored to the collection interval** (e.g. start of the minute) — would make
  any re-execution within the same interval idempotent via the unique constraint, but
  stores a time up to a minute earlier than the actual fetch and silently drops a run when
  beat jitter puts two runs into one interval.

## Consequences

- A partially failed run stores what it can; the failed ticker is retried on its own and
  gets the timestamp of the retry.
- A run re-executed after the transaction committed (e.g. a worker crash between commit
  and the task finishing with late acknowledgement) can still store a second row with a
  later timestamp; this is accepted at one-minute granularity.
