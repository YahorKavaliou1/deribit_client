from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker
from app.services.ports import PriceRepository


class PriceNotFoundError(Exception):
    def __init__(self, ticker: Ticker) -> None:
        super().__init__(f"No prices stored for {ticker}")
        self.ticker = ticker


class PriceQueryService:
    """Read-side use cases behind the public API."""

    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    async def get_all(self, ticker: Ticker, pagination: Pagination) -> list[PriceRecord]:
        return await self._repository.find(ticker, pagination)

    async def get_latest(self, ticker: Ticker) -> PriceRecord:
        record = await self._repository.get_latest(ticker)
        if record is None:
            raise PriceNotFoundError(ticker)
        return record

    async def get_by_period(
        self, ticker: Ticker, time_range: TimeRange, pagination: Pagination
    ) -> list[PriceRecord]:
        return await self._repository.find(ticker, pagination, time_range)
