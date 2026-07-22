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

## Learning-Session Phase 1 Boundary

Phase 1 adds a dedicated learning-session router plus a feature-focused repository behind the `Database` compatibility facade. It introduces additive schema `0012`, strict `active -> completed|abandoned` transitions, append-only event sequencing, canonical retry-safe idempotency, and deterministic summaries derived only from stored session/event data.

Phase 1 does not automatically wire lesson completion, review submission, SRS scheduling, chat tutor turns, Feynman submissions, or micro-lesson completion into the new event log yet. That integration belongs to the planned Phase 2 service layer.

Current backend boundary:

- `backend/routers/learning_sessions.py` owns the typed REST contract and error mapping.
- `backend/repositories/learning_session_repository.py` owns SQL, lifecycle rules, pagination, idempotency, event semantics, and deterministic summary generation.
- `backend/learning_session_contract.py` is the single semantic contract table shared by request validation and repository validation.
- `backend/database.py` remains the compatibility facade and exposes one learning-session repository instance per `Database`.
- `backend/repositories/protocols.py` and `backend/repositories/protocol_assertions.py` define and statically verify the real Phase 1 repository protocol.
- A future Phase 2 integration service will be responsible for recording events from lesson, review, SRS, chat tutor, Feynman, and micro-lesson flows without changing the Phase 1 storage contract.

Learning Session event rules in Phase 1:

- `lesson_started` and `lesson_completed` require `entity_type=lesson` and an `entity_id`.
- `review_answered` requires `entity_type=review`, an `entity_id`, and `metadata.correct`; `metadata.note` is optional.
- `srs_reviewed`, `chat_turn_completed`, `feynman_completed`, and `micro_lesson_completed` each require their canonical entity type plus `entity_id` and reject metadata.
- `session_note` requires `metadata.note`, rejects blank notes, and does not allow entity fields or `metadata.correct`.

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
