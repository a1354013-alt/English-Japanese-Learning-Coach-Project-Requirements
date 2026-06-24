# Test Plan

Use this plan when validating a clean checkout or release candidate.

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
