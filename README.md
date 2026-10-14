# Deribit Client

A service that fetches the current index price of `btc_usd` and `eth_usd` from the
[Deribit](https://docs.deribit.com/) exchange every minute (via Celery), stores the ticker,
price and UNIX timestamp in PostgreSQL, and exposes the saved data through an external
FastAPI-based API.

## How it works

```
Celery beat ──(every 60 s)──► RabbitMQ ──► Celery worker ──► Deribit API (aiohttp)
                                                 │
                                                 ▼
                         FastAPI  ◄────────  PostgreSQL
```

1. **Celery beat** publishes a `prices.collect` task every minute.
2. The **worker** requests the index price of every ticker from Deribit concurrently and
   stores all prices of one run with a shared timestamp. If a ticker fails with a
   transient error, only that ticker is retried.
3. The **API** serves the stored prices.

## What's inside

| Path                | Contents                                                       |
|---------------------|----------------------------------------------------------------|
| `app/domain`        | `Ticker` enum and value objects (`PriceRecord`, `TimeRange`, `Pagination`) |
| `app/clients`       | Deribit HTTP client (aiohttp)                                  |
| `app/db`            | SQLAlchemy model and the `Database` session manager            |
| `app/repositories`  | PostgreSQL repository                                          |
| `app/services`      | Price collection and query use cases, repository/source protocols |
| `app/worker`        | Celery app factory, collection task, entry point               |
| `app/api`, `app/main.py` | FastAPI routes, schemas, dependencies, app factory        |
| `migrations`        | Alembic migrations                                             |
| `tests`             | Unit tests and integration tests (PostgreSQL via Testcontainers) |
| `docs/adr`          | Architecture Decision Records                                  |

## API

All methods are `GET` and require the `ticker` query parameter (`btc_usd` or `eth_usd`).
Interactive docs: http://localhost:8000/docs.

| Endpoint                     | Description                         | Extra parameters                         |
|------------------------------|-------------------------------------|------------------------------------------|
| `/api/v1/prices`             | All stored prices, newest first     | `limit` (1–1000, default 100), `offset`  |
| `/api/v1/prices/latest`      | Latest price (`404` if none stored) | —                                        |
| `/api/v1/prices/by-date`     | Prices within a time range          | `date_from`, `date_to` (UNIX seconds, inclusive, optional), `limit`, `offset` |

```bash
curl "http://localhost:8000/api/v1/prices/latest?ticker=btc_usd"
```

```json
{"ticker": "btc_usd", "price": "81526.49", "timestamp": 1792001782}
```

Prices are returned as strings to preserve exact decimal precision.

## Running with Docker

Requires Docker with Compose.

```bash
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, RabbitMQ, a one-shot migration job, the API (port `API_PORT`,
default `8000`), the Celery worker and Celery beat. Prices appear within a minute.

## Running locally

Requires Python 3.12 and Docker (for PostgreSQL and RabbitMQ).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d db rabbitmq
alembic upgrade head
```

Then start each process in its own terminal:

```bash
uvicorn app.main:create_app --factory --reload
python -m app.worker worker --loglevel=INFO
python -m app.worker beat --loglevel=INFO
```

Configuration is read from environment variables / `.env`; see [.env.example](.env.example).

## Tests and checks

```bash
pytest                       # all tests; integration tests need Docker
pytest -m "not integration"  # unit tests only
ruff check . && ruff format --check . && mypy app tests
```

GitHub Actions runs linters, tests and the Docker build on every push.

## Design decisions

Every decision is recorded as an Architecture Decision Record in
[docs/adr](docs/adr/README.md), with context and rejected alternatives. Highlights:

- **No global state:** settings, the Celery app and the FastAPI app are built by
  factories; Celery starts via `python -m app.worker` instead of `celery -A`
  ([0004](docs/adr/0004-configuration-via-pydantic-settings.md),
  [0016](docs/adr/0016-celery-worker-design.md)).
- **Layered architecture** with services depending on protocols, not on SQLAlchemy or
  aiohttp ([0009](docs/adr/0009-layered-architecture.md)).
- **Exact prices:** `Decimal` end to end, from JSON parsing to `NUMERIC` storage and
  string serialization ([0010](docs/adr/0010-price-storage-schema.md),
  [0014](docs/adr/0014-deribit-client.md)).
- **Partial failures:** successful prices are stored, only failed tickers are retried
  ([0015](docs/adr/0015-partial-failures-in-price-collection.md)).
- **RabbitMQ** as the broker and one image running in several containers
  ([0002](docs/adr/0002-rabbitmq-as-celery-broker.md),
  [0018](docs/adr/0018-docker-deployment.md)).
