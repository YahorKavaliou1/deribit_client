from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Database
from app.domain.queries import Pagination, TimeRange
from app.repositories.prices import SqlAlchemyPriceRepository
from app.services.price_query import PriceQueryService

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


async def get_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async with database.session() as session:
        yield session


def get_price_query_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PriceQueryService:
    return PriceQueryService(SqlAlchemyPriceRepository(session))


def get_pagination(
    limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Maximum number of records.")
    ] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip.")] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


def get_time_range(
    date_from: Annotated[
        int | None, Query(ge=0, description="Inclusive lower bound, UNIX seconds.")
    ] = None,
    date_to: Annotated[
        int | None, Query(ge=0, description="Inclusive upper bound, UNIX seconds.")
    ] = None,
) -> TimeRange:
    try:
        return TimeRange(start=date_from, end=date_to)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
