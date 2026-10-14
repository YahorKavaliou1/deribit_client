from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, func, select

from app.core.config import DatabaseSettings
from app.db.database import Database
from app.db.models import PriceModel
from app.domain.tickers import Ticker

pytestmark = pytest.mark.integration


@pytest.fixture
async def database(database_settings: DatabaseSettings) -> AsyncIterator[Database]:
    async with Database(database_settings.url) as database:
        yield database
        async with database.session() as session:
            await session.execute(delete(PriceModel))


async def count_prices(database: Database) -> int:
    async with database.session() as session:
        return await session.scalar(select(func.count()).select_from(PriceModel)) or 0


async def test_session_commits_on_success(database: Database) -> None:
    async with database.session() as session:
        session.add(PriceModel(ticker=Ticker.BTC_USD, price=1, timestamp=1))

    assert await count_prices(database) == 1


async def test_session_rolls_back_on_error(database: Database) -> None:
    with pytest.raises(RuntimeError):
        async with database.session() as session:
            session.add(PriceModel(ticker=Ticker.BTC_USD, price=1, timestamp=1))
            await session.flush()
            raise RuntimeError

    assert await count_prices(database) == 0
