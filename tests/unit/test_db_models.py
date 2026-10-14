from sqlalchemy import BigInteger, Enum, Numeric, Table, UniqueConstraint

from app.db.models import PriceModel
from app.domain.tickers import Ticker

PRICES_TABLE: Table = PriceModel.metadata.tables[PriceModel.__tablename__]


def test_prices_table_has_unique_ticker_timestamp() -> None:
    unique_constraints = [
        constraint
        for constraint in PRICES_TABLE.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert [[column.name for column in uq.columns] for uq in unique_constraints] == [
        ["ticker", "timestamp"]
    ]
    assert unique_constraints[0].name == "uq_prices_ticker_timestamp"


def test_prices_columns_are_not_nullable() -> None:
    assert all(not column.nullable for column in PRICES_TABLE.columns)


def test_prices_column_types() -> None:
    assert isinstance(PRICES_TABLE.columns["price"].type, Numeric)
    assert isinstance(PRICES_TABLE.columns["timestamp"].type, BigInteger)


def test_ticker_is_stored_as_varchar_by_value() -> None:
    ticker_type = PRICES_TABLE.columns["ticker"].type

    assert isinstance(ticker_type, Enum)
    assert not ticker_type.native_enum
    assert ticker_type.enums == [ticker.value for ticker in Ticker]
