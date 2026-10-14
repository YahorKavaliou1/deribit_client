from enum import StrEnum


class Ticker(StrEnum):
    """Currencies whose index price is collected and served by the API.

    Values match Deribit index names (``public/get_index_price?index_name=...``).
    """

    BTC_USD = "btc_usd"
    ETH_USD = "eth_usd"
