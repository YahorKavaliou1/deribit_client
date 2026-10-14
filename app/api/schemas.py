from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.tickers import Ticker


class PriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: Ticker
    price: Decimal = Field(
        description="Index price; serialized as a string to keep exact decimal precision.",
        examples=["81681.37"],
    )
    timestamp: int = Field(description="UNIX time in seconds.", examples=[1792000415])


class PricePageResponse(BaseModel):
    items: list[PriceResponse]
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    detail: str
