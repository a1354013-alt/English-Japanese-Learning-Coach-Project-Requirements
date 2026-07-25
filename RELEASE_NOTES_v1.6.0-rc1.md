# Release Notes: v1.6.0-rc1 Candidate

This document describes the intended `1.6.0-rc1` release scope for the current `1.6.0-dev.1` branch state. It does not promote the repository version on its own.

## 1. Release summary

`v1.6.0-rc1` packages the Learning Session feature set on top of the verified `v1.5.0` persisted-chat baseline. The scope includes typed Session lifecycle APIs, Session/Event persistence, Learning Goals, Weekly Insights, cursor pagination, frontend Progress-page workflow integration, and tolerant recorder observability.

## 2. Learning Session lifecycle

- Session states are `active`, `completed`, and `abandoned`.
- Only one active Session is allowed per user/language pair.
- Summaries are deterministic and derived from stored Session/Event rows only.
- Finalized Sessions remain readable through history, summary, and event timeline APIs.

## 3. Start / resume / complete / abandon behavior

- `POST /api/learning-sessions` starts a Session with optional `planned_minutes`.
- `GET /api/learning-sessions/active?language=EN|JP` restores the active Session after reload.
- `POST /api/learning-sessions/{session_id}/complete` requires an idempotency key and finalizes the Session.
- `POST /api/learning-sessions/{session_id}/abandon` finalizes without a request idempotency key and is state-idempotent.
- The frontend clears active reactive Session state after either completion or abandonment while preserving summary/timeline/history access.

## 4. Event taxonomy

Supported event types:

- `lesson_started`
- `lesson_completed`
- `review_answered`
- `srs_reviewed`
- `chat_turn_completed`
- `feynman_completed`
- `micro_lesson_completed`
- `session_note`

Semantic validation is enforced in both request validation and repository validation.

## 5. Idempotency contract

- Session notes use bounded `session-note:<operation-id>` keys.
- Review retries reuse `client_submission_id`.
- Legacy `/api/srs/review` retries reuse `client_operation_id`.
- Event append checks canonical `(session_id, idempotency_key)` matches before active-state enforcement, so canonical retries still resolve after finalization.
- Completing the same Session twice with the same completion key returns the stored completed row; a different key conflicts.

## 6. Learning Goals

- `GET /api/learning-goals?language=EN|JP` returns typed goal state.
- `PUT /api/learning-goals?language=EN|JP` accepts `daily_minutes`, `weekly_sessions`, and optional `weekly_minutes`.
- Optional `weekly_minutes` must be a positive integer or `null`; empty-string coercion is handled in the frontend before API submission.

## 7. Weekly Insights and attribution rule

- `GET /api/learning-insights/weekly?language=EN|JP` returns Monday-based weekly metrics.
- Optional `week_start` dates normalize to that week’s Monday.
- Session lifecycle metrics are attributed by finalized `ended_at`.
- Event activity metrics are attributed by event `occurred_at`.

## 8. Session and event pagination

- Session history uses cursor pagination with `has_more` and `next_cursor`.
- Event timelines use cursor pagination with `has_more` and `next_cursor`.
- The frontend appends additional pages without duplicating Sessions or Events and resets cursors on language or Session changes.

## 9. Database migrations `0012` through `0014`

- `0012_learning_sessions_and_events.sql`: Session rows, append-only event log, lifecycle constraints.
- `0013_review_and_srs_operation_ids.sql`: persisted Review submission IDs and legacy SRS operation IDs for retry-safe telemetry.
- `0014_learning_goals.sql`: per-language Learning Goals with optional weekly minutes.

## 10. Upgrade procedure

1. Back up the SQLite database before startup.
2. Install backend dependencies from the pinned Python 3.11 lock file.
3. Start the backend and allow additive migrations to run.
4. Verify `schema_migrations` includes `0012`, `0013`, and `0014`.
5. Run frontend installs/checks on Node `22.18.0` and npm `10.9.3`.

## 11. Backup guidance

- Use `python scripts/sqlite_backup_restore.py backup --target <path>` before migration or release verification.
- Validate backup files before relying on them for rollback planning.
- Stop the app before replacing an active SQLite file.

## 12. Rollback limitations

- Schema migrations are additive, but application rollback still assumes compatible pre-release data handling.
- Learning Session rows, Event rows, Review submission IDs, legacy SRS operation IDs, and Learning Goal rows created after upgrade are not automatically translated back for older application binaries.

## 13. Telemetry tolerant / strict mode

- Tolerant mode logs recorder failures and returns control to the primary learner workflow.
- Strict mode raises and is intended for focused integration tests.
- `GET /api/ready` exposes recorder mode, degraded state, and structured counters.

## 14. Single-user demo boundary

The project remains a local single-user demo. Authentication, authorization, multi-user isolation, rate limiting, and audit logging are still out of scope for this release line.

## 15. Known limitations

- TTS is integration-ready but disabled by default.
- Immersion remains text shadowing rather than real voice coaching.
- Real recording and speech comparison are not part of this release.
- Learning Session runtime data is not pre-seeded by demo reset.
- RC promotion remains blocked until the mandated frontend toolchain and full verification lanes pass.

## 16. Verification commands

Backend:

```bash
python scripts/python_dependency_locks.py check
python -m compileall backend scripts tests
python -m ruff check backend scripts tests
python -m mypy backend
python -m pytest -q -m "not rag and not startup_isolation"
python -m pytest backend/tests/test_rag_disabled_startup.py -q
```

Frontend:

```bash
cd frontend
npm ci
npm audit --omit=dev
npm audit
npm run typecheck
npm run lint
npm run format:check
npm run test:unit
npm run test:component
npm run build
```

Release:

```bash
python scripts/verify_delivery.py
python scripts/make_release_zip.py
```

## 17. RC promotion criteria

Promotion to `v1.6.0-rc1` requires:

- all Learning Session RC blockers fixed
- no known P0/P1 regressions
- contract alignment across frontend, backend, migrations, and docs
- full validation on Python `3.11.x`, Node `22.18.0`, npm `10.9.3`
- verifier, Docker, frontend audits, and E2E lanes all green

Until those gates pass, keep the branch at `1.6.0-dev.1`.
