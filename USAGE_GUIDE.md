# Usage Guide

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
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
- Select English or Japanese in the language filter (imports are disabled while filter is “All”)
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
- Open Materials page
- Verify materials list and deletion works

12. PDF export
- Today page → Export PDF

## Notes on Current Build

- Single-tenant demo: backend enforces `user_id=default_user` (no auth shipped).
- TTS: endpoint exists, but returns `available=false` unless a real provider is integrated (`backend/tts_service.py`).
- RAG: uploads go to Chroma when available; when RAG is disabled on the backend, upload/delete returns an error.

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
```

