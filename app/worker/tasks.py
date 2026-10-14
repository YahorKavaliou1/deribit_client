import asyncio
from collections.abc import Sequence

from celery import Task
from celery.utils.log import get_task_logger

from app.clients.deribit import DeribitClient, DeribitUnavailableError
from app.core.config import Settings
from app.db.database import Database
from app.domain.tickers import Ticker
from app.repositories.prices import SqlAlchemyPriceRepository
from app.services.price_collector import CollectionResult, PriceCollector


class CollectPricesTask(Task):  # type: ignore[type-arg]  # Task is not subscriptable at runtime
    """Collect index prices of the given tickers (all by default) and store them.

    Prices that were fetched are committed even if other tickers failed. Only tickers
    that failed with a transient error are retried, so stored prices are never duplicated.
    """

    name = "prices.collect"
    max_retries = 3
    default_retry_delay = 10  # seconds; all retries fit into one collection interval
    _logger = get_task_logger(__name__)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(self, tickers: Sequence[str] | None = None) -> None:
        requested = [Ticker(ticker) for ticker in tickers] if tickers else list(Ticker)
        result = asyncio.run(self._collect(requested))
        self._logger.info(
            "Collected %d price(s), inserted %d", len(result.records), result.inserted
        )

        retryable = self._log_failures(result)
        if retryable:
            raise self.retry(kwargs={"tickers": [ticker.value for ticker in retryable]})

    async def _collect(self, tickers: Sequence[Ticker]) -> CollectionResult:
        deribit = self._settings.deribit
        async with (
            DeribitClient(
                str(deribit.base_url), timeout_seconds=deribit.request_timeout_seconds
            ) as client,
            Database(self._settings.database.url) as database,
            database.session() as session,
        ):
            collector = PriceCollector(client, SqlAlchemyPriceRepository(session))
            return await collector.collect(tickers)

    def _log_failures(self, result: CollectionResult) -> list[Ticker]:
        """Log failed tickers and return those worth retrying."""
        retryable: list[Ticker] = []
        for ticker, error in result.failures.items():
            if isinstance(error, DeribitUnavailableError):
                self._logger.warning("Transient failure for %s, will retry: %s", ticker, error)
                retryable.append(ticker)
            else:
                self._logger.error("Permanent failure for %s: %r", ticker, error)
        return retryable
