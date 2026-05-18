-- 0003: Ensure exercise_results is idempotent per (user_id, lesson_id, exercise_type)
-- Prevents repeated review submissions from creating duplicate rows and inflating analytics.
DELETE FROM exercise_results
WHERE id IN (
    SELECT duplicate_id
    FROM (
        SELECT older.id AS duplicate_id
        FROM exercise_results AS older
        JOIN exercise_results AS newer
          ON newer.user_id = older.user_id
         AND newer.lesson_id = older.lesson_id
         AND newer.exercise_type = older.exercise_type
         AND (
            COALESCE(newer.submitted_at, '') > COALESCE(older.submitted_at, '')
            OR (
                COALESCE(newer.submitted_at, '') = COALESCE(older.submitted_at, '')
                AND newer.id > older.id
            )
         )
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_results_unique
ON exercise_results(user_id, lesson_id, exercise_type);
