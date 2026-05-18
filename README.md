# English-Japanese Learning Coach

Portfolio-grade **AI English-Japanese Learning Coach** built with **FastAPI**, **Vue 3 + TypeScript**, **SQLite**, **spaced repetition**, **chunked RAG lesson evidence**, **wrong-answer review**, **progress analytics**, and **gamification**.

The project is designed for live demos: it can generate EN/JP lessons, score reviews, update learner progress, track wrong answers, export PDFs, and reset demo data back to a presentable state.

TTS is currently integration-ready rather than provider-backed: `POST /api/tts` returns `available=false` with an explicit message unless a real runtime provider is configured.

## Highlights

- FastAPI backend with typed APIs for lessons, review, analytics, imports, demo reset, and tutor tools
- Vue 3 + TypeScript frontend with i18n, workspace flows, progress dashboards, wrong-answer review, and writing support
- Optional RAG integration via ChromaDB, with chunked material storage plus safe disabled mode for CI and lightweight demos
- SRS and gamification flows that avoid duplicate XP on repeated submissions
- TTS provider-ready placeholder with a stable unavailable response shape; this is not shipped as full voice synthesis
- SQLite persistence with migration smoke tests and index coverage
- Dockerized backend with persistent `/data` volume and non-root runtime

## Architecture

```mermaid
flowchart LR
    UI["Vue 3 Frontend"] -->|REST / WebSocket| API["FastAPI Backend"]
    API --> LESSON["Lesson Generator"]
    API --> REVIEW["Review + SRS + Analytics"]
    API --> IMPORTS["Vocabulary / Material Imports"]
    API --> DEMO["Demo Reset Seeder"]
    LESSON --> OLLAMA["Ollama / Local LLM"]
    LESSON --> RAG["RAG Manager"]
    RAG --> CHROMA["ChromaDB (Optional)"]
    REVIEW --> DB["SQLite"]
    IMPORTS --> DB
    DEMO --> DB
    API --> FILES["Lesson JSON / PDF / Audio Files"]
```

Text architecture: the Vue frontend talks to the FastAPI backend through typed REST clients. FastAPI persists progress, lessons, SRS, wrong answers, activity streaks, and analytics in SQLite. RAG is optional and disabled by default; when enabled it stores chunked material metadata in ChromaDB. TTS is integration-ready and currently returns an explicit preview/unavailable contract until a real provider is configured.

## Demo Flow

1. Open `Today` and generate an English or Japanese lesson.
2. Complete grammar and reading questions.
3. Submit review results to update progress, SRS, and wrong-answer records.
4. Show `Progress`, `Vocabulary`, `Wrong Answers`, `Analytics`, `Workspace`, and `Writing Center`.

Reset demo data at any time:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/reset
```

## Repository Layout

- `backend/` FastAPI application, database layer, lesson generation, tests, Docker image
- `frontend/` Vue 3 application, i18n resources, service client, Vitest and Playwright tests
- `docs/screenshots/` suggested portfolio screenshots
- `data/` runtime data directory kept in git only as `data/.gitkeep`
- `LICENSE` project license

## Environment

Backend environment variables:

- `DATA_DIR` runtime data directory
- `DB_PATH` SQLite database path
- `CHROMA_DB_PATH` Chroma persistence directory
- `ENABLE_RAG` defaults to `false`; set `true` only after installing `backend/requirements-rag.txt`
- `MAX_UPLOAD_SIZE_MB` maximum upload size for import and RAG material endpoints, defaults to `10`
- `CORS_ORIGINS` comma-separated frontend origins
- `LOG_LEVEL` backend log level

Frontend environment variables:

- `VITE_API_BASE_URL` defaults to `http://localhost:8000/api`
- `VITE_WS_BASE_URL` defaults to `ws://localhost:8000`

Runtime requirements:

- Frontend tooling requires `Node.js 22.18.0+` because the current Vite/Vitest dependency tree includes packages that no longer support Node 20.

Use `backend/.env.example` as the source of truth for local configuration. Do not commit real secrets or provider credentials. For local development, RAG is disabled by default. Enable it only after installing `backend/requirements-rag.txt` and setting `ENABLE_RAG=true`.

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt -r requirements-dev.txt
# Optional: install RAG dependencies only when you want ENABLE_RAG=true
# python -m pip install -r requirements-rag.txt
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npm ci
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Docker

The provided Compose file starts the backend API only. The frontend is intended to run with `npm run dev` on the host during development.

```bash
docker compose up --build
```

