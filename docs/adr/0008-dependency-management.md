# 0008. Pinned requirements files for dependencies

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The project needs reproducible installs locally and in Docker.

## Decision

- Runtime dependencies are pinned in `requirements.txt`, development dependencies in
  `requirements-dev.txt` (which includes the former).
- `pyproject.toml` holds project metadata and tool configuration (pytest, ruff, mypy) but
  does not duplicate dependencies.

## Alternatives considered

- **Dependencies in `pyproject.toml` + lock file (uv/poetry)** — stronger reproducibility of
  transitive dependencies, but requirements files are the format requested and are
  understood by any tooling.

## Consequences

- Plain `pip install -r requirements.txt` works everywhere, including the Docker image.
- Transitive dependencies are not locked.
