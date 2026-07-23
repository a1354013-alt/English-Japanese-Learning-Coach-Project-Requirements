# Test Plan

Use this plan when validating a clean checkout or release.

## Toolchain

```bash
python --version
nvm install
nvm use
node -v
```

Expected versions:

- Python `3.11.x`
- Node.js `22.18.0`
- npm `10.9.3`

## Backend

```bash
python scripts/python_dependency_locks.py check
python -m compileall backend scripts tests
python -m ruff check backend scripts tests
python -m mypy backend
python -m pytest -q -m "not rag and not startup_isolation"
python -m pytest backend/tests/test_rag_disabled_startup.py -q
```

Review contract coverage is included in backend pytest: the frontend must submit one answer for every grammar and reading question, and the API rejects incomplete, duplicate, out-of-range, or lesson-mismatched answers with `422`.

Learning Session hardening coverage is included in backend pytest and should explicitly verify:

- Migration `0012` applies cleanly.
- Migration `0013` adds persisted Review submission IDs and legacy SRS review operation IDs.
- Migration `0014` adds per-language Learning Goals.
- The shared event semantic table is enforced in both request validation and repository validation.
- Event idempotent retry ordering is canonical after completion or abandonment.
- Abandonment is state-idempotent without an idempotency key.
- Summary reads stay snapshot-consistent under concurrent append/complete pressure.
- Demo reset clears all Learning Session sessions and events for the local demo user without seeding fake Session history.
- The concurrent incompatible-idempotency race remains stable for at least 50 rounds without assuming Future ordering.
- Optional recorder telemetry failures are tolerant in production mode and strict in focused integration tests.
- Lesson generation does not record `lesson_started`; explicit lesson start records one idempotent event.
- Repeated Review attempts use distinct canonical submission IDs, while a network retry with the same client submission ID creates no duplicate events.
- Both `/api/srs/review` and `/api/srs/items/review` are visible to Learning Session statistics.
- Chat assistant completion, Chat provider failure, Feynman completion, Micro Lesson completion, no active Session, wrong-language active Session, and backend restart persistence stay covered by focused regressions.
- Weekly Insights use Monday 00:00 inclusive through next Monday 00:00 exclusive in the configured timezone.
- RAG-enabled smoke uses the local SQLite RAG store and must pass without Chroma.

Current `1.6.0-dev.1` blocker:

- RC validation requires Node.js `22.18.0` and npm `10.9.3`. This local environment currently exposes Node `24.11.1` and npm `11.6.2`, so full frontend reinstall, E2E, Docker, and delivery verification must be rerun on the mandated toolchain before RC promotion.

## Frontend

```bash
cd frontend
npm ci
npm --version
npm audit --omit=dev
npm audit
npm run typecheck
npm run lint
npm run format:check
npm run test:unit
npm run test:component
npm run build
```

## E2E

Install Playwright Chromium before the first local browser run:

```bash
cd frontend
npm run e2e:install
RUN_E2E=1 npm run test:e2e -- --project=chromium
npm run test:e2e:fullstack:smoke -- --project=chromium
npm run test:e2e:fullstack -- --project=chromium
```

The `v1.5.0` persisted-chat release gate should explicitly verify:

- Conversation list loading and empty state
- Create, select, rename, and delete conversation flows
- Reload restoring the selected conversation plus canonical message history
- Older-history pagination
- EN/JP conversation-state isolation
- Retry-safe optimistic user message reconciliation
- Deterministic mocked browser coverage without live Ollama
- Full-stack persisted-chat coverage with `CHAT_PROVIDER_MODE=mock`

`npm run e2e:install` runs `playwright install chromium`. On local Windows checkouts, `cd frontend && npx playwright install chromium` is the direct fallback command after `npm ci`.

## Release Verification

```bash
python scripts/verify_delivery.py
python scripts/make_release_zip.py
```

For development versions such as `1.6.0-dev.1`, release verification should pass using README development markers while `RELEASE_CHECKLIST.md` and `docs/DEMO_GUIDE.md` remain pinned to the latest stable release documentation (`v1.5.0` as of July 22, 2026).

Optional RAG verification is a separate lane and requires:

```bash
python -m pip install -r backend/requirements-rag.txt
python scripts/verify_delivery.py --include-rag
```
