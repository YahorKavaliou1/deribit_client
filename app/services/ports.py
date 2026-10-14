from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker


class PriceRepository(Protocol):
    async def add_many(self, records: Sequence[PriceRecord]) -> int:
        """Store records, skipping already stored ``(ticker, timestamp)`` pairs.

        Returns the number of records actually inserted.
        """
        ...

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None: ...

    async def find(
        self, ticker: Ticker, pagination: Pagination, time_range: TimeRange | None = None
    ) -> list[PriceRecord]:
        """Return records of a ticker, newest first, optionally within a time range."""
        ...


class PriceSource(Protocol):
    async def get_index_price(self, ticker: Ticker) -> Decimal: ...
