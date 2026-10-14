from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_pagination, get_price_query_service, get_time_range
from app.api.schemas import ErrorResponse, PricePageResponse, PriceResponse
from app.domain.prices import PriceRecord
from app.domain.queries import Pagination, TimeRange
from app.domain.tickers import Ticker
from app.services.price_query import PriceQueryService

router = APIRouter(prefix="/prices", tags=["prices"])

TickerQuery = Annotated[Ticker, Query(description="Currency index name.")]
Service = Annotated[PriceQueryService, Depends(get_price_query_service)]


def to_page(records: list[PriceRecord], pagination: Pagination) -> PricePageResponse:
    return PricePageResponse(
        items=[PriceResponse.model_validate(record) for record in records],
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("", summary="All stored prices of a currency, newest first")
async def get_prices(
    ticker: TickerQuery,
    pagination: Annotated[Pagination, Depends(get_pagination)],
    service: Service,
) -> PricePageResponse:
    return to_page(await service.get_all(ticker, pagination), pagination)


@router.get(
    "/latest",
    summary="Latest stored price of a currency",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_latest_price(ticker: TickerQuery, service: Service) -> PriceResponse:
    return PriceResponse.model_validate(await service.get_latest(ticker))


@router.get("/by-date", summary="Prices of a currency within a UNIX timestamp range")
async def get_prices_by_date(
    ticker: TickerQuery,
    time_range: Annotated[TimeRange, Depends(get_time_range)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    service: Service,
) -> PricePageResponse:
    return to_page(await service.get_by_period(ticker, time_range, pagination), pagination)
