# English-Japanese Learning Coach

**Version: 1.2.0** — Portfolio-grade AI learning platform

A comprehensive AI-powered language learning platform built with FastAPI + Vue 3, featuring personalized lesson generation, SRS vocabulary tracking, gamification, and RAG-enhanced content.

## 🎯 Project Overview

This project demonstrates **full-stack engineering discipline** with:

- Clean modular architecture (routers, services, shared models)
- Async-first design with proper error handling
- Type safety across backend (Pydantic v2) and frontend (TypeScript)
- Retrieval-augmented generation (RAG) for personalized learning
- Gamification engine with XP, levels, achievements, and word cards
- Reproducible developer workflow (Docker, tests, documented setup)

---

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Vue 3 Frontend    │ ◄─────► │   FastAPI Backend   │
│   (TypeScript)      │  HTTP   │   (Python 3.11+)    │
│   - Vite build      │         │   - Async routers   │
│   - Vue Router      │         │   - Pydantic models │
│   - Axios client    │         │   - SQLite + Chroma │
└─────────────────────┘         └──────────┬──────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
           ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
           │   SQLite (DB)   │   │  ChromaDB (RAG) │   │   Ollama LLM    │
           │   - Lessons     │   │  - Documents    │   │   - Generation  │
           │   - Progress    │   │  - Embeddings   │   │   - Analysis    │
           │   - SRS/Vocab   │   │  - Metadata     │   │   - Chat        │
           │   - Gamification│   └─────────────────┘   └─────────────────┘
           └─────────────────┘
```

### Data Flow

1. **Lesson Generation**: User request → LLM prompt → Structured JSON → SQLite storage → Frontend render
2. **Review/SRS**: User answers → Scoring service → XP/progress update → SRS interval calculation → DB persistence
3. **RAG Upload**: File upload → Text extraction → Chunking (metadata: source, language, timestamp) → ChromaDB embedding
4. **RAG Query**: Search query → Vector similarity → Retrieved chunks → LLM context → Personalized lesson/explanation

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Pydantic v2, SQLite, APScheduler |
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Axios |
| AI/ML | Ollama (local LLM), ChromaDB (vector store) |
| DevOps | Docker Compose, GitHub Actions (CI), pytest, vitest |

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| AI Lesson Generation | ✅ Stable | EN (CEFR A1-C2) / JP (JLPT N5-N1) |
| Spaced Repetition (SRS) | ✅ Stable | SM-2 algorithm, vocabulary tracking |
| Gamification Engine | ✅ Stable | XP, levels, achievements, word cards |
| Wrong Answer Notebook | ✅ Stable | CRUD + retry practice |
| Daily Streak Tracking | ✅ Stable | Derived from learning activity log |
| RAG Document Upload | ✅ Stable | .txt/.md/.csv with metadata |
| Writing Analysis | ✅ Stable | Grammar, vocabulary, style scoring |
| Study Plan Generation | ✅ Stable | Milestone-based planning |
| PDF Export | ✅ Stable | Cross-platform with CJK font support |
| Excel Vocabulary Import | ✅ Stable | Requires explicit language selection |
| TTS Audio Generation | ⚠️ Placeholder | Returns `null` audio_url; ready for integration |
| WebSocket AI Chat | ⚠️ Beta | Ephemeral session memory; no persistence |
| User Authentication | ⚠️ Demo Only | Single `default_user` ID; add real auth before production |
| Persistent Chat Memory | 📋 Planned | User profile memory under roadmap |
| OAuth2/JWT Auth | 📋 Planned | Production authentication roadmap |
| E2E Testing | 📋 Planned | Playwright integration planned |

---

## Repository Layout

| Path | Role |
|------|------|
| `backend/main.py` | FastAPI app, CORS, lifespan, router includes |
| `backend/routers/` | API routers: `lessons`, `review`, `imports`, `ai_tools`, `system`, `streak`, `wrong_answers` |
| `backend/services/` | Shared domain helpers (`lesson_ops.py`: load lesson, score answers, SRS/progress hooks) |
| `backend/tests/` | Pytest suite (run `pytest tests/` from `backend/`) |
| `frontend/` | Vue 3 + Vite + TypeScript application |
| `frontend/src/views/` | Page components: TodayLesson, LessonDetail, Archive, Progress, WrongAnswers, WritingCenter |
| `frontend/src/services/` | API client layer with TypeScript types |
| `data/` | Runtime data (SQLite DB, ChromaDB, exports — gitignored) |
| `docker-compose.yml` | API service + volume mounts for `/data` |
| `.github/workflows/ci.yml` | CI pipeline (pytest, vitest, type check) |

Legacy scripts: `start_backend.sh`, `start_frontend.sh` (bash wrappers).

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama running locally (or set `OLLAMA_URL` to remote instance)
- Optional: Docker Compose for containerized deployment

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

### 3. Docker (API only)

```bash
docker compose up --build
```

Point the Vite dev server at `http://localhost:8000` (default proxy target).

---

## Environment Variables

See `backend/.env.example`. Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `CORS_ORIGINS` | Comma-separated allowed browser origins | `http://localhost:5173` |
| `DEFAULT_USER_ID` | Demo user ID for routes accepting `user_id` | `default_user` |
| `DATA_DIR` | Base directory for runtime data | `./data` |
| `DB_PATH` | SQLite database path | `./data/language_coach.db` |
| `CHROMA_DB_PATH` | ChromaDB persistent path | `./data/chroma_db` |
| `OLLAMA_URL` | Ollama API endpoint | `http://localhost:11434` |
| `SMALL_MODEL_NAME` | Model for chat/fast tasks | `llama3.2` |
| `LARGE_MODEL_NAME` | Model for lesson generation | `llama3.1` |

