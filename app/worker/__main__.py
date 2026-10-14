"""Celery entry point: ``python -m app.worker <celery command> [options]``.

Examples::

    python -m app.worker worker --loglevel=INFO
    python -m app.worker beat --loglevel=INFO

Used instead of ``celery -A <module>`` because the Celery CLI requires a module-level app
instance, while the app is built by a factory without global state.
"""

import sys

from app.core.config import Settings
from app.worker.celery_app import create_celery_app


def main() -> None:
    create_celery_app(Settings()).start(argv=sys.argv[1:])


if __name__ == "__main__":
    main()
