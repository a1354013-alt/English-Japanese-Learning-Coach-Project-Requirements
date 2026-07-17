# ADR 0001: Incremental Database Extraction for v1.5

- Status: Accepted
- Date: 2026-07-16

## Context

`backend/database.py` is intentionally still the runtime facade in `v1.4.1`, but upcoming persisted-chat and learning-session work would become harder to validate if new storage code keeps expanding the same module without boundaries.

At the same time, this maintenance release explicitly avoids a broad persistence refactor.

## Decision

We will introduce protocol-level repository boundaries now and defer concrete extraction to `v1.5`.

The first extraction targets are:

1. Persisted chat history
2. Guided learning-session persistence

The existing `Database` class remains the live facade until protocol-backed adapters can be introduced with regression coverage.

## Consequences

- `v1.4.1` stays low-risk because runtime persistence behavior does not change.
- `v1.5` feature work can target narrow interfaces instead of growing the monolith first.
- Repository extraction can happen feature-by-feature instead of as a one-shot rewrite.
- Test coverage becomes the migration safety net for every extraction step.

## Rejected alternatives

- Full database-module split in `v1.4.1`: rejected because it adds maintenance-release risk without delivering requested learner value.
- Leaving no boundaries until the feature lands: rejected because it would make the eventual extraction harder to scope and test.
