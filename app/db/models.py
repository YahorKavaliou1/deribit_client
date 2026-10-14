from decimal import Decimal

from sqlalchemy import BigInteger, Enum, Identity, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.tickers import Ticker


class PriceModel(Base):
    __tablename__ = "prices"
    # Makes repeated deliveries of the same collection task idempotent and also serves
    # as the (ticker, timestamp) index used by every API query.
    __table_args__ = (UniqueConstraint("ticker", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ticker: Mapped[Ticker] = mapped_column(
        # Stored as VARCHAR: adding a ticker needs no ALTER TYPE migration.
        Enum(
            Ticker,
            native_enum=False,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    price: Mapped[Decimal] = mapped_column(Numeric)
    timestamp: Mapped[int] = mapped_column(BigInteger)
