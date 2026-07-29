PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS learning_goals (
    user_id TEXT NOT NULL,
    language TEXT NOT NULL
        CHECK (language IN ('EN', 'JP')),
    daily_minutes INTEGER NOT NULL
        CHECK (daily_minutes > 0 AND daily_minutes <= 480),
    weekly_sessions INTEGER NOT NULL
        CHECK (weekly_sessions > 0 AND weekly_sessions <= 28),
    weekly_minutes INTEGER NULL
        CHECK (weekly_minutes IS NULL OR (weekly_minutes > 0 AND weekly_minutes <= 3360)),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, language)
);
