# English-Japanese Learning Coach

A single-project delivery build focused on reproducibility and stable contracts between backend and frontend.

## Project Status

### Completed
- FastAPI backend with unified API contracts for:
  - onboarding
  - lesson generation
  - today lesson retrieval
  - lesson archive and lesson detail
  - review submission with persistence
  - progress tracking
  - writing analysis
  - study plan generation
  - Excel vocabulary import
  - RAG text upload
  - PDF export
- SQLite persistence for lessons, progress, review results, SRS items, and imported vocabulary
- Frontend TypeScript contracts aligned to backend payloads
- Frontend route coverage includes `/lesson/:id`
- Path handling unified with `settings.data_dir` and absolute path resolution
- `npm` unified as frontend package manager

### Partially Completed (Beta / Placeholder)
- TTS endpoint exists but runtime audio generation is placeholder when no TTS engine is configured
- Chat memory uses explicit fallback text (no persistent user memory source yet)
- RAG quality depends on local Chroma/embedding runtime availability

### Planned
- Persistent user memory service for chat
- Production-grade TTS integration
- Expanded automated tests (unit + integration + E2E)

## Repository Layout

- `backend/` FastAPI application
- `frontend/` Vue 3 + TypeScript application
- `data/` runtime data directory (kept empty in source control)
- `start_backend.sh` backend start script
- `start_frontend.sh` frontend start script

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

## Environment Variables (`backend/.env`)

Use `backend/.env.example` as source. Required keys:
- `OLLAMA_URL`
- `MODEL_NAME`
- `SMALL_MODEL_NAME`
- `LARGE_MODEL_NAME`
- `DATA_DIR`
- `DB_PATH`
- `CHROMA_DB_PATH`
- `REDIS_URL`
- `CACHE_EXPIRE`
- `AUTO_GENERATE_TIME`
- `TIMEZONE`
- `API_HOST`
- `API_PORT`

## Minimal Verification Flow

1. Open frontend and complete onboarding.
2. Generate a lesson from Today page.
3. Submit review answers and confirm progress updates.
4. Open Archive and enter lesson detail page.
5. Run writing analysis in Writing Center.
6. Generate a study plan from Progress page.
7. Import vocabulary Excel from Archive.
8. Upload a RAG text file from Archive.
9. Export lesson PDF from Today page.

## Build Commands

### Frontend
```bash
cd frontend
npm install
npm run build
```

### Backend sanity check
```bash
cd backend
python -m pip install -r requirements.txt
python -m compileall .
```
