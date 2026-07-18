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
    assert "chat_conversations" in tables
    assert "chat_messages" in tables


def _create_v143_baseline(db_path):
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
            CREATE TABLE learning_item_srs (
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
            CREATE TABLE learning_item_reviews (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL REFERENCES learning_items(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 5),
                correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
                response_time_ms INTEGER,
                source TEXT NOT NULL
                    CHECK (source IN ('lesson_review', 'srs_review', 'feynman_feedback', 'manual')),
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
            CREATE TABLE micro_lesson_reward_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, lesson_id, reward_type)
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
                "legacy topic",
                "2026-07-10T08:00:00+08:00",
                15,
                '["intro"]',
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
                '{"language":"EN","current_level":"A1","target_level":"A2","completed_lessons":1,"total_exercises":3,"correct_exercises":2,"accuracy_rate":66.7}',
                '{"language":"JP","current_level":"N5","target_level":"N4","completed_lessons":0,"total_exercises":0,"correct_exercises":0,"accuracy_rate":0.0}',
                '{"level":1,"current_xp":5,"next_level_xp":100,"total_xp":5,"avatar_url":"x","title":"Beginner Adventurer","unlocked_skills":[],"achievements":[],"word_cards":[],"streak_days":0,"difficulty_mode":"normal","is_onboarded":true,"error_distribution":{"spelling":0,"grammar":0,"vocabulary":0,"comprehension":0}}',
                "2026-07-10T08:00:00+08:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO learning_items (
                id, user_id, item_type, item_key, language, level, lesson_id,
                content_json, category, tags, created_at, updated_at
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
                "2026-07-10T08:00:00+08:00",
                "2026-07-10T08:00:00+08:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO learning_item_srs (
                item_id, interval_days, ease_factor, repetitions, lapses, due_at, last_reviewed_at, mastery_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("item-1", 1, 2.5, 1, 0, "2026-07-11T08:00:00+08:00", "2026-07-10T08:00:00+08:00", "learning"),
        )
        conn.execute(
            """
            INSERT INTO learning_item_reviews (
                id, item_id, rating, correct, response_time_ms, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("review-1", "item-1", 4, 1, 1200, "manual", "2026-07-10T08:05:00+08:00"),
        )
        conn.execute(
            """
            INSERT INTO micro_lessons (
                lesson_id, user_id, day_index, lesson_json, completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "micro-1",
                "default_user",
                1,
                '{"sentence":"Hello world"}',
                1,
                "2026-07-10T09:00:00+08:00",
                "2026-07-10T09:30:00+08:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO micro_lesson_reward_events (user_id, lesson_id, reward_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            ("default_user", "micro-1", "xp", "2026-07-10T09:30:00+08:00"),
        )
    finally:
        conn.close()


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
    assert "chat_conversations" in tables
    assert "chat_messages" in tables
    assert indexes
    assert "0007_micro_lesson_reward_events.sql" in versions
    assert "0008_chat_conversations_and_messages.sql" in versions

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


def test_upgrade_from_v143_adds_persisted_chat_without_changing_existing_data(tmp_path):
    db_path = tmp_path / "legacy-v143.db"
    _create_v143_baseline(db_path)

    db = Database(str(db_path))

    with db.get_connection() as conn:
        lesson = conn.execute("SELECT topic, file_path FROM lessons WHERE lesson_id = ?", ("legacy-lesson",)).fetchone()
        progress = conn.execute("SELECT english_progress, japanese_progress FROM progress WHERE user_id = ?", ("default_user",)).fetchone()
        review = conn.execute(
            "SELECT item_id, rating, source FROM learning_item_reviews WHERE id = ?",
            ("review-1",),
        ).fetchone()
        micro_lesson = conn.execute(
            "SELECT day_index, completed FROM micro_lessons WHERE lesson_id = ?",
            ("micro-1",),
        ).fetchone()
        reward = conn.execute(
            "SELECT reward_type FROM micro_lesson_reward_events WHERE lesson_id = ?",
            ("micro-1",),
        ).fetchone()
        chat_tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('chat_conversations', 'chat_messages')"
            ).fetchall()
        }
        version = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            ("0008_chat_conversations_and_messages.sql",),
        ).fetchone()

    assert lesson is not None
    assert lesson["topic"] == "legacy topic"
    assert lesson["file_path"] == "legacy.json"
    assert progress is not None
    assert '"completed_lessons":1' in progress["english_progress"]
    assert '"current_level":"N5"' in progress["japanese_progress"]
    assert review is not None
    assert review["item_id"] == "item-1"
    assert int(review["rating"]) == 4
    assert review["source"] == "manual"
    assert micro_lesson is not None
    assert int(micro_lesson["day_index"]) == 1
    assert int(micro_lesson["completed"]) == 1
    assert reward is not None
    assert reward["reward_type"] == "xp"
    assert chat_tables == {"chat_conversations", "chat_messages"}
    assert version is not None
