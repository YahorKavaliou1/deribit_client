import json
from decimal import Decimal
from functools import partial
from types import TracebackType
from typing import Any, Self

import aiohttp

from app.domain.tickers import Ticker

# Parse JSON numbers as Decimal so prices never pass through float.
_decimal_json_loads = partial(json.loads, parse_float=Decimal, parse_int=Decimal)


class DeribitError(Exception):
    """Base class for Deribit client errors."""


class DeribitUnavailableError(DeribitError):
    """Network failure, timeout, rate limit or server error; the request may be retried."""


class DeribitApiError(DeribitError):
    """Deribit rejected the request with a JSON-RPC error."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"Deribit API error {code}: {message}")
        self.code = code
        self.message = message


class DeribitResponseError(DeribitError):
    """Deribit returned a response the client cannot interpret."""


class DeribitClient:
    """Async client for the public Deribit HTTP API (JSON-RPC over GET).

    Owns one ``aiohttp.ClientSession`` for its lifetime; use as an async context manager::

        async with DeribitClient(base_url, timeout_seconds=10) as client:
            price = await client.get_index_price(Ticker.BTC_USD)
    """

    _INDEX_PRICE_METHOD = "public/get_index_price"

    def __init__(self, base_url: str, *, timeout_seconds: float) -> None:
        # aiohttp joins relative paths only onto a base URL ending with a slash.
        self._base_url = f"{base_url.rstrip('/')}/"
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        self._session = aiohttp.ClientSession(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_index_price(self, ticker: Ticker) -> Decimal:
        result = await self._call(self._INDEX_PRICE_METHOD, {"index_name": ticker.value})
        price = result.get("index_price")
        if not isinstance(price, Decimal):
            raise DeribitResponseError(f"Missing or invalid index_price for {ticker}: {result}")
        return price

    async def _call(self, method: str, params: dict[str, str]) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("DeribitClient must be used as an async context manager")

        try:
            async with self._session.get(method, params=params) as response:
                if response.status == 429 or response.status >= 500:
                    raise DeribitUnavailableError(f"Deribit responded with HTTP {response.status}")
                payload = await self._read_json(response)
        except (aiohttp.ClientError, TimeoutError) as error:
            raise DeribitUnavailableError(f"Request to Deribit failed: {error!r}") from error

        return self._unwrap(payload)

    @staticmethod
    async def _read_json(response: aiohttp.ClientResponse) -> Any:
        try:
            return await response.json(loads=_decimal_json_loads, content_type=None)
        except ValueError as error:
            raise DeribitResponseError(
                f"Deribit returned non-JSON body (HTTP {response.status})"
            ) from error

    @staticmethod
    def _unwrap(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise DeribitResponseError(f"Unexpected JSON-RPC payload: {payload!r}")

        error = payload.get("error")
        if isinstance(error, dict):
            raise DeribitApiError(code=int(error.get("code", 0)), message=str(error.get("message")))

        result = payload.get("result")
        if not isinstance(result, dict):
            raise DeribitResponseError(f"JSON-RPC payload has no result: {payload!r}")
        return result
