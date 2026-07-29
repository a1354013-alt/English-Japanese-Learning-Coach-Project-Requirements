PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS review_submissions (
    submission_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    client_submission_id TEXT NULL,
    request_hash TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    accuracy_rate REAL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_submissions_client_id
ON review_submissions(user_id, client_submission_id)
WHERE client_submission_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_review_submissions_lesson_created
ON review_submissions(user_id, lesson_id, created_at DESC);

CREATE TABLE IF NOT EXISTS legacy_srs_review_operations (
    operation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    word TEXT NOT NULL,
    language TEXT NOT NULL
        CHECK (language IN ('EN', 'JP')),
    client_operation_id TEXT NULL,
    request_hash TEXT NOT NULL,
    quality INTEGER NOT NULL
        CHECK (quality >= 0 AND quality <= 5),
    created_at TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_legacy_srs_review_operations_client_id
ON legacy_srs_review_operations(user_id, client_operation_id)
WHERE client_operation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_legacy_srs_review_operations_word_created
ON legacy_srs_review_operations(user_id, language, word, created_at DESC);
