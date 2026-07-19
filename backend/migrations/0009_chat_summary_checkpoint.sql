ALTER TABLE chat_conversations
ADD COLUMN summary_through_sequence INTEGER NOT NULL DEFAULT 0 CHECK (summary_through_sequence >= 0);

ALTER TABLE chat_conversations
ADD COLUMN summary_updated_at TIMESTAMP NULL;

CREATE TRIGGER IF NOT EXISTS trg_chat_conversations_summary_checkpoint_insert
BEFORE INSERT ON chat_conversations
FOR EACH ROW
BEGIN
    SELECT
        CASE
            WHEN NEW.summary_through_sequence < 0 THEN
                RAISE(ABORT, 'chat summary checkpoint must be >= 0')
            WHEN NEW.summary IS NULL AND NEW.summary_through_sequence <> 0 THEN
                RAISE(ABORT, 'chat summary checkpoint must be 0 when summary is null')
            WHEN NEW.summary IS NULL AND NEW.summary_updated_at IS NOT NULL THEN
                RAISE(ABORT, 'chat summary_updated_at must be null when summary is null')
            WHEN NEW.summary_through_sequence > COALESCE(
                (SELECT MAX(sequence_number) FROM chat_messages WHERE conversation_id = NEW.conversation_id),
                0
            ) THEN
                RAISE(ABORT, 'chat summary checkpoint exceeds message sequence')
        END;
END;

CREATE TRIGGER IF NOT EXISTS trg_chat_conversations_summary_checkpoint_update
BEFORE UPDATE OF summary, summary_through_sequence, summary_updated_at ON chat_conversations
FOR EACH ROW
BEGIN
    SELECT
        CASE
            WHEN NEW.summary_through_sequence < 0 THEN
                RAISE(ABORT, 'chat summary checkpoint must be >= 0')
            WHEN NEW.summary IS NULL AND NEW.summary_through_sequence <> 0 THEN
                RAISE(ABORT, 'chat summary checkpoint must be 0 when summary is null')
            WHEN NEW.summary IS NULL AND NEW.summary_updated_at IS NOT NULL THEN
                RAISE(ABORT, 'chat summary_updated_at must be null when summary is null')
            WHEN NEW.summary_through_sequence > COALESCE(
                (SELECT MAX(sequence_number) FROM chat_messages WHERE conversation_id = NEW.conversation_id),
                0
            ) THEN
                RAISE(ABORT, 'chat summary checkpoint exceeds message sequence')
        END;
END;
