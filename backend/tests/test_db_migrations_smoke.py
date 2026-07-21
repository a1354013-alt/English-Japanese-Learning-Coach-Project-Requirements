"""DB init/migration smoke test (ensures migrations apply cleanly on a fresh DB)."""

import re
import sqlite3

import pytest
from database import CHAT_SUMMARY_CANONICAL_TRIGGER_SQL, Database


def _normalize_sql(sql: str) -> str:
    normalized = re.sub(r"\bIF\s+NOT\s+EXISTS\b", "", sql, flags=re.IGNORECASE)
    normalized = re.sub(r";+\s*$", "", normalized.strip())
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower()


def _trigger_sql(conn, name: str) -> str:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?", (name,)).fetchone()
    assert row is not None
    return str(row["sql"])


def _assert_canonical_summary_triggers(conn) -> None:
    for name, expected in CHAT_SUMMARY_CANONICAL_TRIGGER_SQL.items():
        assert _normalize_sql(_trigger_sql(conn, name)) == _normalize_sql(expected)


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
    with db.get_connection() as conn:
        chat_columns = {r["name"] for r in conn.execute("PRAGMA table_info(chat_conversations)").fetchall()}
    assert "summary_through_sequence" in chat_columns
    assert "summary_updated_at" in chat_columns
    with db.get_connection() as conn:
        versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
        _assert_canonical_summary_triggers(conn)
    assert "0010_chat_summary_trigger_canonicalization.sql" in versions


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


def _create_partial_0009_state(
    db_path,
    *,
    include_summary_through_sequence: bool,
    include_summary_updated_at: bool,
    include_insert_trigger: bool,
    include_update_trigger: bool,
) -> None:
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        summary_through_sequence_sql = (
            ", summary_through_sequence INTEGER NOT NULL DEFAULT 0 CHECK (summary_through_sequence >= 0)"
            if include_summary_through_sequence
            else ""
        )
        summary_updated_at_sql = ", summary_updated_at TIMESTAMP NULL" if include_summary_updated_at else ""
        conn.executescript(
            f"""
            PRAGMA foreign_keys=ON;
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE chat_conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                language TEXT NOT NULL,
                title TEXT NOT NULL,
                lesson_id TEXT NULL,
                summary TEXT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                last_message_at TIMESTAMP NULL
                {summary_through_sequence_sql}
                {summary_updated_at_sql}
            );
            CREATE TABLE chat_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                metadata_json TEXT NULL,
                idempotency_key TEXT NULL,
                created_at TIMESTAMP NOT NULL
            );
            CREATE UNIQUE INDEX idx_chat_messages_conversation_sequence
            ON chat_messages(conversation_id, sequence_number);
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
        ):
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

        insert_columns = [
            "conversation_id",
            "user_id",
            "language",
            "title",
            "lesson_id",
            "summary",
            "created_at",
            "updated_at",
            "last_message_at",
        ]
        insert_values = [
            "conv-1",
            "default_user",
            "EN",
            "Recovered",
            None,
            "summary",
            "2026-07-19T09:00:00+08:00",
            "2026-07-19T09:00:00+08:00",
            "2026-07-19T09:01:00+08:00",
        ]
        if include_summary_through_sequence:
            insert_columns.append("summary_through_sequence")
            insert_values.append(1)
        if include_summary_updated_at:
            insert_columns.append("summary_updated_at")
            insert_values.append("2026-07-19T09:01:00+08:00")
        placeholders = ", ".join("?" for _ in insert_columns)
        conn.execute(
            f"INSERT INTO chat_conversations ({', '.join(insert_columns)}) VALUES ({placeholders})",
            insert_values,
        )
        conn.execute(
            """
            INSERT INTO chat_messages (
                message_id, conversation_id, role, content, sequence_number,
                metadata_json, idempotency_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("msg-1", "conv-1", "user", "hello", 1, None, "key-1", "2026-07-19T09:01:00+08:00"),
        )

        if include_insert_trigger and include_summary_through_sequence and include_summary_updated_at:
            conn.executescript(
                """
                CREATE TRIGGER trg_chat_conversations_summary_checkpoint_insert
                BEFORE INSERT ON chat_conversations
                FOR EACH ROW
                BEGIN
                    SELECT
                        CASE
                            WHEN NEW.summary_through_sequence < 0 THEN
                                RAISE(ABORT, 'chat summary checkpoint must be >= 0')
                        END;
                END;
                """
            )
        if include_update_trigger and include_summary_through_sequence and include_summary_updated_at:
            conn.executescript(
                """
                CREATE TRIGGER trg_chat_conversations_summary_checkpoint_update
                BEFORE UPDATE OF summary, summary_through_sequence, summary_updated_at ON chat_conversations
                FOR EACH ROW
                BEGIN
                    SELECT
                        CASE
                            WHEN NEW.summary_through_sequence < 0 THEN
                                RAISE(ABORT, 'chat summary checkpoint must be >= 0')
                        END;
                END;
                """
            )
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", ("0009_chat_summary_checkpoint.sql",))
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
    assert "0009_chat_summary_checkpoint.sql" in versions

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
        version_0009 = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            ("0009_chat_summary_checkpoint.sql",),
        ).fetchone()
        chat_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(chat_conversations)").fetchall()
        }

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
    assert version_0009 is not None
    assert "summary_through_sequence" in chat_columns
    assert "summary_updated_at" in chat_columns
    with db.get_connection() as conn:
        version_0010 = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            ("0010_chat_summary_trigger_canonicalization.sql",),
        ).fetchone()
        _assert_canonical_summary_triggers(conn)
    assert version_0010 is not None


