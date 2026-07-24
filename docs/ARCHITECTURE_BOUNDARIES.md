# Architecture Boundaries for v1.6 Phase 2.1

This document describes the current storage, API, and integration boundaries for the additive Learning Session foundation that ships on the `1.6.0-dev.1` branch.

## Runtime Boundary

- `backend/database.py` remains the SQLite runtime facade.
- `backend/repositories/learning_session_repository.py` is now the real Phase 1 repository, not a placeholder.
- `backend/routers/learning_sessions.py` exposes the typed REST contract and maps repository errors to structured API codes.
- `backend/services/learning_session_recorder.py` is the optional telemetry boundary used by existing Lesson, Review, SRS, Chat Tutor, Feynman, and Micro Lesson workflows.
- Integrated learning workflows must remain usable with no active Session, the wrong-language active Session, or tolerant telemetry failure.

## Migrations

- Migration `0012_learning_sessions_and_events.sql` adds the `learning_sessions` and `learning_session_events` tables.
- Session lifecycle is additive and local-first: `active -> completed` or `active -> abandoned`.
- Event history is append-only and ordered by per-session `sequence_number`.
- Idempotency remains local SQLite behavior; no distributed coordinator is introduced in Phase 1.
- Migration `0013_review_and_srs_operation_ids.sql` adds `review_submissions` and `legacy_srs_review_operations`.
- `review_submissions.submission_id` is the canonical Review attempt operation ID; optional `client_submission_id` dedupes client retries.
- `legacy_srs_review_operations.operation_id` is the canonical operation ID for `/api/srs/review`; optional `client_operation_id` dedupes client retries.
- Migration `0014_learning_goals.sql` adds `learning_goals` with `(user_id, language)` uniqueness, bounded daily minutes, weekly Sessions, optional weekly minutes, and timestamps.

## Repository Protocol

`LearningSessionRepositoryProtocol` now matches the implemented Phase 1 contract:

- `start_session`
- `get_session`
- `find_active_session`
- `list_session_history`
- `append_event`
- `list_events`
- `complete_session`
- `abandon_session`
- `produce_summary`
- `delete_session`
- `clear_local_demo_user_session_data`

`backend/repositories/protocol_assertions.py` provides the static typing assertion that `LearningSessionRepository` satisfies this protocol.

## Event Boundary

One shared semantic table is used by both request validation and repository validation. Internal callers cannot bypass the Phase 1 event contract.

| Event type | Required entity | Required metadata | Forbidden extras |
| --- | --- | --- | --- |
| `lesson_started` | `lesson` + `entity_id` | none | all metadata |
| `lesson_completed` | `lesson` + `entity_id` | optional completion metadata | unsupported metadata |
| `review_answered` | `review` + `entity_id` | `metadata.correct` | unsupported entity types |
| `srs_reviewed` | `srs_item` + `entity_id` | optional correctness/rating/schedule metadata | unsupported metadata |
| `chat_turn_completed` | `conversation` + `entity_id` | none | all metadata |
| `feynman_completed` | `feynman_response` + `entity_id` | optional result category | unsupported metadata |
| `micro_lesson_completed` | `micro_lesson` + `entity_id` | optional completion outcome | unsupported metadata |
| `session_note` | no entity | `metadata.note` | `metadata.correct`, entity fields |

Blank `entity_id` values, blank notes, mismatched entity types, and unsupported metadata combinations are rejected.

## Idempotency Rules

- Event append checks for an existing `(session_id, idempotency_key)` record before it checks whether the session is still active.
- A canonical retry with the same payload returns the original event, even after the session has already been completed or abandoned.
- A conflicting retry raises `LearningSessionIdempotencyConflictError`.
- A brand-new event after finalization still raises `LearningSessionNotActiveError`.
- Session completion remains idempotent by `completion_idempotency_key`.
- Session abandonment is state-idempotent and does not accept an idempotency key in Phase 1.
- Manual Session notes use a bounded operation identity. The frontend creates one random operation ID per intentional Add Note action and sends `session-note:<operation-id>` as the idempotency key; note text is never part of that key. A pending timeout retry reuses the same operation ID until the canonical event is accepted, and canonical event IDs are de-duplicated in the timeline.

