# Architecture Boundaries for v1.6 Phase 1.1

This document describes the current storage and API boundaries for the additive Learning Session foundation that ships on the `1.6.0-dev.1` branch.

## Runtime Boundary

- `backend/database.py` remains the SQLite runtime facade.
- `backend/repositories/learning_session_repository.py` is now the real Phase 1 repository, not a placeholder.
- `backend/routers/learning_sessions.py` exposes the typed REST contract and maps repository errors to structured API codes.
- Existing lesson, review, SRS, Chat Tutor, Feynman, and Micro Lesson flows are not automatically wired to Learning Sessions yet.

## Migration 0012

- Migration `0012_learning_sessions.sql` adds the `learning_sessions` and `learning_session_events` tables.
- Session lifecycle is additive and local-first: `active -> completed` or `active -> abandoned`.
- Event history is append-only and ordered by per-session `sequence_number`.
- Idempotency remains local SQLite behavior; no distributed coordinator is introduced in Phase 1.

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
| `lesson_completed` | `lesson` + `entity_id` | none | all metadata |
| `review_answered` | `review` + `entity_id` | `metadata.correct` | unsupported entity types |
| `srs_reviewed` | `srs_item` + `entity_id` | none | all metadata |
| `chat_turn_completed` | `conversation` + `entity_id` | none | all metadata |
| `feynman_completed` | `feynman_response` + `entity_id` | none | all metadata |
| `micro_lesson_completed` | `micro_lesson` + `entity_id` | none | all metadata |
| `session_note` | no entity | `metadata.note` | `metadata.correct`, entity fields |

Blank `entity_id` values, blank notes, mismatched entity types, and unsupported metadata combinations are rejected.

## Idempotency Rules

- Event append checks for an existing `(session_id, idempotency_key)` record before it checks whether the session is still active.
- A canonical retry with the same payload returns the original event, even after the session has already been completed or abandoned.
- A conflicting retry raises `LearningSessionIdempotencyConflictError`.
- A brand-new event after finalization still raises `LearningSessionNotActiveError`.
- Session completion remains idempotent by `completion_idempotency_key`.
- Session abandonment is state-idempotent and does not accept an idempotency key in Phase 1.

## Summary Boundary

- `produce_summary` reads session state and event aggregates inside one SQLite read transaction.
- The returned lifecycle fields and aggregate counts come from one consistent snapshot.
- Phase 1 summaries are deterministic and local; they do not call any external provider while the transaction is open.

## Demo Reset Boundary

- Demo reset now clears Learning Sessions through `clear_local_demo_user_session_data`.
- Learning Session history is not seeded after reset in Phase 1.
- Existing seeded `v1.5.0` demo lessons, review state, SRS state, and analytics-supporting data are rebuilt as before.

## Non-goals

- No automatic Phase 2 integration with lesson, review, SRS, Chat Tutor, Feynman, or Micro Lesson flows
- No weekly reports or adaptive recommendations
- No learner-facing Session dashboard
- No authentication, PostgreSQL migration, or distributed idempotency layer
