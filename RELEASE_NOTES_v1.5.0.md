# Release Notes: v1.5.0

`v1.5.0` is the final persisted-chat release.

## Highlights

- Chat Tutor now exposes persisted conversations in the learner UI with create, select, rename, delete, reload restore, and EN/JP isolation flows.
- WebSocket chat turns now emit canonical `conversation.ready`, `chat.user.persisted`, `chat.assistant.persisted`, `chat.error`, and `chat.validation_error` events so optimistic frontend rows reconcile to persisted message IDs without duplication.
- Persisted scenarios now remain stable across reconnects and reloads for Daily Conversation, Travel, Restaurant, and Workplace chats.
- Prompt construction now uses bounded persisted context with summary checkpoints plus recent turns, keeping the active user message present while preserving turn ordering.
- Browser coverage now includes a deterministic mocked persisted-chat flow plus full-stack smoke and persisted-chat flows with `CHAT_PROVIDER_MODE=mock`, so standard release validation does not require live Ollama.
- Release verification and packaging remain hardened with dependency lock checks, clean audit gates, secret scanning, nested-archive rejection, extraction/bootstrap smoke, and shell syntax validation.

## Migrations

- `0008`: persisted conversations and messages
- `0009`: summary checkpoint columns and validation
- `0010`: canonical summary trigger recovery
- `0011`: persisted conversation scenarios

## Upgrade notes from v1.4.3

- Upgrade from `v1.4.3` by applying additive migrations `0008` through `0011`; no historical `v1.4.x` migrations are rewritten.
- Existing adaptive-learning lesson, review, SRS, analytics, and export flows remain in place; `v1.5.0` adds persisted-chat storage and runtime continuity on top of that baseline.
- Frontend/runtime release identity is now finalized at `1.5.0` across root metadata, frontend package metadata, release markers, and release-facing documentation.

## Demo workflow

1. Install backend dependencies with `cd backend && python -m pip install -r requirements-dev.lock.txt`.
2. Install frontend dependencies with `cd frontend && npm ci`.
3. Copy `backend/.env.example` to `backend/.env`.
4. Start the app with the documented VS Code F5 flow or run the backend/frontend locally.
5. For local demos, set `ALLOW_DEMO_RESET=true` and call `POST /api/demo/reset` before presenting.
6. Walk through Today, SRS, Analytics, vocabulary import/search, Wrong Answers, and Chat Tutor persisted conversations.
7. In Chat Tutor, demonstrate create, reload restore, retry-safe reconciliation, EN/JP isolation, rename, delete, and reconnect continuity.

## Known limitations

- Local single-user demonstration scope only
- Local single-process turn serialization only
- No automatic rolling-summary generation
- No production multi-user SaaS auth, authorization, user isolation, rate limiting, or audit logging
- TTS provider disabled by default
- Immersion is text shadowing only
- No microphone recording
- No pronunciation scoring
- Optional RAG still requires separate dependencies and verification

## Required toolchain versions

- Python `3.11.x` for the main release-verification lane
- Python `3.13.x` for the SQLite lifecycle compatibility/warning gate
- Node.js `22.18.0`
- npm `10.9.3`
