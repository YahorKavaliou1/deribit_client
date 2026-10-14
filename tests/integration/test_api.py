import asyncio
from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import CelerySettings, DatabaseSettings, DeribitSettings, Settings
from app.db.database import Database
from app.db.models import PriceModel
from app.domain.prices import PriceRecord
from app.domain.tickers import Ticker
from app.main import create_app
from app.repositories.prices import SqlAlchemyPriceRepository

pytestmark = pytest.mark.integration

RECORDS = [
    PriceRecord(Ticker.BTC_USD, Decimal("81681.37"), 100),
    PriceRecord(Ticker.BTC_USD, Decimal("81700.01"), 160),
    PriceRecord(Ticker.ETH_USD, Decimal("2434.78"), 100),
]


async def seed(database_settings: DatabaseSettings) -> None:
    async with Database(database_settings.url) as database, database.session() as session:
        await SqlAlchemyPriceRepository(session).add_many(RECORDS)


async def clean(database_settings: DatabaseSettings) -> None:
    async with Database(database_settings.url) as database, database.session() as session:
        await session.execute(delete(PriceModel))


@pytest.fixture
def client(database_settings: DatabaseSettings) -> Iterator[TestClient]:
    """Full application, lifespan included, against the test PostgreSQL."""
    settings = Settings(
        database=database_settings,
        celery=CelerySettings(broker_url="amqp://localhost//", _env_file=None),
        deribit=DeribitSettings(_env_file=None),
    )
    asyncio.run(seed(database_settings))
    with TestClient(create_app(settings)) as client:
        yield client
    asyncio.run(clean(database_settings))


def test_get_prices(client: TestClient) -> None:
    response = client.get("/api/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert [item["price"] for item in response.json()["items"]] == ["81700.01", "81681.37"]


def test_get_latest_price(client: TestClient) -> None:
    response = client.get("/api/v1/prices/latest", params={"ticker": "eth_usd"})

    assert response.json() == {"ticker": "eth_usd", "price": "2434.78", "timestamp": 100}


def test_get_prices_by_date(client: TestClient) -> None:
    response = client.get(
        "/api/v1/prices/by-date", params={"ticker": "btc_usd", "date_from": 150, "date_to": 200}
    )

    assert [item["timestamp"] for item in response.json()["items"]] == [160]
