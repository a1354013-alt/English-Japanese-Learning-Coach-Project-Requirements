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

4. Progress
- Open Progress page
- Verify completed lessons and accuracy update

5. Archive and lesson detail
- Open Archive page
- Click View Lesson on one item

6. Writing analysis
- Open Writing page
- Submit text and verify analysis response

7. Study plan
- Open Progress page
- Enter target goal in Study Plan section

8. Excel import
- Archive page -> Excel Import
- Upload `.xlsx` with at least:
  - `word`
  - `definition` or `definition_zh`
- Optional columns:
  - `reading`
  - `example` or `example_sentence`
  - `example_translation`

9. RAG upload
- Archive page -> RAG Upload
- Upload `.txt`, `.md`, or `.csv`

10. PDF export
- Today page -> Export PDF

## Notes on Current Build

- TTS endpoint is available but returns no audio file unless a real TTS engine is integrated.
- Chat memory currently uses explicit fallback text (no persistent memory source in this release).
- RAG behavior depends on local vector runtime availability.
