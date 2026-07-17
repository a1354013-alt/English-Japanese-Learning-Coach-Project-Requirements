# Release Notes v1.4.2

Release date: 2026-07-17

`v1.4.2` is a maintenance-only hotfix for release reliability and local SQLite safety. It does not add learner-facing features, persisted chat, learning sessions, authentication, voice features, or broad database refactors.

Highlights:

- Release verification now uses stable current-release markers instead of coupling machine checks to a full README prose sentence.
- Python lock verification is now deterministic and portable, while still keeping readable source requirement files plus generated Python 3.11 lock files for core, development/test, and optional RAG installs.
- SQLite `validate` is now genuinely read-only, and backup/restore now validate temporary copies before atomically replacing the final file.
- Backend coverage now reports application code only by excluding `backend/tests/*`.
- Backend startup and pytest teardown now close SQLite connections more cleanly, and repeated unclosed-database warnings are treated as regressions.
