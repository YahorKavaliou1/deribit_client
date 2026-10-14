from collections.abc import Sequence

import pytest
from celery import Celery

from app.clients.deribit import DeribitApiError, DeribitUnavailableError
from app.core.config import CelerySettings, DatabaseSettings, DeribitSettings, Settings
from app.domain.tickers import Ticker
from app.services.price_collector import CollectionResult
from app.worker.celery_app import create_celery_app
from app.worker.tasks import CollectPricesTask

BROKER_URL = "amqp://guest:guest@rabbitmq:5672//"


class ScriptedCollection:
    """Stands in for ``CollectPricesTask._collect``: returns prepared failures per call."""

    def __init__(self, *failures_per_call: dict[Ticker, Exception]) -> None:
        self._failures_per_call = list(failures_per_call)
        self.calls: list[list[Ticker]] = []

    async def __call__(self, tickers: Sequence[Ticker]) -> CollectionResult:
        self.calls.append(list(tickers))
        failures = self._failures_per_call.pop(0) if self._failures_per_call else {}
        return CollectionResult(records=(), inserted=0, failures=failures)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database=DatabaseSettings(user="u", password="p", db="d", _env_file=None),
        celery=CelerySettings(
            broker_url=BROKER_URL, price_fetch_interval_seconds=60, _env_file=None
        ),
        deribit=DeribitSettings(_env_file=None),
    )


@pytest.fixture
def celery_app(settings: Settings) -> Celery:
    celery_app = create_celery_app(settings)
    celery_app.conf.task_always_eager = True
    return celery_app


@pytest.fixture
def task(celery_app: Celery) -> CollectPricesTask:
    task = celery_app.tasks[CollectPricesTask.name]
    assert isinstance(task, CollectPricesTask)
    return task


def test_app_uses_configured_broker(celery_app: Celery) -> None:
    assert celery_app.conf.broker_url == BROKER_URL


def test_control_and_event_queues_are_exclusive_for_rabbitmq_4(celery_app: Celery) -> None:
    assert celery_app.conf.control_queue_exclusive is True
    assert celery_app.conf.event_queue_exclusive is True


def test_beat_runs_collection_every_interval_and_drops_stale_runs(celery_app: Celery) -> None:
    assert celery_app.conf.beat_schedule == {
        "collect-prices": {
            "task": "prices.collect",
            "schedule": 60,
            "options": {"expires": 60},
        }
    }


def test_task_is_bound_to_the_app(celery_app: Celery, task: CollectPricesTask) -> None:
    assert task.app is celery_app


def test_collects_all_tickers_by_default(
    task: CollectPricesTask, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = ScriptedCollection()
    monkeypatch.setattr(task, "_collect", collection)

    result = task.apply()

    assert result.successful()
    assert collection.calls == [[Ticker.BTC_USD, Ticker.ETH_USD]]


def test_collects_requested_tickers(
    task: CollectPricesTask, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = ScriptedCollection()
    monkeypatch.setattr(task, "_collect", collection)

    task.apply(kwargs={"tickers": ["eth_usd"]})

    assert collection.calls == [[Ticker.ETH_USD]]


def test_retries_only_tickers_with_transient_failures(
    task: CollectPricesTask, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = ScriptedCollection({Ticker.BTC_USD: DeribitUnavailableError("timeout")})
    monkeypatch.setattr(task, "_collect", collection)

    result = task.apply()

    assert result.successful()
    assert collection.calls == [[Ticker.BTC_USD, Ticker.ETH_USD], [Ticker.BTC_USD]]


@pytest.mark.parametrize(
    "error", [DeribitApiError(-32602, "Invalid params"), ValueError("bad price")]
)
def test_permanent_failures_are_not_retried(
    task: CollectPricesTask, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    collection = ScriptedCollection({Ticker.BTC_USD: error})
    monkeypatch.setattr(task, "_collect", collection)

    result = task.apply()

    assert result.successful()
    assert len(collection.calls) == 1


def test_gives_up_after_max_retries(
    task: CollectPricesTask, monkeypatch: pytest.MonkeyPatch
) -> None:
    transient: dict[Ticker, Exception] = {Ticker.BTC_USD: DeribitUnavailableError("down")}
    collection = ScriptedCollection(*[transient] * 10)
    monkeypatch.setattr(task, "_collect", collection)

    result = task.apply()

    assert result.failed()
    assert len(collection.calls) == 1 + CollectPricesTask.max_retries
