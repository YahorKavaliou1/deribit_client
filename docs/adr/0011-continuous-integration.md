# 0011. Continuous integration on GitHub Actions

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Code quality (clean code, typing) is an evaluation criterion, and regressions should be
caught before review rather than by hand.

## Decision

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push, with parallel
jobs:

- **Lint** — `ruff check`, `ruff format --check`, `mypy` (strict);
- **Tests** — `pytest`;
- **Docker image** — `docker compose config` and `docker build` (added with
  [0018](0018-docker-deployment.md)).

Both jobs use the same Python version as the project (3.12) and install dependencies from
the pinned requirements files ([0008](0008-dependency-management.md)), with the pip cache
keyed on them. Superseded runs on the same ref are cancelled.

## Alternatives considered

- **Single job** — simpler, but lint and test failures are reported together and run
  sequentially.
- **Pre-commit hooks only** — fast feedback locally, but can be skipped and do not protect
  the remote branch.

## Consequences

- Every push gets lint and test feedback within a couple of minutes.
- Tied to GitHub as the hosting platform ([0012](0012-host-repository-on-github.md)).
