# 0014. Deribit HTTP client design

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The collector needs the index price of each ticker from Deribit's public API
(`GET /api/v2/public/get_index_price?index_name=btc_usd`, JSON-RPC 2.0 envelope). The
optional requirement asks for aiohttp. The Celery task must decide whether a failure is
worth retrying.

## Decision

- **`DeribitClient` is an async context manager** that owns a single
  `aiohttp.ClientSession` (connection pooling, base URL, total timeout). Using it outside
  `async with` raises `RuntimeError`, so a session can never leak.
- **HTTP GET with query parameters**, not WebSocket: one request per ticker per minute
  does not justify a persistent connection, and public methods need no authentication.
- **Prices are parsed as `Decimal` directly from JSON** (`json.loads(parse_float=Decimal)`),
  so they never pass through `float`.
- **Error hierarchy** rooted at `DeribitError`:
  - `DeribitUnavailableError` — network failure, timeout, HTTP 429 or 5xx; retryable;
  - `DeribitApiError` — JSON-RPC `error` object (e.g. invalid params); not retryable;
  - `DeribitResponseError` — non-JSON body or unexpected payload shape; not retryable.
- The service layer depends on a `PriceSource` protocol (`get_index_price(ticker)`), not on
  the client class.
- Retries are **not** done inside the client; the Celery task owns the retry policy.
- **Tests run the client against a local `aiohttp` test server** that plays Deribit,
  covering real HTTP, timeouts and refused connections.

## Alternatives considered

- **WebSocket API with subscriptions** — real-time, but needs reconnection handling and
  is overkill for one poll per minute.
- **`aioresponses` for tests** — version 0.7.9 is incompatible with aiohttp 3.14 (it
  patches aiohttp internals), which is exactly the fragility of mocking a library's
  internals.
- **Retries inside the client (e.g. with backoff)** — would duplicate and hide the retry
  policy of the Celery task.

## Consequences

- Callers can distinguish transient from permanent failures by exception type.
- A dedicated session per client instance; the task creates one client per run.
