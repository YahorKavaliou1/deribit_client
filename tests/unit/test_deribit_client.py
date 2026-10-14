import asyncio
import socket
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app.clients.deribit import (
    DeribitApiError,
    DeribitClient,
    DeribitResponseError,
    DeribitUnavailableError,
)
from app.domain.tickers import Ticker
from app.services.ports import PriceSource

TIMEOUT_SECONDS = 0.5


@dataclass
class FakeDeribit:
    """Local HTTP server standing in for Deribit; responds with a configured reply."""

    status: int = 200
    body: str = ""
    delay_seconds: float = 0
    received_queries: list[dict[str, str]] = field(default_factory=list)

    def reply(self, body: str, *, status: int = 200, delay_seconds: float = 0) -> None:
        self.body, self.status, self.delay_seconds = body, status, delay_seconds

    async def handle_index_price(self, request: web.Request) -> web.Response:
        self.received_queries.append(dict(request.query))
        await asyncio.sleep(self.delay_seconds)
        return web.Response(status=self.status, text=self.body, content_type="application/json")


def success_body(index_price: str) -> str:
    # Raw body keeps the number literal exactly as Deribit sends it.
    return (
        '{"jsonrpc":"2.0","result":{"estimated_delivery_price":1,'
        f'"index_price":{index_price}}},"usIn":1,"usOut":2,"usDiff":1,"testnet":false}}'
    )


@pytest.fixture
def deribit() -> FakeDeribit:
    return FakeDeribit()


@pytest.fixture
async def base_url(deribit: FakeDeribit) -> AsyncIterator[str]:
    app = web.Application()
    app.router.add_get("/api/v2/public/get_index_price", deribit.handle_index_price)
    async with TestServer(app) as server:
        yield str(server.make_url("/api/v2"))


@pytest.fixture
async def client(base_url: str) -> AsyncIterator[DeribitClient]:
    async with DeribitClient(base_url, timeout_seconds=TIMEOUT_SECONDS) as client:
        yield client


async def test_client_satisfies_price_source_protocol(client: DeribitClient) -> None:
    source: PriceSource = client
    assert source is client


async def test_get_index_price_requests_ticker_index(
    client: DeribitClient, deribit: FakeDeribit
) -> None:
    deribit.reply(success_body("81681.37"))

    await client.get_index_price(Ticker.ETH_USD)

    assert deribit.received_queries == [{"index_name": "eth_usd"}]


async def test_base_url_with_trailing_slash_is_supported(
    base_url: str, deribit: FakeDeribit
) -> None:
    deribit.reply(success_body("1"))

    async with DeribitClient(f"{base_url}/", timeout_seconds=TIMEOUT_SECONDS) as client:
        assert await client.get_index_price(Ticker.BTC_USD) == Decimal("1")


async def test_get_index_price_keeps_exact_decimal(
    client: DeribitClient, deribit: FakeDeribit
) -> None:
    # 17 significant digits: a float round trip would change the value.
    deribit.reply(success_body("81681.370000000001"))

    assert await client.get_index_price(Ticker.BTC_USD) == Decimal("81681.370000000001")


async def test_get_index_price_accepts_integer_price(
    client: DeribitClient, deribit: FakeDeribit
) -> None:
    deribit.reply(success_body("81681"))

    assert await client.get_index_price(Ticker.BTC_USD) == Decimal("81681")


async def test_json_rpc_error_raises_api_error(client: DeribitClient, deribit: FakeDeribit) -> None:
    deribit.reply(
        '{"jsonrpc":"2.0","error":{"code":-32602,"message":"Invalid params"}}', status=400
    )

    with pytest.raises(DeribitApiError) as error:
        await client.get_index_price(Ticker.BTC_USD)

    assert (error.value.code, error.value.message) == (-32602, "Invalid params")


@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_server_errors_and_rate_limit_raise_unavailable(
    client: DeribitClient, deribit: FakeDeribit, status: int
) -> None:
    deribit.reply("", status=status)

    with pytest.raises(DeribitUnavailableError, match=str(status)):
        await client.get_index_price(Ticker.BTC_USD)


async def test_timeout_raises_unavailable(client: DeribitClient, deribit: FakeDeribit) -> None:
    deribit.reply(success_body("1"), delay_seconds=TIMEOUT_SECONDS * 4)

    with pytest.raises(DeribitUnavailableError):
        await client.get_index_price(Ticker.BTC_USD)


async def test_connection_failure_raises_unavailable() -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed_port = sock.getsockname()[1]

    async with DeribitClient(
        f"http://127.0.0.1:{closed_port}/api/v2", timeout_seconds=TIMEOUT_SECONDS
    ) as client:
        with pytest.raises(DeribitUnavailableError):
            await client.get_index_price(Ticker.BTC_USD)


@pytest.mark.parametrize(
    "body",
    [
        "<html>maintenance</html>",
        "[]",
        '{"jsonrpc":"2.0"}',
        '{"jsonrpc":"2.0","result":{}}',
        '{"jsonrpc":"2.0","result":{"index_price":"81681.37"}}',
    ],
    ids=["not-json", "not-object", "no-result", "no-price", "price-not-number"],
)
async def test_malformed_response_raises_response_error(
    client: DeribitClient, deribit: FakeDeribit, body: str
) -> None:
    deribit.reply(body)

    with pytest.raises(DeribitResponseError):
        await client.get_index_price(Ticker.BTC_USD)


async def test_client_requires_context_manager() -> None:
    client = DeribitClient("http://127.0.0.1/api/v2", timeout_seconds=TIMEOUT_SECONDS)

    with pytest.raises(RuntimeError, match="context manager"):
        await client.get_index_price(Ticker.BTC_USD)


async def test_session_is_closed_on_exit(base_url: str, deribit: FakeDeribit) -> None:
    deribit.reply(success_body("1"))
    async with DeribitClient(base_url, timeout_seconds=TIMEOUT_SECONDS) as client:
        await client.get_index_price(Ticker.BTC_USD)

    with pytest.raises(RuntimeError):
        await client.get_index_price(Ticker.BTC_USD)
