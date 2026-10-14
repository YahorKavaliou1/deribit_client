# Deribit Client

Every minute fetches the `btc_usd` and `eth_usd` index prices from
[Deribit](https://docs.deribit.com/), stores them in PostgreSQL and serves them via FastAPI.

**Stack:** FastAPI · Celery + RabbitMQ · aiohttp · SQLAlchemy (async) + Alembic · PostgreSQL

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000/docs. The first prices appear within a minute.

## Run locally

Requires Python 3.12 and Docker.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # with uv: uv venv -p 3.12 && uv pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d db rabbitmq
alembic upgrade head

uvicorn app.main:create_app --factory          # API
python -m app.worker worker --loglevel=INFO    # Celery worker
python -m app.worker beat --loglevel=INFO      # Celery beat
```

## API

All endpoints are `GET` and require `ticker` (`btc_usd` | `eth_usd`).

| Endpoint                 | Returns                                    | Parameters                                   |
|--------------------------|--------------------------------------------|----------------------------------------------|
| `/api/v1/prices`         | All prices, newest first                   | `limit` (≤ 1000, default 100), `offset`      |
| `/api/v1/prices/latest`  | Latest price, `404` if none                | —                                            |
| `/api/v1/prices/by-date` | Prices in a range                          | `date_from`, `date_to` (UNIX s, inclusive), `limit`, `offset` |

```json
GET /api/v1/prices/latest?ticker=btc_usd
{"ticker": "btc_usd", "price": "81526.49", "timestamp": 1792001782}
```

## Project structure

```
app/
  domain/        Ticker enum, value objects
  clients/       Deribit client (aiohttp)
  db/            SQLAlchemy model, session management
  repositories/  PostgreSQL repository
  services/      price collection and queries
  worker/        Celery app, task, entry point
  api/, main.py  FastAPI app
migrations/      Alembic
tests/           unit + integration (Testcontainers)
docs/adr/        Architecture Decision Records
```

## Tests

```bash
pytest                       # needs Docker for integration tests
pytest -m "not integration"  # unit tests only
```

CI (GitHub Actions) runs ruff, mypy, tests and the Docker build on every push.

## Design decisions

Each decision with its context and rejected alternatives is in [docs/adr](docs/adr/README.md).
