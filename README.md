# English-Japanese Learning Coach

**Version:** 1.2.0  
Portfolio-grade demo of an AI-assisted language learning workflow (FastAPI + Vue 3).

## What’s included (current release)

- AI lesson generation (EN/JP) with a strict JSON lesson schema persisted to SQLite
- Review flow: scoring + progress updates + SRS updates + wrong-answer notebook
- Daily streak derived from an activity log (single source of truth)
- RAG materials upload to ChromaDB with metadata isolation (`user_id` + `language`)
- PDF export of a lesson (safe degradation on missing fields)
- Minimal WebSocket “Chat Tutor” (ephemeral memory; explicit fallback)

## Scope / tenant model

This repository is **single-tenant demo by default** (`default_user`). Most endpoints accept `user_id` as a query parameter for future multi-user support, but this build does **not** ship authentication/authorization.

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
```

## Repository hygiene

Runtime data is excluded from git:

- `data/*.db` (SQLite)
- `data/chroma_db/` (Chroma persistent store)
- `frontend/node_modules/`, `frontend/dist/`

## License

MIT — see `LICENSE`.

