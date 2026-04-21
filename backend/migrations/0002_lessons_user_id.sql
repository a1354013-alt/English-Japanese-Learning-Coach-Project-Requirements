-- 0002: Add user_id to lessons table for proper scoping (single-user demo compatible)
-- Backfills existing lessons with default_user_id for fallback compatibility

ALTER TABLE lessons ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default_user';

CREATE INDEX IF NOT EXISTS idx_lessons_user ON lessons(user_id);
CREATE INDEX IF NOT EXISTS idx_lessons_user_date ON lessons(user_id, generated_at DESC);

-- Update any existing lessons without user_id to use default_user
UPDATE lessons SET user_id = 'default_user' WHERE user_id IS NULL;
