# Release Notes: v1.4.0

## Release Overview

v1.4.0 is the final Adaptive Learning release for the English-Japanese Learning Coach. It promotes the verified v1.4 release-candidate line into a stable local-demo release focused on adaptive study missions, deterministic daily micro lessons, item-level learning intelligence, Traditional Chinese localization, CJK-safe export behavior, and hardened release delivery.

This release remains a local-first portfolio/demo application, not a production multi-user SaaS deployment.

## Main Learner-Facing Capabilities

- Adaptive English and Japanese Daily Study Mission summaries.
- Diagnostic placement flow for learner starting-point selection.
- Daily micro lessons with date-gated progression.
- Canonical micro-lesson generation for concurrent user/day requests.
- Atomic micro-lesson completion that updates XP, progress, activity, and reward events together.
- Item-level SRS for vocabulary, grammar, and sentence patterns.
- Weak-item review intelligence and snowball-aware lesson context.
- Feynman learning support with provider-backed feedback when available and deterministic fallback behavior otherwise.
- Traditional Chinese localization across the learner-facing v1.4 flow.
- CJK-safe PDF export behavior for Japanese and Traditional Chinese content.
- Explicit TTS availability UI and provider-ready backend status.

## Supported Environment

- Python 3.11.x.
- Node.js 22.18.0.
- VS Code F5 startup through the checked-in launch and task configuration.
- Shell-script startup through `start_backend.sh` and `start_frontend.sh`.
- Docker Compose backend validation with `docker compose config`.
- Optional RAG support after installing `backend/requirements-rag.txt` and setting `ENABLE_RAG=true`.

## Known Limitations

- The app uses a single local demo user architecture and does not include production authentication, authorization, user isolation, rate limiting, or audit logging.
- TTS is provider-ready but unavailable by default unless a real provider is configured.
- Chat memory remains process-local.
- Browser recording and pronunciation scoring are not included in v1.4.0.
- RAG dependencies are optional and must be installed separately for RAG-enabled verification.

## Upgrade Notes for Existing SQLite Databases

Existing SQLite databases can be upgraded through the normal migration path. Migration `0007_micro_lesson_reward_events.sql` is additive and idempotent: it creates the reward-event tracking table and unique index only when they are missing.

Legacy completed micro lessons that predate reward events remain compatible. Missing reward-event rows for already completed lessons do not grant duplicate XP during upgrade or retry paths.

## Validation Summary

The final release gate covers:

- Python compileall, Ruff, Mypy, backend pytest lanes, startup isolation, optional RAG tests, migration smoke tests, micro-lesson concurrency tests, and micro-lesson transaction rollback tests.
- pip dependency consistency and pip-audit.
- npm ci, production npm audit, full npm audit, typecheck, ESLint, Prettier, unit tests, component tests, and production build.
- Mocked Playwright E2E and full-stack Playwright smoke.
- Docker Compose validation.
- Release ZIP creation, version consistency verification, forbidden-file verification, required-file verification, extraction/bootstrap smoke, shell syntax validation, and secret-pattern scanning.

## Final Release Archive

Final archive filename:

```text
english-japanese-learning-coach-v1.4.0.zip
```
