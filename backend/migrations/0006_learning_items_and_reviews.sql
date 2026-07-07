CREATE TABLE IF NOT EXISTS learning_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('vocabulary', 'grammar', 'sentence_pattern')),
    item_key TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT,
    lesson_id TEXT,
    content_json TEXT NOT NULL,
    category TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, item_type, item_key, language)
);

CREATE TABLE IF NOT EXISTS learning_item_srs (
    item_id TEXT PRIMARY KEY REFERENCES learning_items(id) ON DELETE CASCADE,
    interval_days INTEGER NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    repetitions INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    due_at TEXT NOT NULL,
    last_reviewed_at TEXT,
    mastery_state TEXT NOT NULL DEFAULT 'new'
        CHECK (mastery_state IN ('new', 'learning', 'review', 'weak', 'mastered'))
);

CREATE TABLE IF NOT EXISTS learning_item_reviews (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES learning_items(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 5),
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    response_time_ms INTEGER,
    source TEXT NOT NULL
        CHECK (source IN ('lesson_review', 'srs_review', 'feynman_feedback', 'manual')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feynman_feedback_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    explanation TEXT NOT NULL,
    feedback_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_items_lookup
    ON learning_items(user_id, language, item_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_learning_item_srs_due
    ON learning_item_srs(due_at, mastery_state);

CREATE INDEX IF NOT EXISTS idx_learning_item_reviews_item_created
    ON learning_item_reviews(item_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_feynman_feedback_history_lesson
    ON feynman_feedback_history(user_id, lesson_id, created_at DESC);
