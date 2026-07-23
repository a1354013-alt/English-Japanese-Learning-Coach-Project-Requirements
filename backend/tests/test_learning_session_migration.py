import sqlite3

from database import Database


def _create_v150_schema(db_path) -> None:
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        conn.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
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
            );
            CREATE TABLE progress (
                user_id TEXT PRIMARY KEY,
                english_progress TEXT NOT NULL,
                japanese_progress TEXT NOT NULL,
                rpg_stats TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE learning_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
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
            CREATE TABLE learning_item_reviews (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL REFERENCES learning_items(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL,
                correct INTEGER NOT NULL,
                response_time_ms INTEGER,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE micro_lessons (
                lesson_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                day_index INTEGER NOT NULL,
                lesson_json TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, day_index)
            );
            CREATE TABLE chat_conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                language TEXT NOT NULL,
                scenario_id TEXT NOT NULL DEFAULT 'daily_conversation',
                title TEXT NOT NULL,
                lesson_id TEXT NULL,
                summary TEXT NULL,
                summary_through_sequence INTEGER NOT NULL DEFAULT 0,
                summary_updated_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                last_message_at TIMESTAMP NULL
            );
            CREATE TABLE chat_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                idempotency_key TEXT NULL,
                metadata_json TEXT NULL,
                created_at TIMESTAMP NOT NULL
            );
            """
        )
        for version in (
            "0001_wrong_answers_and_learning_activity.sql",
            "0002_lessons_user_id.sql",
            "0003_exercise_results_unique.sql",
            "0004_exercise_results_latest_attempt.sql",
            "0005_vocabulary_categories_and_roots.sql",
            "0006_learning_items_and_reviews.sql",
            "0007_micro_lesson_reward_events.sql",
            "0008_chat_conversations_and_messages.sql",
            "0009_chat_summary_checkpoint.sql",
            "0010_chat_summary_trigger_canonicalization.sql",
            "0011_chat_conversation_scenario.sql",
        ):
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        conn.execute(
            """
            INSERT INTO lessons (
                lesson_id, user_id, language, level, topic, generated_at,
                estimated_duration_minutes, key_points, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-lesson",
                "default_user",
                "EN",
                "A1",
                "legacy",
                "2026-07-21T09:00:00+08:00",
                15,
                "[]",
                "legacy.json",
            ),
        )
        conn.execute(
            """
            INSERT INTO progress (user_id, english_progress, japanese_progress, rpg_stats, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "default_user",
                '{"language":"EN"}',
                '{"language":"JP"}',
                '{"level":1}',
                "2026-07-21T09:00:00+08:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO learning_items (
                id, user_id, item_type, item_key, language, level, lesson_id, content_json, category, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "item-1",
                "default_user",
                "vocabulary",
                "hello",
                "EN",
                "A1",
                "legacy-lesson",
                '{"word":"hello"}',
                "greeting",
                '["intro"]',
                "2026-07-21T09:00:00+08:00",
                "2026-07-21T09:00:00+08:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO learning_item_reviews (
                id, item_id, rating, correct, response_time_ms, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("review-1", "item-1", 4, 1, 1100, "manual", "2026-07-21T09:05:00+08:00"),
        )
        conn.execute(
            """
            INSERT INTO micro_lessons (
                lesson_id, user_id, day_index, lesson_json, completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("micro-1", "default_user", 1, '{"sentence":"hi"}', 1, "2026-07-21T10:00:00+08:00", "2026-07-21T10:30:00+08:00"),
        )
        conn.execute(
            """
            INSERT INTO chat_conversations (
                conversation_id, user_id, language, scenario_id, title, lesson_id, summary,
                summary_through_sequence, summary_updated_at, created_at, updated_at, last_message_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "conv-1",
                "default_user",
                "EN",
                "daily_conversation",
                "Legacy chat",
                None,
                None,
                0,
                None,
                "2026-07-21T11:00:00+08:00",
                "2026-07-21T11:00:00+08:00",
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (
                message_id, conversation_id, user_id, role, content, sequence_number, idempotency_key, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "msg-1",
                "conv-1",
                "default_user",
                "user",
                "hello",
                1,
                "msg-1",
                None,
                "2026-07-21T11:01:00+08:00",
            ),
        )
    finally:
        conn.close()


def test_learning_session_migration_applies_on_fresh_database(tmp_path):
    db = Database(str(tmp_path / "fresh.db"))

    with db.get_connection() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        versions = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
        session_columns = {
            row["name"]: row["type"] for row in conn.execute("PRAGMA table_info(learning_sessions)")
        }
        event_columns = {
            row["name"]: row["type"] for row in conn.execute("PRAGMA table_info(learning_session_events)")
        }

    assert "learning_sessions" in tables
    assert "learning_session_events" in tables
    assert "review_submissions" in tables
    assert "legacy_srs_review_operations" in tables
    assert "0012_learning_sessions_and_events.sql" in versions
    assert "0013_review_and_srs_operation_ids.sql" in versions
    assert "completion_idempotency_key" in session_columns
    assert "metadata_json" in event_columns


def test_learning_session_migration_upgrades_v150_without_data_loss(tmp_path):
    db_path = tmp_path / "upgrade.db"
    _create_v150_schema(db_path)

    db = Database(str(db_path))
    db.run_migrations()

    with db.get_connection() as conn:
        versions = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
        lesson = conn.execute("SELECT lesson_id, topic FROM lessons WHERE lesson_id = 'legacy-lesson'").fetchone()
        progress = conn.execute("SELECT user_id FROM progress WHERE user_id = 'default_user'").fetchone()
        review = conn.execute("SELECT id FROM learning_item_reviews WHERE id = 'review-1'").fetchone()
        micro = conn.execute("SELECT lesson_id FROM micro_lessons WHERE lesson_id = 'micro-1'").fetchone()
        chat_message = conn.execute("SELECT message_id FROM chat_messages WHERE message_id = 'msg-1'").fetchone()

    assert "0012_learning_sessions_and_events.sql" in versions
    assert "0013_review_and_srs_operation_ids.sql" in versions
    assert lesson["topic"] == "legacy"
    assert progress["user_id"] == "default_user"
    assert review["id"] == "review-1"
    assert micro["lesson_id"] == "micro-1"
    assert chat_message["message_id"] == "msg-1"


def test_learning_session_migration_is_safe_on_repeated_startup(tmp_path):
    db_path = tmp_path / "repeat.db"
    db = Database(str(db_path))
    db.run_migrations()
    db.run_migrations()

    reopened = Database(str(db_path))

    with reopened.get_connection() as conn:
        versions = [row["version"] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
        session_indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'learning_sessions'"
            )
        }

    assert versions.count("0012_learning_sessions_and_events.sql") == 1
    assert versions.count("0013_review_and_srs_operation_ids.sql") == 1
    assert "idx_learning_sessions_active_user_language" in session_indexes
