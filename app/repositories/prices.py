from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PriceModel
from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker


class SqlAlchemyPriceRepository:
    """PostgreSQL implementation of ``PriceRepository``.

    Works inside the caller's session; transaction boundaries belong to the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, records: Sequence[PriceRecord]) -> int:
        if not records:
            return 0
        statement = (
            insert(PriceModel)
            .values(
                [
                    {"ticker": record.ticker, "price": record.price, "timestamp": record.timestamp}
                    for record in records
                ]
            )
            .on_conflict_do_nothing(index_elements=[PriceModel.ticker, PriceModel.timestamp])
            .returning(PriceModel.id)
        )
        result = await self._session.execute(statement)
        return len(result.all())

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None:
        statement = self._newest_first(ticker).limit(1)
        model = await self._session.scalar(statement)
        return self._to_domain(model) if model is not None else None

    async def find(
        self, ticker: Ticker, pagination: Pagination, time_range: TimeRange | None = None
    ) -> list[PriceRecord]:
        statement = self._newest_first(ticker)
        if time_range is not None and time_range.start is not None:
            statement = statement.where(PriceModel.timestamp >= time_range.start)
        if time_range is not None and time_range.end is not None:
            statement = statement.where(PriceModel.timestamp <= time_range.end)
        statement = statement.limit(pagination.limit).offset(pagination.offset)

        models = await self._session.scalars(statement)
        return [self._to_domain(model) for model in models]

    @staticmethod
    def _newest_first(ticker: Ticker) -> Select[PriceModel]:
        return (
            select(PriceModel)
            .where(PriceModel.ticker == ticker)
            .order_by(PriceModel.timestamp.desc())
        )

    @staticmethod
    def _to_domain(model: PriceModel) -> PriceRecord:
        return PriceRecord(ticker=model.ticker, price=model.price, timestamp=model.timestamp)
