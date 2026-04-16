# English-Japanese Learning Coach

**Version: 1.2.0** - Production Ready for Portfolio Showcase

A comprehensive AI-powered language learning platform built with FastAPI + Vue 3, featuring personalized lesson generation, SRS vocabulary tracking, gamification, and RAG-enhanced content.

## 🎯 Project Highlights (Portfolio-Ready Features)

### Architecture Excellence
- **Clean Architecture**: Modular routers (`backend/routers/`), shared services (`backend/services/`), clear separation of concerns
- **Async-First Design**: Non-blocking LLM calls via `httpx.AsyncClient`, proper event loop handling
- **Type Safety**: Full Pydantic v2 models, TypeScript frontend, strict API contracts
- **Database Layer**: SQLite with migrations, connection pooling, transaction management

### Key Features Implemented
- ✅ **AI Lesson Generation**: Dynamic lessons tailored to user level, interests, and goals
- ✅ **Spaced Repetition System (SRS)**: SM-2 algorithm for vocabulary retention
- ✅ **Gamification Engine**: XP system, leveling, achievements, collectible word cards
- ✅ **RAG Integration**: ChromaDB vector store for semantic search over uploaded materials
- ✅ **Writing Analysis**: AI-powered grammar, vocabulary, and style feedback
- ✅ **Study Planning**: Personalized milestone-based study plans
- ✅ **Multi-language Support**: English (CEFR) and Japanese (JLPT) tracks
- ✅ **PDF Export**: Cross-platform lesson export with CJK font support
- ✅ **Daily Streaks**: Learning activity tracking with timezone awareness
- ✅ **Auto-Scheduler**: APScheduler for daily lesson generation

### Code Quality & DevOps
- ✅ **Multi-stage Dockerfile**: Optimized image size, non-root user, health checks
- ✅ **CI/CD Pipeline**: GitHub Actions with pytest, vitest, type checking
- ✅ **Comprehensive Tests**: Unit tests for routers, services, and integrations
- ✅ **Documentation**: Detailed `.env.example`, API docs (Swagger/OpenAPI)

---

## Project Status

### ✅ Production Ready
- FastAPI backend with unified API contracts
- SQLite persistence with migrations
- Async Ollama client with retry logic and caching
- RAG-enhanced lesson generation
- Vue 3 + TypeScript frontend with error handling
- Docker Compose deployment
- Automated testing suite

### ⚠️ Beta / Placeholder (Documented Limitations)
- TTS endpoint returns placeholder (ready for integration)
- Chat uses ephemeral memory (persistent memory planned)
- Demo authentication only (`DEFAULT_USER_ID`) - **add real auth before production**

### 📋 Roadmap
- [ ] Persistent chat memory with user profiles
- [ ] Production TTS integration (Azure/Google/Edge)
- [ ] OAuth2/JWT authentication
- [ ] E2E testing with Playwright
- [ ] WebSocket improvements for real-time features

---

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
