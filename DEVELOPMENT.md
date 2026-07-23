# Development Guide

This project pins the supported release-verification toolchain to Python `3.11.x`, Node.js `22.18.0`, and npm `10.9.3` for `1.6.0-dev.1`.

## Backend Setup

```bash
cd backend
python3.11 -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-dev.lock.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Refresh the Python 3.11 lock files only when you intentionally want to update the locked transitive dependency set:

```bash
python scripts/python_dependency_locks.py refresh
```

Ordinary CI and release verification should use `python scripts/python_dependency_locks.py check`, which validates lock metadata fingerprints plus portability/secret-redaction rules without re-resolving the package index.

Chat runtime limits are validated at backend startup. Keep `CHAT_CLIENT_MESSAGE_ID_MAX_CHARS` at or below 250 so the stored `user:` idempotency-key prefix still fits the repository's 255-character limit.

## Learning-Session Phase 2.1 Boundary

Phase 1 adds a dedicated learning-session router plus a feature-focused repository behind the `Database` compatibility facade. It introduces additive schema `0012`, strict `active -> completed|abandoned` transitions, append-only event sequencing, canonical retry-safe idempotency, and deterministic summaries derived only from stored session/event data.

Phase 2.1 wires existing learning workflows into the event log as optional telemetry only. Lesson, Review, SRS, Chat Tutor, Feynman, and Micro Lesson must still succeed when no same-language active Session exists or when tolerant recorder lookup/append fails after the primary workflow has committed.

Migration `0013_review_and_srs_operation_ids.sql` adds:

- `review_submissions`: canonical persisted Review submission IDs, optional client retry IDs, request hashes, and submitted score snapshots.
- `legacy_srs_review_operations`: canonical persisted operation IDs for `/api/srs/review`, optional client retry IDs, request hashes, quality, and created time.

Migration `0014_learning_goals.sql` adds per-user/per-language Learning Goals with bounded daily minutes, weekly Sessions, and optional weekly minutes. Demo defaults are EN 20 daily minutes / 4 weekly Sessions / 120 weekly minutes and JP 15 / 3 / 90.

Current backend boundary:

- `backend/routers/learning_sessions.py` owns the typed REST contract and error mapping.
- `backend/repositories/learning_session_repository.py` owns SQL, lifecycle rules, pagination, idempotency, event semantics, and deterministic summary generation.
- `backend/learning_session_contract.py` is the single semantic contract table shared by request validation and repository validation.
- `backend/database.py` remains the compatibility facade and exposes one learning-session repository instance per `Database`.
- `backend/repositories/protocols.py` and `backend/repositories/protocol_assertions.py` define and statically verify the real Phase 1 repository protocol.
- `backend/services/learning_session_recorder.py` owns the strict/tolerant optional telemetry failure boundary.
- Integrated primary flows call the recorder only after their primary persistence succeeds.

Integration contracts:

- Generating, scheduling, opening, or reloading a Lesson does not record `lesson_started`.
- `POST /api/lessons/{lesson_id}/start` is the explicit learner-start operation and records one idempotent `lesson_started` event per default lesson start key.
- Review answer events use `review_submissions.submission_id` plus answer coordinates as their source operation identity. Existing Review payloads remain valid; clients can send `client_submission_id` on each answer to dedupe a network retry.
- A frontend Review action creates one stable `client_submission_id`, reuses it on retry after failure/timeout, and clears it after canonical success.
- `/api/srs/items/review` records `srs_reviewed` using the persisted learning item review event ID.
- `/api/srs/review` records `srs_reviewed` using `legacy_srs_review_operations.operation_id`; clients can send `client_operation_id` to dedupe a retry.
- Chat assistant completion, Feynman completion, and Micro Lesson completion record their existing persisted source IDs.
- `GET/PUT /api/learning-goals?language=EN|JP` owns typed Learning Goal state.
- `GET /api/learning-insights/weekly?language=EN|JP` returns deterministic Monday-based weekly metrics from stored Sessions and Events only.
- RAG-enabled local development uses the SQLite RAG store under `CHROMA_DB_PATH`; Chroma is no longer a runtime dependency.

Learning Session event rules:

- `lesson_started` and `lesson_completed` require `entity_type=lesson` and an `entity_id`.
- `review_answered` requires `entity_type=review`, an `entity_id`, and `metadata.correct`; `metadata.note` is optional.
- `srs_reviewed` requires `entity_type=srs_item` and may include correctness, rating, interval, and result-category metadata.
- `chat_turn_completed` requires `entity_type=conversation` and rejects metadata.
- `feynman_completed` requires `entity_type=feynman_response` and may include result-category metadata.
- `micro_lesson_completed` requires `entity_type=micro_lesson` and may include completion-outcome metadata.
- `session_note` requires `metadata.note`, rejects blank notes, and does not allow entity fields or `metadata.correct`.

Recorder failure policy:

- Set `LEARNING_SESSION_RECORDER_MODE=tolerant` for production-style optional telemetry. Lookup, append, idempotency, semantic, and SQLite failures are logged with structured context and return `None`.
- Set `LEARNING_SESSION_RECORDER_MODE=strict`, or call `build_learning_session_recorder(..., mode="strict")`, for focused integration tests that must fail on malformed mappings, ownership bugs, source-ID mistakes, and programmer errors.
- If the environment variable is unset, pytest defaults to strict mode and normal runtime defaults to tolerant mode.

Lifecycle and idempotency rules:

- Event append looks up an existing event by `(session_id, idempotency_key)` before enforcing the active-session requirement.
- Canonical retries after completion or abandonment return the stored event instead of creating a duplicate.
- New events after finalization are still rejected.
- Abandonment is state-idempotent and no longer accepts an idempotency key in the request contract.
- Demo reset now clears all Learning Session rows for the local demo user through the repository clear operation before rebuilding the seeded `v1.5.0` demo dataset.

Version verification note:

- `scripts/verify_delivery.py` now has an explicit development-version mode for versions like `1.6.0-dev.1`.
- Development mode requires root/frontend/package-lock version parity plus the canonical README development marker and line.
- Development mode intentionally keeps `RELEASE_CHECKLIST.md` and `docs/DEMO_GUIDE.md` pinned to the latest stable release, currently `v1.5.0`.
- RC and final versions still use the strict release-facing wording checks.

Phase 2.1 gate status:

- Backend pytest, RAG-enabled tests, RAG-disabled startup tests, Python lock checks, and Python lock audit are green locally.
- A compact frontend Session/Weekly Review workflow is present on the Progress overview tab.
- `1.6.0-rc1` promotion remains blocked until validation runs with Node.js `22.18.0` and npm `10.9.3`, plus full frontend reinstall, E2E, Docker, and delivery verification.

## Frontend Setup

Run these commands from the repository root so `nvm` picks up the pinned version from `.nvmrc`:

```bash
nvm install
nvm use
node -v
cd frontend
npm ci
npm run dev
```

## First-Time E2E Setup

Install the Playwright Chromium browser once before the first local E2E run:

```bash
cd frontend
npm run e2e:install
npm run test:e2e -- --project=chromium
```

`npm run e2e:install` maps to `playwright install chromium`. On Windows, if script resolution is noisy, run `cd frontend && npx playwright install chromium` after `npm ci`, then rerun the E2E command.

For real backend/frontend coverage, use:

```bash
cd frontend
npm run e2e:install
npm run test:e2e:fullstack:smoke -- --project=chromium
npm run test:e2e:fullstack -- --project=chromium
```

The full-stack persisted-chat browser lane now uses `CHAT_PROVIDER_MODE=mock` in Playwright so ordinary frontend release validation does not require a live Ollama process.

## Frontend Verification

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

## VS Code F5 One-Click Development

This repository includes VS Code launch and task configuration for starting the frontend Vite dev server and backend FastAPI debug session together.

1. Open the project root in VS Code.
2. Set the Python interpreter to the correct environment for this project.
3. Copy `backend/.env.example` to `backend/.env` if `backend/.env` does not exist.
4. Select `F5: Backend + Frontend` from the Run and Debug dropdown.
5. Press F5.

The `F5: Backend + Frontend` configuration starts `Frontend Dev Server` in the background and then launches the backend debug server.

### Notes

- Backend URL: `http://localhost:8000`
- Frontend URL: `http://localhost:5173` (or the host/port displayed by Vite)
- If the frontend task does not start, run `cd frontend && npm ci` manually.
- If the backend does not start, run `cd backend && python -m pip install -r requirements-dev.lock.txt` manually.
- Ensure ports `8000` and `5173` are not already in use.


Production dependencies are a hard release gate. Full `npm audit` must also stay clean right now because the locked dependency tree has no remaining advisories after the current security updates.
