# Usage Guide

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

## End-to-End Functional Check (demo flow)

1. Onboarding
- Open `http://localhost:5173`
- Choose language, level, and difficulty

2. Generate lesson
- Go to Today page
- Click Generate

3. Review (lesson scoring)
- Answer grammar and reading questions
- Click Submit Review
- Re-submitting the same lesson is allowed, but **XP/progress/SRS side-effects are only awarded once per lesson**
- If you submit with unanswered questions, they are counted as incorrect (by design)

4. SRS Review (due items)
- Open Review page
- Confirm you can review due items (Easy/Hard/Forgot)

5. Progress
- Open Progress page
- Verify completed lessons and accuracy update

6. Archive and lesson detail
- Open Archive page
- Click View Lesson on one item

7. Writing analysis
- Open Writing page
- Submit text and verify analysis response

8. Study plan
- Open Progress page
- Enter target goal in Study Plan section

9. Excel import (vocabulary)
- Archive page → Excel Import
- Select English or Japanese in the language filter (imports are disabled while filter is `All`)
- Upload `.xlsx` with at least:
  - `word`
  - `definition` or `definition_zh`
- Optional columns:
  - `reading`
  - `example` or `example_sentence`
  - `example_translation`

10. Imported vocabulary management
- Open Vocabulary page
- Verify imported items list and deletion works

11. RAG upload + management
- Archive page → RAG Upload (select a language)
- Supported upload formats: `.txt`, `.md`, `.csv`, `.pdf`
- Open Materials page
- Verify materials list and deletion works (non-existent `doc_id` returns 404)
- If the backend runs with `ENABLE_RAG=false`, the materials list should still load, while upload/delete return a clear unavailable error

12. PDF export
- Today page → Export PDF
- User text containing `<tag> & "quotes"` should not crash export

13. Chat Tutor (Preview)
- Open Chat (Preview) page
- This is a preview UI and requires a configured AI provider
- If the AI provider is not configured/available, expect the UI to show a connection failure message

## Notes on Current Build

- Single-tenant demo: backend enforces `user_id=default_user` (no auth shipped). The frontend does not send `user_id`; the API defaults to the demo user internally.
- TTS (API only): endpoint returns `available=false` unless a real provider is integrated (`backend/tts_service.py`). No TTS UI in this build.
- RAG: uploads go to Chroma when available; materials are chunked per document and keep stable metadata. When RAG is disabled on the backend, listing still works and mutating endpoints return an unavailable error.

## Tests

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
ENABLE_RAG=false MAX_UPLOAD_SIZE_MB=10 python -m pytest tests -q
```

```bash
cd frontend
npm ci
npm run test:ci
npm run build
```

## Playwright e2e (mocked acceptance)

This suite does not require a backend:

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
npm run e2e -- --project=chromium
```

## Playwright e2e (full-stack)

This suite starts the real backend and real frontend automatically:

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
```

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
npm run e2e:fullstack -- --project=chromium
```

The full-stack test uses deterministic fallback lesson generation plus `/api/demo/reset`, so it does not depend on a live LLM response.
