-- 0003: Ensure exercise_results is idempotent per (user_id, lesson_id, exercise_type)
-- Prevents repeated review submissions from creating duplicate rows and inflating analytics.
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_results_unique
ON exercise_results(user_id, lesson_id, exercise_type);

