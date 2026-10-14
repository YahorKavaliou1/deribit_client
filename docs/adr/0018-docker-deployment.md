# 0018. Docker deployment

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The application consists of an HTTP API, a Celery worker, Celery beat and database
migrations, plus PostgreSQL and RabbitMQ ([0002](0002-rabbitmq-as-celery-broker.md)).
It must be runnable with a single command.

## Decision

- **One application image, several roles.** The `Dockerfile` builds one image; Compose
  runs it as `migrate` (one-shot `alembic upgrade head`), `api` (uvicorn, default command),
  `worker` and `beat` (`python -m app.worker ...`, see
  [0016](0016-celery-worker-design.md)). One process per container: each role is
  restarted, scaled and logged independently.
- **Multi-stage build.** Dependencies are installed into a virtualenv in a builder stage;
  the runtime stage copies only the virtualenv and the code (`app`, `migrations`,
  `alembic.ini`). Tests, docs and tooling are excluded via `.dockerignore`.
- **Non-root user.** Processes run as the `app` system user. Beat keeps its schedule state
  in `/tmp`, because the application directory is not writable for that user.
- **Startup ordering.** `migrate` waits for a healthy database; `api`, `worker` and `beat`
  wait for healthy PostgreSQL and RabbitMQ and for `migrate` to complete successfully.
  The API has a healthcheck (`/openapi.json`), so it does not need an extra endpoint
  outside the specified API.
- **Configuration.** All containers read the same `.env`
  ([0004](0004-configuration-via-pydantic-settings.md)). Application containers override
  only the hosts (`POSTGRES_HOST=db`, broker URL with `rabbitmq`), so the same `.env`
  works for local runs against published ports and inside Compose. The API host port is
  configurable via `API_PORT`.
- **CI** validates the Compose file and builds the image on every push.

## Alternatives considered

- **Single application container running API, worker and beat under supervisord** — fits
  the optional "two containers" wording more literally, but couples lifecycles, hides
  crashes from Docker and prevents scaling the worker separately.
- **Running migrations on API startup** — races when several API replicas start, and mixes
  deployment steps with serving traffic.
- **Separate images per role** — duplicated builds of identical code and dependencies.

## Consequences

- `cp .env.example .env && docker compose up --build` starts the whole system.
- Six services in Compose (two infrastructure, one one-shot, three long-running) instead
  of the suggested two containers; the deviation is deliberate and documented here and in
  [0002](0002-rabbitmq-as-celery-broker.md).
