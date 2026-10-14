from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker
from app.repositories.prices import SqlAlchemyPriceRepository
from app.services.ports import PriceRepository

pytestmark = pytest.mark.integration

ALL = Pagination(limit=100)


def btc(timestamp: int, price: str = "100") -> PriceRecord:
    return PriceRecord(ticker=Ticker.BTC_USD, price=Decimal(price), timestamp=timestamp)


def eth(timestamp: int, price: str = "10") -> PriceRecord:
    return PriceRecord(ticker=Ticker.ETH_USD, price=Decimal(price), timestamp=timestamp)


@pytest.fixture
def repository(session: AsyncSession) -> PriceRepository:
    return SqlAlchemyPriceRepository(session)


async def test_add_many_returns_number_of_inserted_records(repository: PriceRepository) -> None:
    assert await repository.add_many([btc(1), eth(1)]) == 2


async def test_add_many_with_no_records_is_noop(repository: PriceRepository) -> None:
    assert await repository.add_many([]) == 0


async def test_add_many_skips_already_stored_ticker_and_timestamp(
    repository: PriceRepository,
) -> None:
    await repository.add_many([btc(1, "100")])

    inserted = await repository.add_many([btc(1, "999"), eth(1)])

    assert inserted == 1
    assert await repository.find(Ticker.BTC_USD, ALL) == [btc(1, "100")]


async def test_price_precision_is_preserved(repository: PriceRepository) -> None:
    await repository.add_many([btc(1, "67012.123456789012")])

    assert await repository.get_latest(Ticker.BTC_USD) == btc(1, "67012.123456789012")


async def test_get_latest_returns_newest_record_of_ticker(repository: PriceRepository) -> None:
    await repository.add_many([btc(1), btc(3), btc(2), eth(4)])

    assert await repository.get_latest(Ticker.BTC_USD) == btc(3)


async def test_get_latest_returns_none_without_data(repository: PriceRepository) -> None:
    await repository.add_many([eth(1)])

    assert await repository.get_latest(Ticker.BTC_USD) is None


async def test_find_returns_ticker_records_newest_first(repository: PriceRepository) -> None:
    await repository.add_many([btc(1), eth(2), btc(3), btc(2)])

    assert await repository.find(Ticker.BTC_USD, ALL) == [btc(3), btc(2), btc(1)]


async def test_find_paginates(repository: PriceRepository) -> None:
    await repository.add_many([btc(timestamp) for timestamp in range(1, 6)])

    page = await repository.find(Ticker.BTC_USD, Pagination(limit=2, offset=1))

    assert page == [btc(4), btc(3)]


@pytest.mark.parametrize(
    ("time_range", "expected_timestamps"),
    [
        (TimeRange(start=2, end=4), [4, 3, 2]),
        (TimeRange(start=4), [5, 4]),
        (TimeRange(end=2), [2, 1]),
        (TimeRange(start=3, end=3), [3]),
        (TimeRange(), [5, 4, 3, 2, 1]),
    ],
)
async def test_find_filters_by_inclusive_time_range(
    repository: PriceRepository, time_range: TimeRange, expected_timestamps: list[int]
) -> None:
    await repository.add_many([btc(timestamp) for timestamp in range(1, 6)] + [eth(3)])

    records = await repository.find(Ticker.BTC_USD, ALL, time_range)

    assert [record.timestamp for record in records] == expected_timestamps
