from decimal import Decimal

import pytest

from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker
from app.services.price_query import PriceNotFoundError, PriceQueryService
from tests.fakes.repositories import InMemoryPriceRepository

RECORDS = [PriceRecord(Ticker.BTC_USD, Decimal("100"), timestamp) for timestamp in (10, 20, 30)] + [
    PriceRecord(Ticker.ETH_USD, Decimal("5"), 40)
]


@pytest.fixture
def service() -> PriceQueryService:
    return PriceQueryService(InMemoryPriceRepository(RECORDS))


async def test_get_all_returns_ticker_records_newest_first(service: PriceQueryService) -> None:
    records = await service.get_all(Ticker.BTC_USD, Pagination(limit=2))

    assert [record.timestamp for record in records] == [30, 20]


async def test_get_latest_returns_newest_record(service: PriceQueryService) -> None:
    assert (await service.get_latest(Ticker.ETH_USD)).timestamp == 40


async def test_get_latest_raises_when_nothing_stored() -> None:
    service = PriceQueryService(InMemoryPriceRepository())

    with pytest.raises(PriceNotFoundError) as error:
        await service.get_latest(Ticker.BTC_USD)

    assert error.value.ticker is Ticker.BTC_USD


async def test_get_by_period_filters_by_time_range(service: PriceQueryService) -> None:
    records = await service.get_by_period(
        Ticker.BTC_USD, TimeRange(start=15, end=30), Pagination(limit=10)
    )

    assert [record.timestamp for record in records] == [30, 20]
