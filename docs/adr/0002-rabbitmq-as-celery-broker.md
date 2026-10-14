# 0002. RabbitMQ as the Celery broker

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Celery requires a message broker: Celery beat publishes a `collect prices` message every
minute and a worker consumes it. The workload is tiny (one task per minute). The optional
requirement suggests running the application in two containers (app and database).

## Decision

Use **RabbitMQ** as the broker (`amqp://`). Task results are not stored
(`ignore_result=True`), so no result backend is configured.

We accept an extra container in Docker Compose; the "two containers" requirement is
optional and a dedicated broker is the more conventional and robust setup.

## Alternatives considered

- **Redis** — popular and simple, but RabbitMQ is the reference broker for Celery with
  full feature support (acknowledgements, routing, remote control).
- **PostgreSQL via the kombu `sqlalchemy` transport** — would keep two containers, but the
  transport is experimental, polling-based, lacks broadcast/remote control and needs an
  extra synchronous driver.
- **Filesystem transport** — no dependencies, but requires beat and worker to share a
  directory on the same host; non-standard.

## Consequences

- One more service (`rabbitmq`) in Docker Compose, with a healthcheck.
- `CELERY_BROKER_URL` is validated as `AmqpDsn` at startup.
- The broker can still be swapped by changing `CELERY_BROKER_URL` and the URL type.
