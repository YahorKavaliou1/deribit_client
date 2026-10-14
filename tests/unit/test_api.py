from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_price_query_service
from app.core.config import CelerySettings, DatabaseSettings, DeribitSettings, Settings
from app.domain.prices import PriceRecord
from app.domain.tickers import Ticker
from app.main import create_app
from app.services.price_query import PriceQueryService
from tests.fakes.repositories import InMemoryPriceRepository

BTC = [
    PriceRecord(Ticker.BTC_USD, Decimal("81681.370000000001"), 1_792_000_000 + minute * 60)
    for minute in range(5)
]
ETH = [PriceRecord(Ticker.ETH_USD, Decimal("2434.78"), 1_792_000_000)]


@pytest.fixture
def repository() -> InMemoryPriceRepository:
    return InMemoryPriceRepository(BTC + ETH)


@pytest.fixture
def client(repository: InMemoryPriceRepository) -> Iterator[TestClient]:
    settings = Settings(
        database=DatabaseSettings(user="u", password="p", db="d", _env_file=None),
        celery=CelerySettings(broker_url="amqp://localhost//", _env_file=None),
        deribit=DeribitSettings(_env_file=None),
    )
    app = create_app(settings)
    app.dependency_overrides[get_price_query_service] = lambda: PriceQueryService(repository)
    # Not entering the client's context skips the lifespan, so no database is touched.
    yield TestClient(app)


def timestamps(response_json: dict[str, list[dict[str, object]]]) -> list[object]:
    return [item["timestamp"] for item in response_json["items"]]


@pytest.mark.parametrize(
    "path", ["/api/v1/prices", "/api/v1/prices/latest", "/api/v1/prices/by-date"]
)
def test_ticker_is_required(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "ticker"]


@pytest.mark.parametrize(
    "path", ["/api/v1/prices", "/api/v1/prices/latest", "/api/v1/prices/by-date"]
)
def test_unknown_ticker_is_rejected(client: TestClient, path: str) -> None:
    assert client.get(path, params={"ticker": "doge_usd"}).status_code == 422


def test_get_prices_returns_ticker_prices_newest_first(client: TestClient) -> None:
    response = client.get("/api/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    body = response.json()
    assert timestamps(body) == [record.timestamp for record in reversed(BTC)]
    assert (body["limit"], body["offset"]) == (100, 0)


def test_price_is_serialized_as_exact_decimal_string(client: TestClient) -> None:
    item = client.get("/api/v1/prices", params={"ticker": "btc_usd"}).json()["items"][0]

    assert item == {
        "ticker": "btc_usd",
        "price": "81681.370000000001",
        "timestamp": BTC[-1].timestamp,
    }


def test_get_prices_paginates(client: TestClient) -> None:
    response = client.get("/api/v1/prices", params={"ticker": "btc_usd", "limit": 2, "offset": 1})

    body = response.json()
    assert timestamps(body) == [BTC[3].timestamp, BTC[2].timestamp]
    assert (body["limit"], body["offset"]) == (2, 1)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 1001}, {"offset": -1}])
def test_invalid_pagination_is_rejected(client: TestClient, params: dict[str, int]) -> None:
    response = client.get("/api/v1/prices", params={"ticker": "btc_usd", **params})

    assert response.status_code == 422


def test_get_latest_price(client: TestClient) -> None:
    response = client.get("/api/v1/prices/latest", params={"ticker": "eth_usd"})

    assert response.status_code == 200
    assert response.json() == {"ticker": "eth_usd", "price": "2434.78", "timestamp": 1_792_000_000}


def test_get_latest_price_returns_404_without_data(
    client: TestClient, repository: InMemoryPriceRepository
) -> None:
    repository.records.clear()

    response = client.get("/api/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No prices stored for btc_usd"}


def test_get_prices_by_date_filters_inclusive_range(client: TestClient) -> None:
    response = client.get(
        "/api/v1/prices/by-date",
        params={"ticker": "btc_usd", "date_from": BTC[1].timestamp, "date_to": BTC[3].timestamp},
    )

    assert response.status_code == 200
    assert timestamps(response.json()) == [BTC[3].timestamp, BTC[2].timestamp, BTC[1].timestamp]


def test_get_prices_by_date_supports_open_range(client: TestClient) -> None:
    response = client.get(
        "/api/v1/prices/by-date", params={"ticker": "btc_usd", "date_from": BTC[3].timestamp}
    )

    assert timestamps(response.json()) == [BTC[4].timestamp, BTC[3].timestamp]


def test_get_prices_by_date_paginates(client: TestClient) -> None:
    response = client.get(
        "/api/v1/prices/by-date", params={"ticker": "btc_usd", "limit": 1, "offset": 1}
    )

    assert timestamps(response.json()) == [BTC[3].timestamp]


@pytest.mark.parametrize(
    "params", [{"date_from": 20, "date_to": 10}, {"date_from": -1}, {"date_to": "yesterday"}]
)
def test_get_prices_by_date_rejects_invalid_range(
    client: TestClient, params: dict[str, int | str]
) -> None:
    response = client.get("/api/v1/prices/by-date", params={"ticker": "btc_usd", **params})

    assert response.status_code == 422


def test_all_endpoints_are_get_with_documented_ticker(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths) == {"/api/v1/prices", "/api/v1/prices/latest", "/api/v1/prices/by-date"}
    for operations in paths.values():
        assert set(operations) == {"get"}
        ticker = next(p for p in operations["get"]["parameters"] if p["name"] == "ticker")
        assert ticker["required"] is True
