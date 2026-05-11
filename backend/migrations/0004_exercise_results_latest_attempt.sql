-- 0004: Keep best score and latest attempt in the idempotent exercise result row.
ALTER TABLE exercise_results ADD COLUMN latest_correct_count INTEGER;
ALTER TABLE exercise_results ADD COLUMN latest_accuracy_rate REAL;
