# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The assignment is evaluated, among other things, on the ability to explain the decisions
taken. Decisions discussed in chat or code review are easily lost.

## Decision

Record every architecturally significant decision as an Architecture Decision Record (ADR)
in `docs/adr`, using the lightweight format described by Michael Nygard
(see [template.md](template.md)).

- Files are numbered sequentially: `NNNN-short-title.md`.
- Decisions still under discussion are recorded with status **Proposed**.
- An accepted ADR is not rewritten; a change of mind is a new ADR that supersedes it.
- The README "Design decisions" section summarises the ADRs and links to them.

## Consequences

- The reasoning behind the code is versioned together with the code.
- Small overhead of writing a short document per decision.
