from celery import Celery

from app.core.config import Settings
from app.worker.tasks import CollectPricesTask


def create_celery_app(settings: Settings) -> Celery:
    """Build a fully configured Celery app: broker, the collection task and its schedule."""
    celery_app = Celery("deribit_client")
    interval = settings.celery.price_fetch_interval_seconds
    celery_app.conf.update(
        broker_url=str(settings.celery.broker_url),
        broker_connection_retry_on_startup=True,
        task_ignore_result=True,
        # RabbitMQ 4 rejects transient non-exclusive queues; Celery's control (pidbox)
        # and event queues are transient, so they must be exclusive.
        control_queue_exclusive=True,
        event_queue_exclusive=True,
        timezone="UTC",
        beat_schedule={
            "collect-prices": {
                "task": CollectPricesTask.name,
                "schedule": interval,
                # A run that waited in the queue longer than one interval is stale:
                # the next scheduled run already covers it.
                "options": {"expires": interval},
            },
        },
    )
    celery_app.register_task(CollectPricesTask(settings))
    return celery_app
