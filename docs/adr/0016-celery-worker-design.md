# 0016. Celery worker design

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Prices must be collected every minute with Celery. The assignment penalises global
variables, while the usual Celery setup is a module-level `app = Celery(...)` with
`@app.task` functions, discovered by `celery -A module`.

## Decision

- **App factory.** `create_celery_app(settings)` builds the app: broker URL, beat schedule
  and task registration. Nothing is created at import time.
- **Entry point without a global app.** The Celery CLI (`-A`) can only find a module-level
  instance and does not call factories, so processes start with
  `python -m app.worker worker|beat ...`, which runs
  `create_celery_app(Settings()).start(argv)`. All regular Celery CLI options still apply.
- **Class-based task.** `CollectPricesTask` (name `prices.collect`) receives `Settings` in
  its constructor and is registered via `app.register_task(...)`. Each run creates its own
  `DeribitClient`, `Database` and session inside one `asyncio.run(...)`
  ([0003](0003-single-async-database-driver.md)), so nothing is shared between runs.
- **Retry policy** (implements [0015](0015-partial-failures-in-price-collection.md)):
  successful prices are committed; only tickers that failed with
  `DeribitUnavailableError` are retried, passing `tickers=[...]` to the retry.
  Up to 3 retries, 10 s apart, so all retries fit into one collection interval. Permanent
  errors (`DeribitApiError`, invalid values) are logged and not retried.
- **Stale runs are dropped.** Beat messages expire after one interval: if workers were
  down, queued runs are not executed in a burst later; the next scheduled run covers them.
- **No result backend** (`task_ignore_result=True`); outcomes are logged.
- **RabbitMQ 4 compatibility.** RabbitMQ 4 rejects transient non-exclusive queues, which
  Celery uses for its control (pidbox) and event queues; found during an end-to-end run.
  `control_queue_exclusive` and `event_queue_exclusive` are enabled.
- **Typing.** `celery-types` provides stubs for mypy strict mode.

## Alternatives considered

- **Module-level app + `@app.task`** — idiomatic but a global by definition; tasks are bound
  to import-time configuration.
- **`@shared_task`** — avoids importing the app in task modules, but the CLI still needs a
  module-level app, and a function task cannot hold injected settings.
- **Retrying the whole run** — would re-fetch and duplicate already stored tickers.
- **Late acknowledgement (`acks_late`)** — redelivers on worker crash but can re-execute a
  committed run; not worth it for a value that is re-collected a minute later.

## Consequences

- Workers and beat are started via `python -m app.worker`, not `celery -A`.
- The database connection is held while prices are fetched (bounded by the HTTP timeout);
  negligible at one run per minute.
