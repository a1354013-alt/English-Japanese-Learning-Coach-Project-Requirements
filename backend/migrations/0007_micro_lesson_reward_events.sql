CREATE TABLE IF NOT EXISTS micro_lesson_reward_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    reward_type TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    UNIQUE(user_id, lesson_id, reward_type)
);
