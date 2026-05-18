"""Critical lesson indexes should exist even on partially migrated databases."""

import sqlite3

from database import Database


def test_runtime_indexes_backfill_lesson_indexes(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    with db.get_connection() as conn:
        indexes = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
        }
    assert "idx_lessons_user" in indexes
    assert "idx_lessons_user_date" in indexes


def test_runtime_index_backfill_removes_duplicate_exercise_results(tmp_path):
    db_path = tmp_path / "dedupe.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE lessons (
                lesson_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                language TEXT NOT NULL,
                level TEXT NOT NULL,
                topic TEXT NOT NULL,
                generated_at TIMESTAMP NOT NULL,
                estimated_duration_minutes INTEGER,
                key_points TEXT,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE exercise_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                exercise_type TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                accuracy_rate REAL NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO exercise_results (
                user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate, submitted_at
            ) VALUES
                ('default_user', 'lesson-1', 'mixed', 10, 4, 40.0, '2026-05-10T10:00:00'),
                ('default_user', 'lesson-1', 'mixed', 10, 8, 80.0, '2026-05-11T10:00:00')
            """
        )

    db = Database(str(db_path))

    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT correct_count, accuracy_rate
            FROM exercise_results
            WHERE user_id = 'default_user' AND lesson_id = 'lesson-1' AND exercise_type = 'mixed'
            """
        ).fetchall()
        indexes = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
        }

    assert len(rows) == 1
    assert rows[0]["correct_count"] == 8
    assert rows[0]["accuracy_rate"] == 80.0
    assert "idx_exercise_results_unique" in indexes
