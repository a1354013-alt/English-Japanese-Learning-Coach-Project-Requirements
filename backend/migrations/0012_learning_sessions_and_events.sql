PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS learning_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    language TEXT NOT NULL
        CHECK (language IN ('EN', 'JP')),
    status TEXT NOT NULL
        CHECK (status IN ('active', 'completed', 'abandoned')),
    planned_minutes INTEGER NULL
        CHECK (planned_minutes IS NULL OR (planned_minutes > 0 AND planned_minutes <= 480)),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP NULL,
    duration_seconds INTEGER NULL
        CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    completion_idempotency_key TEXT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CHECK (
        (status = 'active' AND ended_at IS NULL)
        OR (status IN ('completed', 'abandoned') AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_sessions_active_user_language
ON learning_sessions(user_id, language)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_learning_sessions_user_language_history
ON learning_sessions(user_id, language, started_at DESC, session_id DESC);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_recent
ON learning_sessions(started_at DESC, session_id DESC);

CREATE TABLE IF NOT EXISTS learning_session_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES learning_sessions(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'lesson_started',
                'lesson_completed',
                'review_answered',
                'srs_reviewed',
                'chat_turn_completed',
                'feynman_completed',
                'micro_lesson_completed',
                'session_note'
            )
        ),
    entity_type TEXT NULL
        CHECK (
            entity_type IS NULL
            OR entity_type IN (
                'lesson',
                'review',
                'srs_item',
                'conversation',
                'feynman_response',
                'micro_lesson'
            )
        ),
    entity_id TEXT NULL,
    sequence_number INTEGER NOT NULL
        CHECK (sequence_number > 0),
    idempotency_key TEXT NULL,
    metadata_json TEXT NULL
        CHECK (
            metadata_json IS NULL
            OR (
                length(metadata_json) <= 1000
                AND json_valid(metadata_json)
                AND json_type(metadata_json) = 'object'
            )
        ),
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CHECK ((entity_type IS NULL AND entity_id IS NULL) OR (entity_type IS NOT NULL AND entity_id IS NOT NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_session_events_session_sequence
ON learning_session_events(session_id, sequence_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_session_events_session_idempotency
ON learning_session_events(session_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_learning_session_events_session_occurred
ON learning_session_events(session_id, occurred_at ASC, sequence_number ASC);

CREATE TRIGGER IF NOT EXISTS trg_learning_session_events_require_active_session
BEFORE INSERT ON learning_session_events
FOR EACH ROW
BEGIN
    SELECT
        CASE
            WHEN NOT EXISTS (
                SELECT 1
                FROM learning_sessions
                WHERE session_id = NEW.session_id
                  AND status = 'active'
            ) THEN RAISE(ABORT, 'learning session events may only be appended to an active session')
        END;
END;
