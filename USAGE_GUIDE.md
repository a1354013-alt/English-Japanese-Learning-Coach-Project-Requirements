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
```

### Frontend

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npm ci
npm run dev
```

Frontend note: the current dependency tree requires `Node.js 22.18.0+`. Using Node 20 can fail during `npm ci`, typecheck, test, or build.

## End-to-End Functional Check

1. Onboarding
- Open `http://localhost:5173`
- Choose language, level, and difficulty

2. Generate lesson
- Go to Today page
- Click Generate

3. Review
- Answer grammar and reading questions
- Click Submit Review
- Re-submitting the same lesson is allowed: XP and completed lesson count are awarded once, progress keeps the best score for that lesson, and SRS is refreshed from the latest attempt
- If you submit with unanswered questions, they are counted as incorrect by design

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
- Optional columns: `reading`, `example`, `example_sentence`, `example_translation`

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

- Single-tenant demo: backend enforces `user_id=default_user`; the frontend does not send `user_id`.
- TTS is API-only and provider-ready. `POST /api/tts` returns `available=false` with a clear preview message unless a real provider is configured.
- RAG uploads go to Chroma when available; materials are CJK-aware chunked per document and keep stable metadata.
- When RAG is disabled, listing still works and mutating endpoints return an unavailable error.

## Tests

```bash
cd backend
python -m compileall .
pip-audit -r requirements.txt
ENABLE_RAG=false MAX_UPLOAD_SIZE_MB=10 python -m pytest -q
```

```bash
cd frontend
node -v   # should be 22.18.0 or newer
npm ci
npm audit
npm audit --omit=dev
npm run typecheck
npm run test:ci
npm run build
```

## Playwright E2E

Mocked acceptance suite:

```bash
cd frontend
npm ci
node -v   # should be 22.18.0 or newer
npx playwright install --with-deps chromium
RUN_E2E=1 npm run e2e -- --project=chromium
```

Full-stack suite:

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
```

```bash
cd frontend
npm ci
node -v   # should be 22.18.0 or newer
npx playwright install --with-deps chromium
npm run e2e:fullstack -- --project=chromium
```

The full-stack test uses deterministic fallback lesson generation plus `/api/demo/reset`, so it does not depend on a live LLM response.
