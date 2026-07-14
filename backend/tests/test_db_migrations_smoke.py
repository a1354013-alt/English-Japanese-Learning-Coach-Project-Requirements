"""DB init/migration smoke test (ensures migrations apply cleanly on a fresh DB)."""

import sqlite3

from database import Database


def test_db_init_and_migrations_smoke(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    # Basic smoke: core tables exist and migrations table populated (at least created).
    with db.get_connection() as conn:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "lessons" in tables
    assert "schema_migrations" in tables
    assert "exercise_results" in tables


def test_micro_lesson_reward_event_migration_is_tracked_and_idempotent(tmp_path):
    db = Database(str(tmp_path / "t.db"))

    with db.get_connection() as conn:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        indexes = {
            r["name"]
            for r in conn.execute("PRAGMA index_list(micro_lesson_reward_events)").fetchall()
            if int(r["unique"]) == 1
        }
        versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}

    assert "micro_lesson_reward_events" in tables
    assert indexes
    assert "0007_micro_lesson_reward_events.sql" in versions

    db.run_migrations()
    with db.get_connection() as conn:
        after_rerun = {
            r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
    assert after_rerun == versions


def test_existing_database_upgrades_micro_lesson_reward_events_without_data_loss(tmp_path):
    db_path = tmp_path / "existing.db"
    legacy = sqlite3.connect(str(db_path), isolation_level=None)
    legacy.execute(
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
    legacy.execute(
        """
        INSERT INTO lessons (
            lesson_id, user_id, language, level, topic, generated_at,
            estimated_duration_minutes, key_points, file_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("legacy-lesson", "default_user", "en", "A1", "legacy", "2026-07-10T08:00:00+08:00", 5, "[]", "legacy.json"),
    )
    legacy.close()

    db = Database(str(db_path))

    with db.get_connection() as conn:
        lesson = conn.execute("SELECT * FROM lessons WHERE lesson_id = ?", ("legacy-lesson",)).fetchone()
        reward_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='micro_lesson_reward_events'"
        ).fetchone()
        version = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            ("0007_micro_lesson_reward_events.sql",),
        ).fetchone()

    assert lesson is not None
    assert lesson["topic"] == "legacy"
    assert reward_table is not None
    assert version is not None
