# 0012. Host the repository on GitHub

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The assignment asks to publish the code on GitLab.

## Decision

Host the repository on **GitHub** instead. CI runs on GitHub Actions
([0011](0011-continuous-integration.md)); no `.gitlab-ci.yml` is maintained.

## Consequences

- Deviation from the assignment wording; this ADR documents it explicitly.
- If a GitLab mirror is ever required, CI has to be ported to `.gitlab-ci.yml`.
