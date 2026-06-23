# Development Guide

This project pins the local release-verification toolchain to Python 3.11 and Node.js 22.18.0.

## Backend Setup

```bash
cd backend
python3.11 -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

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

For real backend/frontend coverage, use:

```bash
cd frontend
npm run e2e:install
npm run test:e2e:fullstack:smoke -- --project=chromium
npm run test:e2e:fullstack -- --project=chromium
```

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

Production dependencies are a hard release gate. Full `npm audit` must also stay clean right now because the locked dependency tree has no remaining advisories after the current security updates.
