ALTER TABLE chat_conversations ADD COLUMN scenario_id TEXT NOT NULL DEFAULT 'daily-conversation';

UPDATE chat_conversations
SET scenario_id = 'daily-conversation'
WHERE scenario_id IS NULL OR TRIM(scenario_id) = '';

CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_language_scenario
ON chat_conversations(user_id, language, scenario_id, created_at DESC);
