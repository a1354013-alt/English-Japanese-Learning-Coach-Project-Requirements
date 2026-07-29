# Release Notes: v1.6.0

English-Japanese Learning Coach `v1.6.0` finalizes the Learning Sessions release on top of the verified `v1.5.0` persisted-chat baseline.

## Highlights

- Structured Learning Sessions with active, completed, and abandoned lifecycle states.
- Automatic learning-activity Events for Lesson, Review, SRS, Chat, Feynman, and Micro Lesson workflows when a same-language active Session exists.
- Explicit Lesson start via `POST /api/lessons/{lesson_id}/start` so generated or opened Lessons are not counted as started until the learner begins them.
- Session restoration after browser reload with server-derived elapsed time and canonical finalized duration.
- Manual Session Notes with retry-safe operation IDs that do not include note text.
- Canonical completion and abandonment behavior with deterministic summaries, history, and event timelines remaining readable after finalization.
- Learning Goals for English and Japanese.
- Deterministic Weekly Insights using application-timezone week attribution and correctness denominators based only on Review Events with correctness metadata.
- SQLite-backed RAG storage and verification without ChromaDB.

## Database Migrations

- `0012_learning_sessions_and_events.sql` adds Learning Sessions and append-only Learning Session Events.
- `0013_review_and_srs_operation_ids.sql` adds Review submission identities and legacy SRS operation identities for retry-safe Event recording.
- `0014_learning_goals.sql` adds per-language Learning Goals.

Migrations remain additive and run through the existing migration runner.

## Upgrade Notes

- Upgrade path is from `v1.5.0` to `v1.6.0`.
- Existing Lessons, Reviews, SRS data, wrong answers, progress, persisted Chat conversations, and learning activities remain preserved.
- Existing learning activities remain usable without an active Learning Session.
- Back up the SQLite data directory before upgrading, especially before replacing an active local demo database.
- Run the existing migration runner as part of backend startup or the standard release verification flow.

## Supported Toolchain

- Python `3.11.x` for release verification.
- Python `3.13.x` lifecycle compatibility for warning and shutdown checks.
- Node.js `22.18.0`.
- npm `10.9.3`.

## Verification Scope

The final release gate covers component tests, mocked E2E, full-stack E2E, Docker validation, security checks, SQLite-backed RAG delivery verification, and packaging hardening.

## Known Limitations

- Local single-user demonstration scope.
- No authentication, authorization, multi-user SaaS infrastructure, rate limiting, or audit logging.
- No adaptive recommendation engine or automatic curriculum adjustment.
- No AI-generated weekly report.
- No PostgreSQL deployment target.
- No voice recording or pronunciation scoring.
- TTS remains provider-ready but disabled unless a real provider is configured.
