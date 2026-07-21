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

## Backend

```bash
python -m compileall backend scripts tests
python -m ruff check backend scripts tests
python -m mypy backend
python -m pytest -q -m "not rag and not startup_isolation"
python -m pytest backend/tests/test_rag_disabled_startup.py -q
```

Review contract coverage is included in backend pytest: the frontend must submit one answer for every grammar and reading question, and the API rejects incomplete, duplicate, out-of-range, or lesson-mismatched answers with `422`.

## Frontend

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

Optional RAG verification is a separate lane and requires:

```bash
python -m pip install -r backend/requirements-rag.txt
python scripts/verify_delivery.py --include-rag
```
