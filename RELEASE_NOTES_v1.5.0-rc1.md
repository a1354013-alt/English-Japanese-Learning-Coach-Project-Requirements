# Release Notes: v1.5.0-rc1

`v1.5.0-rc1` is the first release candidate for persisted learner conversations.

## Highlights

- Chat Tutor now exposes persisted conversations in the learner UI with create, select, rename, delete, reload restore, and EN/JP isolation flows.
- WebSocket chat turns now emit canonical `conversation.ready`, `chat.user.persisted`, and `chat.assistant.persisted` events so optimistic frontend rows reconcile to persisted message IDs without duplication.
- Persisted scenarios now remain stable across reconnects and reloads for Daily Conversation, Travel, Restaurant, and Workplace chats.
- Browser coverage now includes a deterministic mocked persisted-chat flow plus a full-stack persisted-chat flow with `CHAT_PROVIDER_MODE=mock`, so ordinary frontend validation does not require live Ollama.

## Migrations

- `0008`: persisted conversations and messages
- `0009`: summary checkpoint columns and validation
- `0010`: canonical summary trigger recovery
- `0011`: persisted conversation scenarios

## Known limitations

- Local single-user demonstration scope only
- Local single-process turn serialization only
- No automatic rolling-summary generation
- TTS provider disabled by default
- No microphone recording
- No pronunciation scoring