@pytest.mark.parametrize(
    (
        "include_summary_through_sequence",
        "include_summary_updated_at",
        "include_insert_trigger",
        "include_update_trigger",
    ),
    (
        (False, False, False, False),
        (True, False, False, False),
        (False, True, False, False),
        (True, True, False, False),
        (True, True, True, False),
        (True, True, False, True),
    ),
)
def test_partial_0009_startup_recovery_is_idempotent_and_preserves_chat_data(
    tmp_path,
    include_summary_through_sequence,
    include_summary_updated_at,
    include_insert_trigger,
    include_update_trigger,
):
    db_path = tmp_path / "partial-0009.db"
    _create_partial_0009_state(
        db_path,
        include_summary_through_sequence=include_summary_through_sequence,
        include_summary_updated_at=include_summary_updated_at,
        include_insert_trigger=include_insert_trigger,
        include_update_trigger=include_update_trigger,
    )

    db = Database(str(db_path))
    db.run_migrations()

    with db.get_connection() as conn:
        chat_columns = {row["name"] for row in conn.execute("PRAGMA table_info(chat_conversations)").fetchall()}
        versions = {
            row["version"]
            for row in conn.execute(
                "SELECT version FROM schema_migrations WHERE version IN (?, ?)",
                ("0009_chat_summary_checkpoint.sql", "0010_chat_summary_trigger_canonicalization.sql"),
            ).fetchall()
        }
        triggers = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_chat_conversations_summary_checkpoint_%'"
            ).fetchall()
        }
        conversation = conn.execute(
            """
            SELECT conversation_id, title, summary, summary_through_sequence, summary_updated_at
            FROM chat_conversations
            WHERE conversation_id = ?
            """,
            ("conv-1",),
        ).fetchone()
        message = conn.execute(
            """
            SELECT message_id, conversation_id, sequence_number, content
            FROM chat_messages
            WHERE message_id = ?
            """,
            ("msg-1",),
        ).fetchone()

    assert chat_columns.issuperset({"summary_through_sequence", "summary_updated_at"})
    assert versions == {"0009_chat_summary_checkpoint.sql", "0010_chat_summary_trigger_canonicalization.sql"}
    assert triggers == {
        "trg_chat_conversations_summary_checkpoint_insert",
        "trg_chat_conversations_summary_checkpoint_update",
    }
    assert conversation is not None
    assert conversation["conversation_id"] == "conv-1"
    assert conversation["title"] == "Recovered"
    assert conversation["summary"] == "summary"
    expected_checkpoint = 1 if include_summary_through_sequence else 0
    assert int(conversation["summary_through_sequence"]) == expected_checkpoint
    assert message is not None
    assert message["conversation_id"] == "conv-1"
    assert int(message["sequence_number"]) == 1
    assert message["content"] == "hello"
    with db.get_connection() as conn:
        _assert_canonical_summary_triggers(conn)


def test_0010_canonicalizes_previous_phase_2a_triggers_and_preserves_data(tmp_path):
    db_path = tmp_path / "phase-2a.db"
    _create_partial_0009_state(
        db_path,
        include_summary_through_sequence=True,
        include_summary_updated_at=True,
        include_insert_trigger=True,
        include_update_trigger=True,
    )

    db = Database(str(db_path))

    with db.get_connection() as conn:
        versions = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
        _assert_canonical_summary_triggers(conn)
        conversation = conn.execute(
            """
            SELECT conversation_id, title, summary, summary_through_sequence, summary_updated_at
            FROM chat_conversations
            WHERE conversation_id = ?
            """,
            ("conv-1",),
        ).fetchone()
        message = conn.execute("SELECT content FROM chat_messages WHERE message_id = ?", ("msg-1",)).fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                UPDATE chat_conversations
                SET summary = ?, summary_through_sequence = ?, summary_updated_at = ?
                WHERE conversation_id = ?
                """,
                ("older summary", 0, "2026-07-19T09:02:00+08:00", "conv-1"),
            )

    assert "0009_chat_summary_checkpoint.sql" in versions
    assert "0010_chat_summary_trigger_canonicalization.sql" in versions
    assert conversation is not None
    assert conversation["title"] == "Recovered"
    assert conversation["summary"] == "summary"
    assert int(conversation["summary_through_sequence"]) == 1
    assert message is not None
    assert message["content"] == "hello"

    updated = db.chat_repository.update_conversation_summary(
        conversation_id="conv-1",
        user_id="default_user",
        summary="new summary",
        summary_through_sequence=1,
    )
    assert updated.summary == "new summary"

    before = {
        row["name"]: row["sql"]
        for row in db.get_connection().execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_chat_conversations_summary_checkpoint_%'"
        ).fetchall()
    }
    db.run_migrations()
    after = {
        row["name"]: row["sql"]
        for row in db.get_connection().execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_chat_conversations_summary_checkpoint_%'"
        ).fetchall()
    }
    assert after == before


def test_startup_rebuilds_malformed_summary_trigger_body(tmp_path):
    db_path = tmp_path / "malformed.db"
    _create_partial_0009_state(
        db_path,
        include_summary_through_sequence=True,
        include_summary_updated_at=True,
        include_insert_trigger=True,
        include_update_trigger=True,
    )
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        conn.execute("DROP TRIGGER trg_chat_conversations_summary_checkpoint_update")
        conn.executescript(
            """
            CREATE TRIGGER trg_chat_conversations_summary_checkpoint_update
            BEFORE UPDATE OF summary, summary_through_sequence, summary_updated_at ON chat_conversations
            FOR EACH ROW
            BEGIN
                SELECT CASE WHEN NEW.summary_through_sequence < 0 THEN RAISE(ABORT, 'old') END;
            END;
            """
        )
    finally:
        conn.close()

    db = Database(str(db_path))

    with db.get_connection() as upgraded:
        _assert_canonical_summary_triggers(upgraded)