---

## Tests & Build

### Backend Tests

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
python -m compileall .
```

### Frontend Tests & Build

```bash
cd frontend
npm install
npm run test
npm run build
```

Build output: `frontend/dist/`

---

## Demo Flow

Follow this flow to experience the full platform capabilities:

1. **Generate Lesson** → Select language (EN/JP), level, difficulty → AI generates structured lesson
2. **Complete Exercises** → Answer grammar & reading questions → Receive instant scoring + XP
3. **Review Results** → View detailed feedback → Wrong answers saved to Mistakes notebook
4. **See Progress Update** → Check Progress tab → Watch XP, level, and streak grow
5. **Upload Notes (RAG)** → Upload .txt/.md files in Archive → Materials chunked and indexed
6. **Generate Personalized Lesson** → RAG-enhanced lessons use your uploaded materials
7. **Chat with Tutor** → Practice conversation in target language → WebSocket real-time chat
8. **View Analytics** → Identify hardest words, weakest categories, accuracy trends
9. **Export PDF** → Download complete lesson with vocabulary, grammar, reading, dialogue

---

## Screenshots

### Dashboard - Today Lesson
![Dashboard](./docs/screenshots/dashboard.png)
*Generate AI-powered lessons tailored to your level*

### Lesson Detail
![Lesson Detail](./docs/screenshots/lesson-detail.png)
*Complete lesson with vocabulary, grammar, reading, and dialogue sections*

### Chat Tutor
![Chat Tutor](./docs/screenshots/chat.png)
*Real-time conversation practice with AI tutor*

### Analytics Dashboard
![Analytics](./docs/screenshots/analytics.png)
*Track progress, identify weak areas, monitor streaks*

> **Note**: Screenshots are placeholders. Run the application and capture actual screens for your portfolio.

---

## Minimal Verification Flow

1. **Onboarding** → Select language (EN/JP), level, difficulty
2. **Generate Lesson** (Today tab) → AI generates structured lesson
3. **Submit Review** → Answer grammar/reading questions → See score + XP gain
4. **Archive** → View past lessons → Click into Lesson Detail
5. **Writing Center** → Submit text → Get AI analysis
6. **Study Plan** (Progress tab) → Generate milestone-based plan
7. **Excel Import** (Archive) → Upload vocabulary (select EN or JP language)
8. **RAG Upload** (Archive) → Upload .txt/.md/.csv materials
9. **Export PDF** → Download lesson as PDF

> **Note**: Imports require explicit language selection (English or Japanese). "All" filter is blocked for imports.

---

## Known Limitations

| Limitation | Impact | Workaround / Roadmap |
|------------|--------|---------------------|
| Demo authentication only | All data scoped to `default_user` | Add OAuth2/JWT before multi-user deployment |
| TTS returns placeholder | No audio playback in lessons | Integrate Azure TTS / Google Cloud TTS / Edge TTS |
| Chat uses ephemeral memory | Conversation history lost on disconnect | Implement persistent user memory store |
| No E2E tests | Manual QA required for full flows | Add Playwright test suite |
| Single-file RAG uploads only | Bulk upload not supported | Add ZIP/folder upload with batch processing |

---

## Portfolio Talking Points

This project showcases:

1. **Full-Stack Architecture**: Clean separation of concerns (routers, services, models), async patterns, dependency injection
2. **AI Integration**: Prompt engineering, structured JSON extraction, fallback handling, caching strategies
3. **Retrieval-Augmented Workflows**: Vector embeddings, semantic search, metadata filtering, citation tracking
4. **Product Thinking**: Gamification loops, spaced repetition, error tracking, progressive difficulty
5. **Engineering Discipline**: Type safety, test coverage, reproducible builds, documented APIs, Docker deployment
6. **Data Modeling**: Relational schema design, SRS algorithm implementation, activity logging, analytics hooks

---

## Roadmap

- [ ] Persistent chat memory with user profiles
- [ ] Production TTS integration (Azure/Google/Edge)
- [ ] OAuth2/JWT authentication with role-based access
- [ ] E2E testing with Playwright
- [ ] Real-time WebSocket improvements (typing indicators, presence)
- [ ] Bulk RAG upload (ZIP/folder support)
- [ ] Mobile-responsive UI enhancements
- [ ] Analytics dashboard (learning trends, time spent, weak areas)

---

## License

MIT License — See LICENSE file for details.

---

## Repository Hygiene

**Note**: `node_modules` and build artifacts are excluded from version control. Run `npm install` and `npm run build` to reproduce the build.

### Excluded from Git

- `frontend/node_modules/` - npm dependencies
- `frontend/dist/` - Vite build output
- `data/*.db` - SQLite database (runtime data)
- `data/chroma_db/` - Vector store (runtime data)
- `__pycache__/` - Python bytecode
- `.pytest_cache/`, `.mypy_cache/` - Testing caches
- `coverage/`, `htmlcov/` - Test coverage reports

This keeps the repository clean, lightweight, and focused on source code.

---

## License

MIT License — See LICENSE file for details.
