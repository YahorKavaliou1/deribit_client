import asyncio
from collections.abc import Mapping, Sequence
from decimal import Decimal

import pytest

from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker
from app.services.price_collector import PriceCollector

NOW = 1_760_000_000.75


class FakePriceSource:
    def __init__(self, prices: Mapping[Ticker, Decimal | BaseException]) -> None:
        self._prices = prices
        self.requested: list[Ticker] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def get_index_price(self, ticker: Ticker) -> Decimal:
        self.requested.append(ticker)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0)  # yield so concurrent requests overlap
        self.in_flight -= 1

        outcome = self._prices[ticker]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakePriceRepository:
    def __init__(self) -> None:
        self.saved: list[PriceRecord] = []

    async def add_many(self, records: Sequence[PriceRecord]) -> int:
        self.saved.extend(records)
        return len(records)

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None:
        raise NotImplementedError

    async def find(
        self, ticker: Ticker, pagination: Pagination, time_range: TimeRange | None = None
    ) -> list[PriceRecord]:
        raise NotImplementedError


def make_collector(
    prices: Mapping[Ticker, Decimal | BaseException],
) -> tuple[PriceCollector, FakePriceSource, FakePriceRepository]:
    source, repository = FakePriceSource(prices), FakePriceRepository()
    return PriceCollector(source, repository, clock=lambda: NOW), source, repository


async def test_collects_all_tickers_with_one_truncated_timestamp() -> None:
    collector, _, repository = make_collector(
        {Ticker.BTC_USD: Decimal("81681.37"), Ticker.ETH_USD: Decimal("2434.78")}
    )

    result = await collector.collect()

    expected = (
        PriceRecord(Ticker.BTC_USD, Decimal("81681.37"), 1_760_000_000),
        PriceRecord(Ticker.ETH_USD, Decimal("2434.78"), 1_760_000_000),
    )
    assert result.records == expected
    assert repository.saved == list(expected)
    assert result.inserted == 2
    assert result.failures == {}


async def test_fetches_tickers_concurrently() -> None:
    collector, source, _ = make_collector(
        {Ticker.BTC_USD: Decimal("1"), Ticker.ETH_USD: Decimal("2")}
    )

    await collector.collect()

    assert source.max_in_flight == 2


async def test_collects_only_requested_tickers() -> None:
    collector, source, repository = make_collector({Ticker.ETH_USD: Decimal("2")})

    result = await collector.collect([Ticker.ETH_USD])

    assert source.requested == [Ticker.ETH_USD]
    assert [record.ticker for record in repository.saved] == [Ticker.ETH_USD]
    assert result.failed_tickers == ()


async def test_failed_ticker_does_not_prevent_storing_others() -> None:
    error = ConnectionError("deribit is down")
    collector, _, repository = make_collector({Ticker.BTC_USD: error, Ticker.ETH_USD: Decimal("2")})

    result = await collector.collect()

    assert [record.ticker for record in repository.saved] == [Ticker.ETH_USD]
    assert result.failures == {Ticker.BTC_USD: error}
    assert result.failed_tickers == (Ticker.BTC_USD,)


async def test_invalid_price_is_reported_as_failure() -> None:
    collector, _, repository = make_collector(
        {Ticker.BTC_USD: Decimal("0"), Ticker.ETH_USD: Decimal("2")}
    )

    result = await collector.collect()

    assert isinstance(result.failures[Ticker.BTC_USD], ValueError)
    assert [record.ticker for record in repository.saved] == [Ticker.ETH_USD]


async def test_all_tickers_failing_stores_nothing() -> None:
    collector, _, repository = make_collector(
        {Ticker.BTC_USD: TimeoutError(), Ticker.ETH_USD: TimeoutError()}
    )

    result = await collector.collect()

    assert repository.saved == []
    assert result.inserted == 0
    assert result.failed_tickers == (Ticker.BTC_USD, Ticker.ETH_USD)


async def test_cancellation_is_propagated() -> None:
    collector, _, repository = make_collector(
        {Ticker.BTC_USD: asyncio.CancelledError(), Ticker.ETH_USD: Decimal("2")}
    )

    with pytest.raises(asyncio.CancelledError):
        await collector.collect()

    assert repository.saved == []
