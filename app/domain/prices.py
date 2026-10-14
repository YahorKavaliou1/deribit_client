from dataclasses import dataclass
from decimal import Decimal

from app.domain.tickers import Ticker


@dataclass(frozen=True, slots=True)
class PriceRecord:
    """Index price of a currency at a moment in time.

    ``timestamp`` is UNIX time in seconds.
    """

    ticker: Ticker
    price: Decimal
    timestamp: int

    def __post_init__(self) -> None:
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError(f"Price must be a positive finite number, got {self.price}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
