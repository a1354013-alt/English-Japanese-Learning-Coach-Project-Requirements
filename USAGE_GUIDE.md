# Usage Guide

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt -r requirements-dev.txt
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/ready
```

### Frontend

```bash
cd frontend
node -v   # should be >= 22.18.0
nvm use   # optional, uses the repo-pinned 22.18.0 from .nvmrc / .node-version
npm ci
npm run dev
```

Frontend note: the current dependency tree requires `Node.js >= 22.18.0`. Using Node 20 can fail during `npm ci`, typecheck, test, or build.

Runtime data note: keep only `data/.gitkeep` in version control. Local SQLite files, generated lessons, audio, exports, and SQLite-backed RAG data should stay untracked under `data/` or another `DATA_DIR`.

Production readiness note: this project currently runs as a single-user/local demo learning coach. It does not include production-grade authentication, authorization, user isolation, rate limiting, or audit logging by default.

## Test Lane Guide

- Standard tests: default release gate, no RAG dependency required.
- Optional RAG tests: validate the SQLite-backed RAG store with `ENABLE_RAG=true`.
- Mocked E2E: stable browser coverage with deterministic API mocks.
- Full-stack smoke: real backend + frontend with demo seed data, but still no live LLM requirement.

## End-to-End Functional Check

1. Onboarding
- Open `http://localhost:5173`
- Choose language, level, and difficulty

2. Generate lesson
- Go to Today page
- Click Generate
- The generated lesson is a textbook-style unit: objectives, vocabulary, word roots or affixes, sentence patterns, grammar, dialogue, reading, text shadowing, exercises, Feynman self-explanation, and a spaced review plan.
- Immersion/shadowing is currently text-based. TTS remains a provider-ready placeholder unless a real provider is configured.

3. Review
- Answer grammar and reading questions
- Click Submit Review
- Re-submitting the same lesson is allowed: XP and completed lesson count are awarded once, progress keeps the best score for that lesson, and SRS is refreshed from the latest attempt
- All grammar and reading questions must be answered before submission. The frontend blocks incomplete reviews, and the backend rejects incomplete, duplicate, out-of-range, or lesson-mismatched answers with a validation error.

4. SRS review
- Open Review page
- Confirm you can review due items

5. Progress
- Open Progress page
- Verify completed lessons, streak, XP, word cards, and accuracy update

6. Archive and lesson detail
- Open Archive page
- Click View Lesson on one item

7. Writing analysis
- Open Writing page
- Submit text and verify analysis response

8. Study plan
- Open Progress page
- Enter a target goal in the Study Plan section

9. Excel import
- Archive page -> Excel Import
- Select English or Japanese in the language filter; imports are disabled while filter is `All`
- Upload `.xlsx` with at least `word` and `definition` or `definition_zh`
- Optional columns: `reading`, `example`, `example_sentence`, `example_translation`, `part_of_speech`, `root`, `prefix`, `suffix`, `word_family`, `memory_tip`, `category`, `tags`
- `word_family` and `tags` may be comma-separated. Imported roots, categories, and memory tips appear in the vocabulary list and SRS due-card review.

10. Imported vocabulary management
- Open Vocabulary page
- Verify imported items list and deletion works

11. RAG upload and management
- Archive page -> RAG Upload, then select a language
- Supported upload formats: `.txt`, `.md`, `.csv`, `.pdf`
- Open Materials page
- Verify materials list and deletion works
- If the backend runs with `ENABLE_RAG=false`, the materials list should still load, while upload/delete return a clear unavailable error

12. PDF export
- Today page -> Export PDF
- User text containing `<tag> & "quotes"` should not crash export

13. Chat Tutor preview
- Open Chat page
- This is a preview UI and requires a configured AI provider
- If the AI provider is unavailable, expect a connection failure message

## Current Build Notes

- Single-user/local demo: backend enforces `user_id=default_user`; the frontend does not send `user_id`.
- TTS is integration-ready but disabled by default. No real TTS provider is enabled unless configured; `POST /api/tts` returns `available=false` with a clear preview message unless a real provider is configured.
- VS Code F5 one-click startup is supported through the checked-in `.vscode/launch.json` and `.vscode/tasks.json`; use `F5: Backend + Frontend` after backend/frontend dependencies are installed.
- Core mode works with `ENABLE_RAG=false`; RAG mode sets `ENABLE_RAG=true` and runs the separate SQLite-backed RAG verification lane.
- RAG uploads are stored as CJK-aware chunks in the local SQLite-backed RAG database and keep stable metadata.
- When RAG is disabled, listing still works and mutating endpoints return an unavailable error.

## Tests

Standard backend checks:

```bash
cd backend
python -m compileall -q .
python -m ruff check .
python -m mypy .
python -m pytest -q
```

Optional RAG smoke check:

```bash
cd backend
python -m pip install -r requirements-rag.txt
python -m pytest tests -q -m rag
```

```bash
cd frontend
node -v   # should be >= 22.18.0
npm ci
npm audit
npm audit --omit=dev
npm run typecheck
npm run lint
npm run format:check
npm run test:ci
npm run build
```

Release helper:

```bash
python scripts/verify_delivery.py
```

The standard helper includes production and full frontend audits. Optional RAG, Playwright, Docker, and pip-audit checks are reported as explicit skipped/warning entries when the local environment is missing the required dependency.

## Playwright E2E

Mocked acceptance suite:

```bash
cd frontend
node -v   # should be >= 22.18.0
npm ci
npx playwright install --with-deps chromium
RUN_E2E=1 npm run test:e2e -- --project=chromium
```

Full-stack suite:

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
```

```bash
cd frontend
node -v   # should be >= 22.18.0
npm ci
npx playwright install --with-deps chromium
npm run test:e2e:fullstack -- --project=chromium
```

### Mocked vs Full-Stack E2E

- `npm run test:e2e` is the default CI path. It runs only the frontend dev server and mocks lesson, review, progress, analytics, streak, onboarding, and PDF export APIs. Use it for fast regression checks.
- `npm run test:e2e:fullstack` starts the real FastAPI backend and real Vite frontend. The backend process for this flow must set `ALLOW_DEMO_RESET=true` because it calls `POST /api/demo/reset` before the scenario to rebuild deterministic demo data.
- The full-stack suite is better for release smoke tests or `workflow_dispatch`; the mocked suite is better for every PR because it is faster and less sensitive to process startup timing.

## Demo Seed Workflow

1. Start the backend locally with `ALLOW_DEMO_RESET=true`.
2. Call `POST /api/demo/reset`.
3. Walk through Today -> Review -> Progress -> Workspace -> Analytics.
4. Turn `ALLOW_DEMO_RESET` back off outside local demo use.

## Troubleshooting

- Node version mismatch: switch to `22.18.0` using `.nvmrc` or `.node-version`; the minimum supported version is `>= 22.18.0`.
- Optional RAG disabled: leave `ENABLE_RAG=false` for standard development and test flows; set it to `true` only when validating the SQLite-backed RAG lane.
- Ollama unavailable: `/api/health` should still pass; use `/api/ready` to inspect readiness details.
- Frontend API base URL: set `VITE_API_BASE_URL` when the API is not served from the same origin or `/api`.
- Playwright browser missing: run `npx playwright install --with-deps chromium`.
