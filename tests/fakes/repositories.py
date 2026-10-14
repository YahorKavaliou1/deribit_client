from collections.abc import Sequence

from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker


class InMemoryPriceRepository:
    """In-memory ``PriceRepository`` with the same query semantics as the SQL one."""

    def __init__(self, records: Sequence[PriceRecord] = ()) -> None:
        self.records: list[PriceRecord] = list(records)

    async def add_many(self, records: Sequence[PriceRecord]) -> int:
        stored = {(record.ticker, record.timestamp) for record in self.records}
        new = [record for record in records if (record.ticker, record.timestamp) not in stored]
        self.records.extend(new)
        return len(new)

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None:
        records = self._newest_first(ticker)
        return records[0] if records else None

    async def find(
        self, ticker: Ticker, pagination: Pagination, time_range: TimeRange | None = None
    ) -> list[PriceRecord]:
        time_range = time_range or TimeRange()
        matching = [
            record
            for record in self._newest_first(ticker)
            if (time_range.start is None or record.timestamp >= time_range.start)
            and (time_range.end is None or record.timestamp <= time_range.end)
        ]
        return matching[pagination.offset : pagination.offset + pagination.limit]

    def _newest_first(self, ticker: Ticker) -> list[PriceRecord]:
        return sorted(
            (record for record in self.records if record.ticker == ticker),
            key=lambda record: record.timestamp,
            reverse=True,
        )