## Primary Workflow Isolation

- Recorder mode is explicit: `LEARNING_SESSION_RECORDER_MODE=tolerant` for optional telemetry and `strict` for focused integration tests.
- Tolerant mode catches and logs active-session lookup, append, idempotency, semantic, and SQLite failures without changing an already committed primary workflow response.
- Strict mode raises a `RuntimeError` wrapping the recorder failure so invalid mappings, ownership bugs, malformed source IDs, and programmer errors fail tests.
- Pytest defaults to strict mode when the environment variable is absent; normal runtime defaults to tolerant mode.

## Integrated Source Operations

- Lesson start: `POST /api/lessons/{lesson_id}/start` records one `lesson_started` event. Lesson generation and Lesson GET do not record starts.
- Lesson completion: the first successful Review completion for a Lesson records `lesson_completed` and preserves the existing one-time XP/completed-lesson reward rule.
- Review: each persisted `review_submissions.submission_id` scopes answer events as `{submission_id}:{exercise_type}:{question_index}`.
- Review retry: a repeated `client_submission_id` with the same request hash reuses the canonical submission and event keys.
- Review retry side effects are isolated: canonical retries do not reapply XP, completion rewards, wrong-answer tracking, SRS updates, or Session Events.
- SRS item path: `/api/srs/items/review` records from the persisted learning item review event ID.
- Legacy SRS path: `/api/srs/review` records from `legacy_srs_review_operations.operation_id`.
- Chat, Feynman, and Micro Lesson use their existing persisted conversation, feedback, and micro-lesson IDs.

## Goals and Weekly Insights

- `GET/PUT /api/learning-goals?language=EN|JP` returns and updates the demo user's per-language goals.
- `GET /api/learning-insights/weekly?language=EN|JP` computes deterministic weekly metrics from stored Sessions and Events.
- `week_start` is typed as a date query parameter. Invalid text or invalid calendar dates return FastAPI's structured `422` validation response. Any valid supplied date is normalized to the Monday of that week.
- Weeks start Monday 00:00 in `settings.timezone` and end at the next Monday 00:00.
- Completed and abandoned Session lifecycle metrics are attributed to the week containing the Session's canonical `ended_at`. Active unfinished Sessions are not counted as completed or abandoned.
- Event activity metrics are attributed to the week containing each Event's `occurred_at`. A Session may start in one week and finish in the next while its Events remain attributed to their actual occurrence dates.
- Insights include completed/abandoned Sessions, duration, active days, goal progress, event counts, review correctness only when review-answer metadata exists, most-active-day tie-breaking by earliest date, and recent completed Sessions.
- Insights do not call AI and do not infer CEFR movement, weakness analysis, mastery, recommendations, or curriculum changes.

## RAG Boundary

- RAG-enabled local storage is backed by SQLite under `CHROMA_DB_PATH`.
- Chroma, Transformers, and sentence-transformers are no longer runtime dependencies for the local RAG lane.
- RAG-disabled startup remains deterministic and does not import optional vector-store packages.
- Production RAG operations use a managed SQLite connection boundary that commits on success, rolls back on failure, closes every connection in `finally`, and allows exceptions to propagate.

## Summary Boundary

- `produce_summary` reads session state and event aggregates inside one SQLite read transaction.
- The returned lifecycle fields and aggregate counts come from one consistent snapshot.
- Phase 1 summaries are deterministic and local; they do not call any external provider while the transaction is open.

## Demo Reset Boundary

- Demo reset now clears Learning Sessions through `clear_local_demo_user_session_data`.
- Learning Session history is not seeded after reset in Phase 1.
- Existing seeded `v1.5.0` demo lessons, review state, SRS state, and analytics-supporting data are rebuilt as before.

## Non-goals

- No weekly reports, adaptive recommendations, or AI-generated recommendations
- No authentication, PostgreSQL migration, or distributed idempotency layer

## Current Gate Status

Focused backend/RAG and frontend component checks are green locally for this hardening pass. Keep `1.6.0-dev.1`; do not promote to `1.6.0-rc1` until the mandatory Python `3.11.x`, Node.js `22.18.0` / npm `10.9.3`, full frontend, E2E, Docker, and delivery gates are run and green.
