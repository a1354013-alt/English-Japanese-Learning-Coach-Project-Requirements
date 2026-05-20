# Demo Guide

Use this guide when you want to present the project as a polished portfolio demo instead of only a developer handoff.

## Recommended Demo Flow

1. Start the backend with `ALLOW_DEMO_RESET=true` for local demo use.
2. Call `POST /api/demo/reset` once to rebuild the deterministic demo dataset.
3. Open the frontend and walk through:
   - Today lesson overview
   - Lesson generation or seeded lesson review
   - Progress update
   - Wrong answers / SRS review
   - Workspace materials and optional RAG state
   - Writing center
   - Chat tutor preview

## Demo Notes

- `GET /api/health` is a lightweight liveness check for app + DB only.
- `GET /api/ready` reports optional dependency state such as Ollama / RAG.
- RAG is optional. A demo can succeed with `ENABLE_RAG=false`.
- Demo reset is intentionally protected and should stay disabled outside local demo environments.

## Suggested Presenter Script

- Start on Today to show the dashboard-style lesson summary.
- Submit one review to demonstrate progress, streak, and wrong-answer persistence.
- Open Progress to show stats and history updating from the same backend source of truth.
- Open Workspace to explain optional materials/RAG and the chat tutor preview.

## Screenshots To Capture

- Home / dashboard overview
- Lesson generation panel
- Review result panel
- Progress dashboard
- Chat tutor preview
- Materials / RAG optional workflow
