-- 0001: Wrong Answer Notebook + Daily Learning Activity (streak source-of-truth)

CREATE TABLE IF NOT EXISTS wrong_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    language TEXT NOT NULL,
    question_type TEXT NOT NULL,
    question TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    source_lesson_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    wrong_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wrong_answers_user_status_updated
ON wrong_answers(user_id, status, updated_at DESC);

-- Dedup strategy: one active row per (user, language, question_type, question, correct_answer, source_lesson_id).
-- On repeated wrong attempts, we update wrong_count + updated_at instead of inserting more rows.
CREATE UNIQUE INDEX IF NOT EXISTS ux_wrong_answers_active_dedupe
ON wrong_answers(user_id, language, question_type, question, correct_answer, IFNULL(source_lesson_id, ''))
WHERE status = 'active';

CREATE TABLE IF NOT EXISTS user_learning_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    activity_date TEXT NOT NULL, -- local date YYYY-MM-DD in configured timezone
    activity_type TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Same day / same activity type only counts once; streak calculation uses distinct dates.
CREATE UNIQUE INDEX IF NOT EXISTS ux_learning_activity_user_date_type
ON user_learning_activity(user_id, activity_date, activity_type);

CREATE INDEX IF NOT EXISTS idx_learning_activity_user_date
ON user_learning_activity(user_id, activity_date DESC);

