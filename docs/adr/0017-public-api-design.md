# 0017. Public API design

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The API must expose three GET methods (all prices of a currency, the latest price, prices
filtered by date), each with a mandatory `ticker` query parameter.

## Decision

**Endpoints** (versioned under `/api/v1`):

| Method | Path                     | Query parameters                                         |
|--------|--------------------------|----------------------------------------------------------|
| GET    | `/api/v1/prices`         | `ticker`, `limit`, `offset`                              |
| GET    | `/api/v1/prices/latest`  | `ticker`                                                 |
| GET    | `/api/v1/prices/by-date` | `ticker`, `date_from`, `date_to`, `limit`, `offset`      |

- `ticker` is typed as the `Ticker` enum: missing or unknown values return `422`, and the
  allowed values appear in the OpenAPI schema ([0005](0005-supported-tickers-as-enum.md)).
- Date range and pagination follow [0006](0006-date-filter-as-timestamp-range.md) and
  [0007](0007-limit-offset-pagination.md); they are parsed by reusable dependencies into
  the `TimeRange` and `Pagination` value objects, so their validation lives in one place.
- List endpoints return an envelope `{"items": [...], "limit": n, "offset": n}`; the
  latest-price endpoint returns a single object or `404` when nothing is stored.
- **Prices are serialized as strings** (`"81681.37"`), Pydantic's default for `Decimal`,
  so clients receive the exact stored value; JSON numbers are commonly parsed as binary
  floats.
- `/api/v1` prefix leaves room for incompatible changes without breaking clients.

**Structure:**

- A `PriceQueryService` holds the read use cases and raises a domain
  `PriceNotFoundError`; an exception handler registered in the app factory maps it to
  `404`. Routes contain no business logic.
- Dependency chain per request: `Database` (from `app.state`) → transactional session →
  `SqlAlchemyPriceRepository` → `PriceQueryService`.
- `create_app(settings=None)` builds the app; the lifespan creates and disposes the
  `Database`. Uvicorn runs it with `--factory`, so there is no module-level app instance.
  Module-level router and `Annotated` aliases are immutable declarations, not state.

**Testing:** HTTP-layer unit tests override `get_price_query_service` with a service over
an in-memory repository (no lifespan, no database); integration tests run the full app,
lifespan included, against the Testcontainers PostgreSQL. Starlette's `TestClient` uses
`httpx2` (plain `httpx` is deprecated for it).

## Alternatives considered

- **Routes calling the repository directly** — fewer files, but HTTP concerns and the
  "not found" rule would mix, and the service layer would be bypassed for reads.
- **Prices as JSON numbers** — friendlier for quick scripts, but may lose precision on the
  client side.
- **`date_from`/`date_to` on `/prices` instead of a separate endpoint** — the assignment
  lists the date filter as a distinct method, so it gets its own path.

## Consequences

- OpenAPI docs at `/docs` describe tickers, bounds and error responses accurately.
- Clients must parse `price` as a decimal string.
