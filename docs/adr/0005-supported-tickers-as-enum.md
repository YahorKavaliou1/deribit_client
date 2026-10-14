# 0005. Supported tickers defined by an enum, not configuration

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The assignment fixes the set of currencies: `btc_usd` and `eth_usd`. The list is needed in
two places: the collector (what to fetch) and the API (validating the `ticker` parameter).

## Decision

Define a `Ticker` `StrEnum` as the single source of truth. The collector iterates over its
members; the API uses it as the type of the `ticker` query parameter, so unknown tickers
are rejected with `422` and appear as an enum in the OpenAPI schema.

## Alternatives considered

- **Configurable list (`DERIBIT_TICKERS`)** — two sources of truth that can diverge: the
  collector could store tickers the API rejects, or vice versa.

## Consequences

- Adding a currency is a code change (one enum member), which is acceptable for a fixed
  scope and keeps API documentation accurate.
