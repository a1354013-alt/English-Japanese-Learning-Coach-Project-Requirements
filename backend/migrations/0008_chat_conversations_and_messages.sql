CREATE TABLE IF NOT EXISTS chat_conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('EN', 'JP')),
    title TEXT NOT NULL,
    lesson_id TEXT NULL,
    summary TEXT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_message_at TIMESTAMP NULL,
    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_language_last_message
ON chat_conversations(user_id, language, COALESCE(last_message_at, updated_at) DESC, created_at DESC, conversation_id DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    metadata_json TEXT NULL,
    idempotency_key TEXT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_messages_conversation_sequence
ON chat_messages(conversation_id, sequence_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_messages_conversation_idempotency
ON chat_messages(conversation_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_created
ON chat_messages(conversation_id, created_at ASC, sequence_number ASC);
