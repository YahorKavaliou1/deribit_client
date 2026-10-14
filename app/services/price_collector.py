import asyncio
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from app.domain.prices import PriceRecord
from app.domain.tickers import Ticker
from app.services.ports import PriceRepository, PriceSource


@dataclass(frozen=True, slots=True)
class CollectionResult:
    records: tuple[PriceRecord, ...]
    inserted: int
    failures: Mapping[Ticker, Exception]

    @property
    def failed_tickers(self) -> tuple[Ticker, ...]:
        return tuple(self.failures)


class PriceCollector:
    """Fetches current index prices and stores them with one shared timestamp per run.

    Tickers are independent: a failure of one ticker does not prevent storing the others.
    Failures are reported in the result rather than raised, so the caller's transaction
    still commits the successful prices and the caller decides what to retry.
    """

    def __init__(
        self,
        source: PriceSource,
        repository: PriceRepository,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._source = source
        self._repository = repository
        self._clock = clock

    async def collect(self, tickers: Iterable[Ticker] = tuple(Ticker)) -> CollectionResult:
        tickers = tuple(tickers)
        timestamp = int(self._clock())
        outcomes = await asyncio.gather(
            *(self._fetch(ticker, timestamp) for ticker in tickers), return_exceptions=True
        )

        records: list[PriceRecord] = []
        failures: dict[Ticker, Exception] = {}
        for ticker, outcome in zip(tickers, outcomes, strict=True):
            if isinstance(outcome, PriceRecord):
                records.append(outcome)
            elif isinstance(outcome, Exception):
                failures[ticker] = outcome
            else:
                raise outcome  # cancellation and other BaseExceptions must propagate

        inserted = await self._repository.add_many(records)
        return CollectionResult(records=tuple(records), inserted=inserted, failures=failures)

    async def _fetch(self, ticker: Ticker, timestamp: int) -> PriceRecord:
        price = await self._source.get_index_price(ticker)
        return PriceRecord(ticker=ticker, price=price, timestamp=timestamp)
