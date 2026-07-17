# Architecture Boundaries for v1.5

This maintenance release keeps `backend/database.py` as the runtime facade while preparing a safer extraction path for `v1.5`.

## Current runtime rule

- `Database` remains the single runtime entry point for SQLite-backed persistence.
- No learner-facing behavior changes are introduced by the boundary work in this document.
- Future repositories must preserve existing migration semantics and local-first SQLite behavior.

## New protocol boundaries

The codebase now defines protocol placeholders for two future areas:

- `PersistedChatRepositoryProtocol`
- `LearningSessionRepositoryProtocol`

These protocols are intentionally additive. They let new feature work target a narrow interface before any data-access code is moved out of `Database`.

## Intended feature-based layout

The target repository layout for `v1.5` is:

```text
backend/
  repositories/
    protocols.py
    chat_repository.py
    learning_session_repository.py
    lesson_repository.py
    progress_repository.py
  services/
    chat/
    learning_sessions/
    lessons/
    review/
```

## Extraction order

1. Introduce repository-specific tests around the current `Database` behavior.
2. Add adapter classes that satisfy the new protocols while still delegating to `Database`.
3. Extract the new persisted-chat feature first because it is mostly additive.
4. Extract learning-session persistence second once the feature contract is stable.
5. Leave lesson, review, and analytics extraction for later releases unless a concrete change requires it.

## Non-goals for v1.4.1

- No multi-user redesign
- No database engine change
- No schema rewrite for existing study, review, or analytics data
- No learner-facing feature work hidden inside the extraction prep
