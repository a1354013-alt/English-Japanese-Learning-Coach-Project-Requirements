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
- If the backend does not start, run `cd backend && python -m pip install -r requirements.txt -r requirements-dev.txt` manually.
- Ensure ports `8000` and `5173` are not already in use.


Production dependencies are a hard release gate. Full `npm audit` must also stay clean right now because the locked dependency tree has no remaining advisories after the current security updates.