The API is exposed at [http://localhost:8000](http://localhost:8000). Health is available at [http://localhost:8000/api/health](http://localhost:8000/api/health), and the compose configuration defaults `ENABLE_RAG=false` plus `MAX_UPLOAD_SIZE_MB=10` for reliable startup in environments without ChromaDB.

## Testing

### Backend

```bash
python -m compileall backend
ruff check backend tests
mypy backend
pip-audit -r backend/requirements.txt
ENABLE_RAG=false MAX_UPLOAD_SIZE_MB=10 pytest
```

### Frontend

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npm ci
npm audit
npm audit --omit=dev
npm run typecheck
npm run lint
npm run format:check
npm run test:ci
npm run build
```

### Mocked Frontend E2E

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npx playwright install --with-deps chromium
RUN_E2E=1 npm run test:e2e -- --project=chromium
```

Playwright mocked E2E starts only the Vite dev server and mocks lesson, review, progress, analytics, streak, onboarding, and PDF export APIs inside the test run.

- No backend startup is required for `cd frontend && npm run test:e2e -- --project=chromium`
- No Ollama, ChromaDB, network access, or other external services are required
- The E2E lesson flow uses stable mocked lesson/review responses instead of relying on live generation

### Full-Stack E2E

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
```

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npx playwright install --with-deps chromium
npm run test:e2e:fullstack -- --project=chromium
```

The full-stack Playwright suite starts:

- a real FastAPI backend on `http://127.0.0.1:8000`
- a real Vite frontend on `http://127.0.0.1:4273`

It uses `POST /api/demo/reset` before and after the run to seed deterministic demo data, exercises the real `lesson generate -> review submit -> progress updated` path plus wrong-answer/PDF flows, and keeps `ENABLE_RAG=false` so the run does not depend on ChromaDB.

### CI E2E Policy

- `npm run test:e2e` is the default CI-safe acceptance check because it is API-mocked and deterministic.
- `npm run test:e2e:fullstack` is reserved for `workflow_dispatch` / manual verification because it boots both servers and exercises real persistence.
- Both suites share the same user-facing lesson flow, but only the full-stack suite validates backend persistence and demo reset behavior.

### Docker

```bash
docker compose config
docker compose build
docker compose up
```

## Screenshots

`docs/screenshots/` currently contains a checklist rather than committed screenshots. Capture real images only after running the app locally so the portfolio reflects the actual UI:

- Dashboard / Home
- Today Lesson
- Review Result
- Progress / Analytics
- Wrong Answer Notebook
- Materials / RAG

## Portfolio Signals

This project is intended to demonstrate engineering quality rather than flashy feature breadth: typed API contracts, migration-safe SQLite persistence, deterministic review scoring, SRS, gamification idempotency, RAG chunking contracts, frontend state/error handling, mocked E2E coverage, dependency audits, Docker config validation, and CI quality gates.

## Reliability Notes

- Importing `backend/main.py` does not require `chromadb` or `sentence-transformers` when `ENABLE_RAG=false`.
- `backend/requirements-rag.txt` contains the optional Chroma / embedding dependencies for RAG-enabled environments.
- If `ENABLE_RAG=true` but `chromadb` or `sentence-transformers` is not installed, the app still starts and RAG endpoints return a clear service-unavailable error instead of crashing startup.
- Upload endpoints enforce a `MAX_UPLOAD_SIZE_MB` limit with chunked reads and return HTTP `413` with code `FILE_TOO_LARGE` when exceeded.
- Excel import is intentionally `.xlsx` only. The backend uses `openpyxl`, and the frontend/file validation/docs now match that contract.
- RAG uploads support `.txt`, `.md`, `.csv`, and `.pdf`. Stored vectors are CJK-aware chunked per material and keep stable metadata for `material_id`, `title`, `language`, `source_type`, `chunk_index`, `total_chunks`, and `uploaded_at`.
- Re-submitted lesson reviews do not duplicate XP or completed lesson count; progress keeps the best per-lesson score while SRS reflects the latest attempt.
- When `ENABLE_RAG=false`, `GET /api/rag/materials` still returns a stable empty list while mutating endpoints return a clear unavailable error.
- Playwright E2E is intentionally mocked at the API layer so CI does not depend on backend process startup, demo seed state, or real LLM/Ollama availability.
- The separate full-stack Playwright suite validates the real seed-reset and persistence path without making every PR wait on a two-process browser test.
- Lesson generation can fall back to deterministic sample content when the model path fails.
- Demo reset rebuilds stable sample data for portfolio walkthroughs.

## License

MIT. See [LICENSE](LICENSE).
