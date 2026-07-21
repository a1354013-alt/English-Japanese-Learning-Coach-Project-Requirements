-- Persist the server-owned scenario identifier for each chat conversation.
-- Existing local/development rows safely default to daily_conversation.
ALTER TABLE chat_conversations
ADD COLUMN scenario_id TEXT NOT NULL DEFAULT 'daily_conversation'
CHECK (scenario_id IN ('daily_conversation', 'travel', 'restaurant', 'workplace'));
