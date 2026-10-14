from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.prices import PriceRecord
from app.domain.tickers import Ticker


def test_tickers_match_deribit_index_names() -> None:
    assert [ticker.value for ticker in Ticker] == ["btc_usd", "eth_usd"]


def test_ticker_is_parsed_from_string() -> None:
    assert Ticker("eth_usd") is Ticker.ETH_USD


def test_price_record_keeps_exact_decimal() -> None:
    record = PriceRecord(
        ticker=Ticker.BTC_USD, price=Decimal("67012.4512"), timestamp=1_760_000_000
    )

    assert record.price == Decimal("67012.4512")


def test_price_record_is_immutable() -> None:
    record = PriceRecord(ticker=Ticker.BTC_USD, price=Decimal("1"), timestamp=0)

    with pytest.raises(FrozenInstanceError):
        record.price = Decimal("2")  # type: ignore[misc]


@pytest.mark.parametrize(
    "price", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")]
)
def test_price_record_rejects_invalid_price(price: Decimal) -> None:
    with pytest.raises(ValueError, match="Price"):
        PriceRecord(ticker=Ticker.BTC_USD, price=price, timestamp=0)


def test_price_record_rejects_negative_timestamp() -> None:
    with pytest.raises(ValueError, match="Timestamp"):
        PriceRecord(ticker=Ticker.BTC_USD, price=Decimal("1"), timestamp=-1)
