# Architecture Boundaries for v1.6 Phase 2.1

This document describes the current storage, API, and integration boundaries for the additive Learning Session foundation that ships on the `1.6.0-dev.1` branch.

## Runtime Boundary

- `backend/database.py` remains the SQLite runtime facade.
- `backend/repositories/learning_session_repository.py` is now the real Phase 1 repository, not a placeholder.
- `backend/routers/learning_sessions.py` exposes the typed REST contract and maps repository errors to structured API codes.
- `backend/services/learning_session_recorder.py` is the optional telemetry boundary used by existing Lesson, Review, SRS, Chat Tutor, Feynman, and Micro Lesson workflows.
- Integrated learning workflows must remain usable with no active Session, the wrong-language active Session, or tolerant telemetry failure.

## Migrations

- Migration `0012_learning_sessions.sql` adds the `learning_sessions` and `learning_session_events` tables.
- Session lifecycle is additive and local-first: `active -> completed` or `active -> abandoned`.
- Event history is append-only and ordered by per-session `sequence_number`.
- Idempotency remains local SQLite behavior; no distributed coordinator is introduced in Phase 1.
- Migration `0013_review_and_srs_operation_ids.sql` adds `review_submissions` and `legacy_srs_review_operations`.
- `review_submissions.submission_id` is the canonical Review attempt operation ID; optional `client_submission_id` dedupes client retries.
- `legacy_srs_review_operations.operation_id` is the canonical operation ID for `/api/srs/review`; optional `client_operation_id` dedupes client retries.

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
- SRS item path: `/api/srs/items/review` records from the persisted learning item review event ID.
- Legacy SRS path: `/api/srs/review` records from `legacy_srs_review_operations.operation_id`.
- Chat, Feynman, and Micro Lesson use their existing persisted conversation, feedback, and micro-lesson IDs.

## Summary Boundary

- `produce_summary` reads session state and event aggregates inside one SQLite read transaction.
- The returned lifecycle fields and aggregate counts come from one consistent snapshot.
- Phase 1 summaries are deterministic and local; they do not call any external provider while the transaction is open.

## Demo Reset Boundary

- Demo reset now clears Learning Sessions through `clear_local_demo_user_session_data`.
- Learning Session history is not seeded after reset in Phase 1.
- Existing seeded `v1.5.0` demo lessons, review state, SRS state, and analytics-supporting data are rebuilt as before.

## Non-goals

- No Phase 3 frontend Session dashboard until Phase 2.1 gates are green
- No Phase 4 Learning Goals or Weekly Insights until Phase 2.1 gates are green
- No weekly reports or adaptive recommendations
- No authentication, PostgreSQL migration, or distributed idempotency layer

## Current Gate Status

Phase 2.1 is not complete in this local checkout because the full backend suite currently fails at `backend/tests/test_rag_enabled_smoke.py::test_rag_enabled_smoke`: installed `chromadb` imports `np.float_`, which NumPy 2.0 removed. Keep `1.6.0-dev.1`; do not promote to `1.6.0-rc1` until that gate is green.
