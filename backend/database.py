"""Database operations for Language Coach."""
import json
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from zoneinfo import ZoneInfo

from config import settings
from models import UserRPGStats


class Database:
    """SQLite database handler with connection pooling."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.db_path).resolve()
        self._ensure_db_directory()
        self._local = threading.local()
        self.init_database()

    def _ensure_db_directory(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def _connection(self) -> sqlite3.Connection:
        """Get thread-local connection (lazy initialization)."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                isolation_level=None,  # Autocommit mode for better concurrency
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent read/write performance
            conn.execute("PRAGMA journal_mode=WAL")
            # Increase cache size for better performance (2000 pages)
            conn.execute("PRAGMA cache_size=-2000")
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Compatibility wrapper for code paths using context-managed connections."""
        return self._connection

    def check_connection(self) -> bool:
        try:
            conn = self._connection
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def init_database(self) -> None:
        conn = self._connection
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                user_id TEXT PRIMARY KEY,
                english_progress TEXT NOT NULL,
                japanese_progress TEXT NOT NULL,
                rpg_stats TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS generation_tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT,
                status TEXT,
                model_used TEXT,
                duration_ms INTEGER,
                error_message TEXT,
                retry_count INTEGER,
                created_at TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exercise_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                exercise_type TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                accuracy_rate REAL NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, lesson_id, exercise_type),
                FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS srs_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                data TEXT NOT NULL,
                srs_level INTEGER DEFAULT 0,
                ease_factor REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 0,
                next_review TIMESTAMP,
                last_reviewed TIMESTAMP,
                UNIQUE(user_id, word, language)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS imported_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                language TEXT NOT NULL,
                word TEXT NOT NULL,
                reading TEXT,
                definition_zh TEXT NOT NULL,
                example_sentence TEXT,
                example_translation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, language, word)
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_language ON lessons(language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(generated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_srs_due ON srs_vocabulary(next_review)")

        self.run_migrations()

    def run_migrations(self) -> None:
        """Apply SQL migrations from backend/migrations (idempotent, tracked in schema_migrations)."""
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        if not migrations_dir.exists():
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))
        if not migration_files:
            return

        conn = self._connection
        existing = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for file_path in migration_files:
            version = file_path.name
            if version in existing:
                continue

            # Some migrations are "upgrade-only" for older schemas. When creating a brand-new DB,
            # the tables already include the latest columns and re-applying ALTERs would fail.
            if version == "0002_lessons_user_id.sql":
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(lessons)").fetchall()]
                if "user_id" in cols:
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                    continue
            sql = file_path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    def _local_date_str(self, dt: Optional[datetime] = None) -> str:
        tz = ZoneInfo(settings.timezone)
        now = dt.astimezone(tz) if dt else datetime.now(tz)
        return now.date().isoformat()

    def save_lesson(self, lesson_data: Dict[str, Any], file_path: str, user_id: Optional[str] = None) -> str:
        metadata = lesson_data["metadata"]
        uid = user_id or settings.default_user_id
        # Store a portable key instead of an absolute path when possible.
        # Preferred format: "lessons/YYYY-MM-DD/lesson_<id>.json" (POSIX separators).
        p = Path(str(file_path))
        normalized_path: str
        if p.is_absolute():
            try:
                normalized_path = p.resolve().relative_to(settings.data_path).as_posix()
            except Exception:
                # If the file lives outside DATA_DIR, fall back to an absolute path.
                normalized_path = str(p.resolve())
        else:
            normalized_path = p.as_posix()

        conn = self._connection
        conn.execute(
            """
            INSERT INTO lessons (
                lesson_id, user_id, language, level, topic, generated_at,
                estimated_duration_minutes, key_points, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata["lesson_id"],
                uid,
                metadata["language"],
                metadata["level"],
                metadata["topic"],
                metadata["generated_at"],
                metadata.get("estimated_duration_minutes"),
                json.dumps(metadata.get("key_points", []), ensure_ascii=False),
                normalized_path,
            ),
        )
        return metadata["lesson_id"]

    def get_lesson(self, lesson_id: str, *, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        conn = self._connection
        if user_id is None:
            row = conn.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM lessons WHERE lesson_id = ? AND user_id = ?",
                (lesson_id, user_id),
            ).fetchone()
        return dict(row) if row else None

    def query_lessons(
        self,
        user_id: str,
        language: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        level: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        base = "FROM lessons WHERE user_id = ?"
        params: List[Any] = [user_id]

        if language:
            base += " AND language = ?"
            params.append(language)
        if start_date:
            base += " AND DATE(generated_at) >= ?"
            params.append(start_date)
        if end_date:
            base += " AND DATE(generated_at) <= ?"
            params.append(end_date)
        if level:
            base += " AND level = ?"
            params.append(level)
        if topic:
            base += " AND topic LIKE ?"
            params.append(f"%{topic}%")

        conn = self._connection
        count_row = conn.execute(f"SELECT COUNT(1) AS c {base}", params).fetchone()
        total = int(count_row["c"]) if count_row else 0

        rows = conn.execute(
            f"SELECT * {base} ORDER BY generated_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows], total

    def create_default_progress(self, user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "english_progress": {
                "language": "EN",
                "current_level": "A1",
                "target_level": "B2",
                "completed_lessons": 0,
                "total_exercises": 0,
                "correct_exercises": 0,
                "accuracy_rate": 0.0,
                "last_study_date": None,
            },
            "japanese_progress": {
                "language": "JP",
                "current_level": "N5",
                "target_level": "N2",
                "completed_lessons": 0,
                "total_exercises": 0,
                "correct_exercises": 0,
                "accuracy_rate": 0.0,
                "last_study_date": None,
            },
            "rpg_stats": UserRPGStats().model_dump(mode="json"),
            "updated_at": datetime.now().isoformat(),
        }

    def get_progress(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        uid = user_id or settings.default_user_id
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM progress WHERE user_id = ?", (uid,)).fetchone()

        if not row:
            progress = self.create_default_progress(uid)
            self.save_progress(progress)
            return progress

        result = dict(row)
        result["english_progress"] = json.loads(result["english_progress"])
        result["japanese_progress"] = json.loads(result["japanese_progress"])
        result["rpg_stats"] = (
            json.loads(result["rpg_stats"])
            if result.get("rpg_stats")
            else UserRPGStats().model_dump(mode="json")
        )
        return result

    def save_progress(self, progress_data: Dict[str, Any]) -> None:
        user_id = progress_data.get("user_id") or settings.default_user_id
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO progress (user_id, english_progress, japanese_progress, rpg_stats, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    english_progress=excluded.english_progress,
                    japanese_progress=excluded.japanese_progress,
                    rpg_stats=excluded.rpg_stats,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    json.dumps(progress_data["english_progress"], ensure_ascii=False, default=str),
                    json.dumps(progress_data["japanese_progress"], ensure_ascii=False, default=str),
                    json.dumps(progress_data.get("rpg_stats", {}), ensure_ascii=False, default=str),
                    datetime.now().isoformat(),
                ),
            )

    def get_rpg_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        progress = self.get_progress(user_id)
        return progress.get("rpg_stats") or UserRPGStats().model_dump(mode="json")

    def save_rpg_stats(self, user_id: str, rpg_stats: Dict[str, Any]) -> None:
        progress = self.get_progress(user_id)
        progress["rpg_stats"] = rpg_stats
        self.save_progress(progress)

    def save_exercise_result(
        self,
        user_id: str,
        lesson_id: str,
        exercise_type: str,
        total_questions: int,
        correct_count: int,
        accuracy_rate: float,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO exercise_results (
                    user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id, exercise_type) DO UPDATE SET
                    total_questions=excluded.total_questions,
                    correct_count=excluded.correct_count,
                    accuracy_rate=excluded.accuracy_rate,
                    submitted_at=CURRENT_TIMESTAMP
                """,
                (user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate),
            )

    def list_recent_exercise_results(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT lesson_id, exercise_type, total_questions, correct_count, accuracy_rate, submitted_at
                FROM exercise_results
                WHERE user_id = ?
                ORDER BY submitted_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def has_exercise_result(self, user_id: str, lesson_id: str) -> bool:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM exercise_results WHERE user_id = ? AND lesson_id = ? LIMIT 1",
                (user_id, lesson_id),
            ).fetchone()
            return row is not None

    def save_generation_task(self, task_data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO generation_tasks (
                    task_id, user_id, status, model_used, duration_ms, error_message, retry_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    model_used=excluded.model_used,
                    duration_ms=excluded.duration_ms,
                    error_message=excluded.error_message,
                    retry_count=excluded.retry_count
                """,
                (
                    task_data["task_id"],
                    task_data.get("user_id") or settings.default_user_id,
                    task_data.get("status", "pending"),
                    task_data.get("model_used", ""),
                    task_data.get("duration_ms", 0),
                    task_data.get("error_message"),
                    task_data.get("retry_count", 0),
                    task_data.get("created_at", datetime.now().isoformat()),
                ),
            )

    def get_generation_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM generation_tasks
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_today_lesson(self, user_id: str, language: str) -> Optional[Dict[str, Any]]:
        tz = ZoneInfo(settings.timezone)
        today = datetime.now(tz).date().isoformat()
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM lessons
                WHERE user_id = ? AND language = ? AND DATE(generated_at) = ?
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                (user_id, language, today),
            ).fetchone()
            return dict(row) if row else None

    def get_srs_item(self, user_id: str, word: str, language: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM srs_vocabulary
                WHERE user_id = ? AND word = ? AND language = ?
                """,
                (user_id, word, language),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item["data"] = json.loads(item["data"])
            return item

    def update_srs_item(
        self,
        user_id: str,
        word: str,
        language: str,
        srs_data: Dict[str, Any],
        vocab_info: Dict[str, Any],
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO srs_vocabulary (
                    user_id, word, language, data, srs_level, ease_factor, interval, next_review, last_reviewed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word, language) DO UPDATE SET
                    data = excluded.data,
                    srs_level = excluded.srs_level,
                    ease_factor = excluded.ease_factor,
                    interval = excluded.interval,
                    next_review = excluded.next_review,
                    last_reviewed = excluded.last_reviewed
                """,
                (
                    user_id,
                    word,
                    language,
                    json.dumps(vocab_info, ensure_ascii=False),
                    srs_data["repetition"],
                    srs_data["ease_factor"],
                    srs_data["interval"],
                    srs_data["next_review"].isoformat(),
                    datetime.now().isoformat(),
                ),
            )

    def get_due_srs_items(
        self,
        user_id: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM srs_vocabulary WHERE user_id = ? AND next_review <= ?"
        params: List[Any] = [user_id, datetime.now().isoformat()]

        if language:
            query += " AND language = ?"
            params.append(language)

        query += " ORDER BY next_review ASC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item["data"])
            result.append(item)
        return result

    def save_imported_vocabulary(self, user_id: str, language: str, item: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO imported_vocabulary (
                    user_id, language, word, reading, definition_zh, example_sentence, example_translation
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, language, word) DO UPDATE SET
                    reading=excluded.reading,
                    definition_zh=excluded.definition_zh,
                    example_sentence=excluded.example_sentence,
                    example_translation=excluded.example_translation
                """,
                (
                    user_id,
                    language,
                    item["word"],
                    item.get("reading"),
                    item["definition_zh"],
                    item.get("example_sentence", ""),
                    item.get("example_translation", ""),
                ),
            )

    def list_imported_vocabulary(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where = ["user_id = ?"]
        params: List[Any] = [user_id]
        if language:
            where.append("language = ?")
            params.append(language)
        if q:
            where.append("(word LIKE ? OR definition_zh LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])

        where_sql = " AND ".join(where)
        with self.get_connection() as conn:
            count_row = conn.execute(f"SELECT COUNT(1) AS c FROM imported_vocabulary WHERE {where_sql}", params).fetchone()
            rows = conn.execute(
                f"""
                SELECT id, user_id, language, word, reading, definition_zh, example_sentence, example_translation, created_at
                FROM imported_vocabulary
                WHERE {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
            return [dict(r) for r in rows], int(count_row["c"]) if count_row else 0

    def delete_imported_vocabulary(self, *, user_id: str, item_id: int) -> bool:
        """Delete an imported vocabulary item and all derived/related data.

        Consistency contract:
        - Removes the imported_vocabulary row (source record)
        - Removes any derived SRS entry for (user_id, word, language)
        - Removes any collected word cards for the same (word, language) from rpg_stats

        Returns True if the imported_vocabulary row existed and was deleted, otherwise False.
        """
        # Ensure progress row exists so rpg_stats cleanup is always well-defined.
        self.get_progress(user_id)

        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, word, language FROM imported_vocabulary WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            ).fetchone()
            if not row:
                return False

            word = str(row["word"])
            language = str(row["language"])

            # Source record deletion.
            cur = conn.execute(
                "DELETE FROM imported_vocabulary WHERE id = ? AND user_id = ?",
                (item_id, user_id),
            )
            if cur.rowcount <= 0:
                return False

            # Derived SRS cleanup (idempotent).
            conn.execute(
                "DELETE FROM srs_vocabulary WHERE user_id = ? AND word = ? AND language = ?",
                (user_id, word, language),
            )

            # RPG word card cleanup: remove any card entries matching (word, language).
            p = conn.execute("SELECT rpg_stats FROM progress WHERE user_id = ?", (user_id,)).fetchone()
            raw_stats = p["rpg_stats"] if p and "rpg_stats" in p.keys() else None
            if raw_stats:
                try:
                    stats = json.loads(raw_stats)
                except Exception:
                    stats = {}
            else:
                stats = {}

            removed_cards = 0
            cards = stats.get("word_cards")
            if isinstance(cards, list) and cards:
                before = len(cards)
                stats["word_cards"] = [
                    c
                    for c in cards
                    if not (
                        isinstance(c, dict)
                        and str(c.get("word", "")) == word
                        and str(c.get("language", "")) == language
                    )
                ]
                removed_cards = before - len(stats["word_cards"])

            if removed_cards:
                conn.execute(
                    "UPDATE progress SET rpg_stats = ?, updated_at = ? WHERE user_id = ?",
                    (json.dumps(stats, ensure_ascii=False, default=str), datetime.now().isoformat(), user_id),
                )

            return True

    # ================= Wrong Answer Notebook =================
    def list_wrong_answers(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM wrong_answers WHERE user_id = ?"
        params: List[Any] = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_wrong_answers(self, *, user_id: str, status: Optional[str] = None) -> int:
        query = "SELECT COUNT(1) AS c FROM wrong_answers WHERE user_id = ?"
        params: List[Any] = [user_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return int(row["c"]) if row else 0

    def upsert_wrong_answer(
        self,
        user_id: str,
        language: str,
        question_type: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        source_lesson_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        key_source = source_lesson_id or ""

        with self.get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO wrong_answers (
                        user_id, language, question_type, question, user_answer, correct_answer, source_lesson_id,
                        status, wrong_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)
                    """,
                    (
                        user_id,
                        language,
                        question_type,
                        question,
                        user_answer,
                        correct_answer,
                        source_lesson_id,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                conn.execute(
                    """
                    UPDATE wrong_answers
                    SET user_answer = ?,
                        wrong_count = wrong_count + 1,
                        updated_at = ?
                    WHERE user_id = ?
                      AND language = ?
                      AND question_type = ?
                      AND question = ?
                      AND correct_answer = ?
                      AND IFNULL(source_lesson_id, '') = ?
                      AND status = 'active'
                    """,
                    (
                        user_answer,
                        now,
                        user_id,
                        language,
                        question_type,
                        question,
                        correct_answer,
                        key_source,
                    ),
                )

            row = conn.execute(
                """
                SELECT * FROM wrong_answers
                WHERE user_id = ?
                  AND language = ?
                  AND question_type = ?
                  AND question = ?
                  AND correct_answer = ?
                  AND IFNULL(source_lesson_id, '') = ?
                  AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user_id, language, question_type, question, correct_answer, key_source),
            ).fetchone()
            return dict(row) if row else {}

    def update_wrong_answer_status(
        self,
        user_id: str,
        wrong_answer_id: int,
        status: str,
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE wrong_answers
                SET status = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (status, now, wrong_answer_id, user_id),
            )
            if cur.rowcount == 0:
                return None

            row = conn.execute(
                "SELECT * FROM wrong_answers WHERE id = ? AND user_id = ?",
                (wrong_answer_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def delete_wrong_answer(self, user_id: str, wrong_answer_id: int) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM wrong_answers WHERE id = ? AND user_id = ?",
                (wrong_answer_id, user_id),
            )
            return cur.rowcount > 0

    def retry_wrong_answer(
        self,
        user_id: str,
        wrong_answer_id: int,
        user_answer: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM wrong_answers WHERE id = ? AND user_id = ?",
                (wrong_answer_id, user_id),
            ).fetchone()
            if not row:
                return False, None

            correct = str(row["correct_answer"]).strip().lower() == str(user_answer).strip().lower()

            if correct:
                conn.execute(
                    """
                    UPDATE wrong_answers
                    SET status = 'mastered', user_answer = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (user_answer, now, wrong_answer_id, user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE wrong_answers
                    SET user_answer = ?, wrong_count = wrong_count + 1, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (user_answer, now, wrong_answer_id, user_id),
                )

            out = conn.execute(
                "SELECT * FROM wrong_answers WHERE id = ? AND user_id = ?",
                (wrong_answer_id, user_id),
            ).fetchone()
            return correct, (dict(out) if out else None)

    # ================= Daily Learning Activity (Streak) =================
    def record_learning_activity(
        self,
        user_id: str,
        activity_type: str,
        activity_date: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> None:
        activity_date = activity_date or self._local_date_str()
        created_at = created_at or datetime.now().isoformat()

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_learning_activity (user_id, activity_date, activity_type, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, activity_date, activity_type) DO NOTHING
                """,
                (user_id, activity_date, activity_type, created_at),
            )

    def _get_activity_dates(self, user_id: str) -> List[date]:
        """Get all unique activity dates for a user."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT activity_date
                FROM user_learning_activity
                WHERE user_id = ?
                ORDER BY activity_date ASC
                """,
                (user_id,),
            ).fetchall()

        out: List[date] = []
        for row in rows:
            try:
                out.append(date.fromisoformat(str(row["activity_date"])))
            except ValueError:
                continue
        return out

    def get_streak_info(self, user_id: str, today: Optional[date] = None) -> Dict[str, Any]:
        """Get streak information for a user."""
        tz_today = today or date.fromisoformat(self._local_date_str())
        dates = self._get_activity_dates(user_id)

        if not dates:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_active_date": None,
                "today_completed": False,
            }

        date_set = set(dates)
        last_active = max(dates)
        today_completed = tz_today in date_set

        anchor = tz_today if today_completed else (tz_today - timedelta(days=1))
        current = 0
        while anchor in date_set:
            current += 1
            anchor -= timedelta(days=1)

        longest = 0
        run = 0
        prev: Optional[date] = None
        for d in dates:
            if prev is None or d == prev + timedelta(days=1):
                run += 1
            else:
                run = 1
            if run > longest:
                longest = run
            prev = d

        return {
            "current_streak": current,
            "longest_streak": longest,
            "last_active_date": last_active.isoformat(),
            "today_completed": today_completed,
        }


# Global database instance
_db_path = Path(settings.db_path)
_db_path.parent.mkdir(parents=True, exist_ok=True)
db = Database(str(_db_path))
