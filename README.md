# English-Japanese Learning Coach

A single-project delivery build focused on reproducibility and stable contracts between backend and frontend.

## Project Status

### Completed
- FastAPI backend with unified API contracts for onboarding, lesson generation, today/archive/detail lessons, review, progress, writing analysis, study plan, Excel import, RAG upload, PDF export
- SQLite persistence for lessons, progress, exercise results, SRS, imported vocabulary
- Modular routes under `backend/routers/` and shared helpers under `backend/services/`
- Async Ollama client (`httpx.AsyncClient`) for non-blocking LLM calls
- **RAG**: uploaded materials are stored in Chroma; **lesson generation** runs optional retrieval (`rag_manager.query_materials`) and appends matching excerpts to the model prompt when Chroma is enabled (same-language filter on metadata when supported by the local Chroma version)
- Frontend Vue 3 + TypeScript, centralized API error banner via Axios interceptor
- Minimal CI (GitHub Actions): backend `pytest` + `compileall`, frontend `vitest` + `npm run build`
- Optional **Docker Compose** stack for the API with a persistent data volume

### Partially Completed (Beta / Placeholder)
- TTS endpoint returns no audio unless a real engine is integrated
- Chat memory uses explicit fallback text (no persistent user memory)
- **Auth**: single demo user; `DEFAULT_USER_ID` and query param `user_id` are aligned for local use only—add real authentication before any public deployment

### Planned
- Persistent user memory for chat
- Production-grade TTS
- Broader automated tests (integration / E2E)

## Repository Layout

| Path | Role |
|------|------|
| `backend/main.py` | FastAPI app, CORS (from `CORS_ORIGINS`), lifespan, router includes |
| `backend/routers/` | `lessons`, `review`, `imports`, `ai_tools`, `system` API routers |
| `backend/services/` | Shared domain helpers (e.g. `lesson_ops.py`: load lesson JSON, score answers, SRS/progress hooks) |
| `backend/tests/` | Pytest suite (`pytest tests/` from `backend/`) |
| `frontend/` | Vue 3 + Vite + TypeScript |
| `data/` | Runtime data (gitignored contents) |
| `docker-compose.yml` | API service + volume for `/data` |
| `.github/workflows/ci.yml` | CI pipeline |

Legacy scripts: `start_backend.sh`, `start_frontend.sh` (bash).

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`  
Backend default URL: `http://localhost:8000`

### 3. Docker (API only)

```bash
docker compose up --build
```

Point the Vite dev server at `http://localhost:8000` (default proxy). Set `CORS_ORIGINS` in Compose or `.env` if you use another frontend origin.

## Environment Variables (`backend/.env`)

See `backend/.env.example`. Notable entries:

| Variable | Purpose |
|----------|---------|
| `CORS_ORIGINS` | Comma-separated allowed browser origins (no JSON array) |
| `DEFAULT_USER_ID` | Default demo user for routes that accept `user_id` |
| `DATA_DIR` / `DB_PATH` / `CHROMA_DB_PATH` | Storage locations |
| Ollama / Redis / scheduler | As in `.env.example` |

## Tests & Build

### Backend

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
python -m compileall .
```

### Frontend

```bash
cd frontend
npm install
npm run test
npm run build
```

## Minimal Verification Flow

1. Onboarding → 2. Generate lesson (Today) → 3. Submit review → 4. Archive / lesson detail → 5. Writing → 6. Study plan (Progress) → 7. Excel import & RAG upload (**select EN or JP** in Archive; “All” is blocked for imports) → 8. Export PDF

## Excel / RAG language (Archive)

Imports require an explicit language (English or Japanese). If the filter is “All”, the UI prompts you to pick a language first.
