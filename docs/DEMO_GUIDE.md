# Demo Guide

Use this guide when you want to present the `v1.4.0-rc2` Adaptive Learning project as a polished portfolio demo instead of only a developer handoff.

## F5 Startup

1. Install backend dependencies with `cd backend && python -m pip install -r requirements.txt -r requirements-dev.txt`.
2. Install frontend dependencies with `cd frontend && npm ci`.
3. Copy `backend/.env.example` to `backend/.env`.
4. Open the repo root in VS Code.
5. Select `F5: Backend + Frontend` in Run and Debug.
6. Press F5 and confirm the backend and frontend both start.

## Manual Smoke Checklist

- [ ] App starts from the documented F5 flow.
- [ ] Today's lesson page loads.
- [ ] Today Mission Panel loads and shows the Daily Study Mission.
- [ ] Micro lesson content loads from the deterministic template bank without a live LLM.
- [ ] Lesson generation works, or the deterministic fallback lesson loads cleanly if live generation is unavailable.
- [ ] Review submission works.
- [ ] Progress updates after review submission.
- [ ] SRS due page works and shows imported review metadata when available.
- [ ] Analytics shows weakest vocabulary, grammar, sentence patterns, and recent 7-day review activity after demo reset.
- [ ] Vocabulary import works with `.xlsx` input.
- [ ] Vocabulary search works for root/category/tags.
- [ ] Wrong answers page works.
- [ ] PDF export works.
- [ ] F5 startup instructions above still match the current repo behavior.

## Recommended Demo Flow

1. Start the backend with `ALLOW_DEMO_RESET=true` for local demo use.
2. Call `POST /api/demo/reset` once to rebuild the deterministic demo dataset.
3. Open the frontend and walk through:
   - Today page
   - Today Mission Panel and Daily Study Mission
   - Seeded micro lesson content from the template bank
   - Due SRS / weak items grouped by vocabulary, grammar, and sentence patterns
   - Analytics weakest vocabulary / grammar / sentence patterns plus recent 7-day review activity
   - Lesson generation or seeded fallback lesson
   - Objectives, vocabulary, word roots, sentence patterns, grammar, dialogue, reading, immersion shadowing, Feynman prompt, and review plan
   - Review submission and progress update
   - SRS review with root/category/memory tip
   - A second lesson generation pass that can reuse weak/recent items through snowball context
   - Feynman explanation submission with structured AI feedback or deterministic fallback feedback
   - Vocabulary import plus search by root/category/tags
   - Wrong answers
   - PDF export

## Demo Notes

- `GET /api/health` is a lightweight liveness check for app + DB only.
- `GET /api/ready` reports optional dependency state such as Ollama / RAG.
- RAG is optional. A demo can succeed with `ENABLE_RAG=false`.
- TTS is provider-ready but disabled by default unless you wire in a real provider.
- Immersion is currently text shadowing only.
- Real recording and speech comparison are not part of the `v1.4.0-rc2` release.
- Demo reset is intentionally protected and should stay disabled outside local demo environments.

## Suggested Presenter Script

- Reset demo data, then start on Today to show the Daily Study Mission and Today Mission Panel.
- Inspect or complete the deterministic micro lesson.
- Open SRS due review to show due weak items.
- Open Analytics to show weakest vocabulary, grammar, sentence patterns, and the recent 7-day activity list.
- Generate or open a lesson and point out the textbook-style sections, especially word roots and the Feynman prompt.
- Submit one review to demonstrate progress, streak, and wrong-answer persistence.
- Open Progress and SRS to show the update plus root/category/memory-tip review context.
- Show weak items before generating the next lesson so the snowball story is easy to explain.
- Submit one short Feynman explanation and call out that fallback feedback still works without a live provider.
- Import vocabulary metadata and search it by root/category/tags.
- Export PDF to close the walkthrough with a tangible artifact.

## Screenshots To Capture

- Home / dashboard overview
- Lesson generation panel
- Review result panel
- Progress dashboard
- Chat tutor preview
- Materials / RAG optional workflow
