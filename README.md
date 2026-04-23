# English-Japanese Learning Coach

**Version:** 1.2.0  
Portfolio-grade demo of an AI-assisted language learning workflow (FastAPI + Vue 3).

## What's included

- AI lesson generation (EN/JP) with a strict JSON lesson schema persisted to SQLite
- Review flow: scoring + progress updates + SRS updates + wrong-answer notebook (idempotent per lesson)
- Daily streak derived from an activity log (single source of truth)
- RAG materials upload to ChromaDB with metadata isolation (`user_id` + `language`)
- PDF export of a lesson
- Chat Tutor (Preview UI): WebSocket chat demo (requires a configured AI provider; messages are not persisted)

## Scope / tenant model

This repository is a **single-tenant demo** (`default_user`). The backend enforces demo scoping and rejects arbitrary `user_id` values (no auth shipped in this build). The frontend does not send `user_id`; the API defaults to the demo user internally.

## Data & portability

- The backend stores lesson **file keys** in SQLite as relative paths under `DATA_DIR` (not absolute machine paths).
- Default `DATA_DIR` is `./data` at the repository root.
- Runtime data is excluded from git (SQLite DB, Chroma persistent store, generated lessons, exports, etc).

Backend environment variables (optional):

- `DATA_DIR` (default: `./data`)
- `DB_PATH` (default: `${DATA_DIR}/language_coach.db`)
- `CHROMA_DB_PATH` (default: `${DATA_DIR}/chroma_db`)

## Preview features (demo-only)

- TTS (API only): endpoint returns `available=false` unless a real provider is integrated (see `backend/tts_service.py`). No TTS UI in this build.
- Chat Tutor (Preview UI): requires a configured AI provider; messages are not persisted.

## Quick start (local)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker (API only)

```bash
docker compose up --build
```

Frontend is intended to run via `npm run dev` and will proxy `/api` and `/ws` to the backend.

## Tests

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

```bash
cd frontend
npm install
npm run test
npm run build
# With backend running on http://localhost:8000 and frontend dev server on http://127.0.0.1:5173
npm run e2e -- --project=chromium
```

### e2e with custom ports (optional)

If you need to run the backend on a different port, set Vite proxy targets:

```bash
# example: backend on 8001, frontend on 5181
cd frontend
VITE_API_TARGET=http://127.0.0.1:8001 VITE_WS_TARGET=ws://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5181 --strictPort
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5181 npm run e2e -- --project=chromium
```

## Repository hygiene

Runtime data is excluded from git:

- `data/*.db` (SQLite)
- `data/chroma_db/` (Chroma persistent store)
- `frontend/node_modules/`, `frontend/dist/`

## License

MIT (see `LICENSE`).

