"""Database operations for Language Coach."""
import json
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from zoneinfo import ZoneInfo

from config import settings
from models import UserRPGStats
from time_utils import local_now


def _local_now() -> datetime:
    return local_now()


def _json_loads_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_loads_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


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
                latest_correct_count INTEGER,
                latest_accuracy_rate REAL,
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
                part_of_speech TEXT,
                root TEXT,
                prefix TEXT,
                suffix TEXT,
                word_family TEXT,
                memory_tip TEXT,
                category TEXT,
                tags TEXT,
                source_lesson_id TEXT,
                mastery_state TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, language, word)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostic_state (
                user_id TEXT PRIMARY KEY,
                estimated_total_days INTEGER NOT NULL,
                current_day INTEGER NOT NULL DEFAULT 1,
                summary_zh TEXT NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                completed_at TIMESTAMP NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS micro_lessons (
                lesson_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                day_index INTEGER NOT NULL,
                lesson_json TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, day_index)
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_language ON lessons(language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(generated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_srs_due ON srs_vocabulary(next_review)")

        self.run_migrations()
        self.ensure_runtime_indexes()

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
            if version == "0004_exercise_results_latest_attempt.sql":
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(exercise_results)").fetchall()]
                if "latest_correct_count" in cols and "latest_accuracy_rate" in cols:
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                    continue
            if version == "0005_vocabulary_categories_and_roots.sql":
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(imported_vocabulary)").fetchall()]
                if {
                    "part_of_speech",
                    "root",
                    "prefix",
                    "suffix",
                    "word_family",
                    "memory_tip",
                    "category",
                    "tags",
                    "source_lesson_id",
                    "mastery_state",
                }.issubset(set(cols)):
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                    continue
            sql = file_path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    def ensure_runtime_indexes(self) -> None:
        """Backfill critical indexes even on partially migrated databases."""
        conn = self._connection
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_user ON lessons(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_user_date ON lessons(user_id, generated_at DESC)")
        self._cleanup_exercise_result_duplicates(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_results_unique "
            "ON exercise_results(user_id, lesson_id, exercise_type)"
        )
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(exercise_results)").fetchall()]
        if "latest_correct_count" not in cols:
            conn.execute("ALTER TABLE exercise_results ADD COLUMN latest_correct_count INTEGER")
        if "latest_accuracy_rate" not in cols:
            conn.execute("ALTER TABLE exercise_results ADD COLUMN latest_accuracy_rate REAL")
        imported_cols = [r["name"] for r in conn.execute("PRAGMA table_info(imported_vocabulary)").fetchall()]
        imported_defs = {
            "part_of_speech": "TEXT",
            "root": "TEXT",
            "prefix": "TEXT",
            "suffix": "TEXT",
            "word_family": "TEXT",
            "memory_tip": "TEXT",
            "category": "TEXT",
            "tags": "TEXT",
            "source_lesson_id": "TEXT",
            "mastery_state": "TEXT DEFAULT 'new'",
        }
        for column, column_type in imported_defs.items():
            if column not in imported_cols:
                conn.execute(f"ALTER TABLE imported_vocabulary ADD COLUMN {column} {column_type}")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostic_state (
                user_id TEXT PRIMARY KEY,
                estimated_total_days INTEGER NOT NULL,
                current_day INTEGER NOT NULL DEFAULT 1,
                summary_zh TEXT NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                completed_at TIMESTAMP NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS micro_lessons (
                lesson_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                day_index INTEGER NOT NULL,
                lesson_json TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, day_index)
            )
            """
        )

    def _cleanup_exercise_result_duplicates(self, conn: sqlite3.Connection) -> None:
        """Keep the newest row per unique exercise-result key before unique index creation."""
        conn.execute(
            """
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
            )
            """
        )

    def _local_date_str(self, dt: Optional[datetime] = None) -> str:
        tz = ZoneInfo(settings.timezone)
        now = dt.astimezone(tz) if dt else _local_now()
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
            "updated_at": _local_now().isoformat(),
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
                    _local_now().isoformat(),
                ),
            )

    def get_rpg_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        progress = self.get_progress(user_id)
        return progress.get("rpg_stats") or UserRPGStats().model_dump(mode="json")

    def save_rpg_stats(self, user_id: str, rpg_stats: Dict[str, Any]) -> None:
        progress = self.get_progress(user_id)
        progress["rpg_stats"] = rpg_stats
        self.save_progress(progress)

    def get_diagnostic_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM diagnostic_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def save_diagnostic_state(
        self,
        *,
        user_id: str,
        estimated_total_days: int,
        current_day: int,
        summary_zh: str,
        correct_count: int,
    ) -> Dict[str, Any]:
        completed_at = _local_now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO diagnostic_state (
                    user_id, estimated_total_days, current_day, summary_zh, correct_count, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    estimated_total_days=excluded.estimated_total_days,
                    current_day=excluded.current_day,
                    summary_zh=excluded.summary_zh,
                    correct_count=excluded.correct_count,
                    completed_at=excluded.completed_at
                """,
                (user_id, estimated_total_days, current_day, summary_zh, correct_count, completed_at),
            )
        return {
            "estimated_total_days": estimated_total_days,
            "current_day": current_day,
            "summary_zh": summary_zh,
        }

    def save_micro_lesson(self, user_id: str, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        now = _local_now().isoformat()
        completed = 1 if lesson_data.get("completed") else 0
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO micro_lessons (
                    lesson_id, user_id, day_index, lesson_json, completed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, day_index) DO UPDATE SET
                    lesson_id=excluded.lesson_id,
                    lesson_json=excluded.lesson_json,
                    completed=excluded.completed,
                    updated_at=excluded.updated_at
                """,
                (
                    lesson_data["lesson_id"],
                    user_id,
                    lesson_data["day_index"],
                    json.dumps(lesson_data, ensure_ascii=False, default=str),
                    completed,
                    now,
                    now,
                ),
            )
        return lesson_data

    def get_micro_lesson_by_day(self, user_id: str, day_index: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT lesson_json, completed
                FROM micro_lessons
                WHERE user_id = ? AND day_index = ?
                """,
                (user_id, day_index),
            ).fetchone()
        if not row:
            return None
        lesson = json.loads(row["lesson_json"])
        lesson["completed"] = bool(row["completed"])
        return lesson

    def get_micro_lesson_by_id(self, user_id: str, lesson_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT lesson_json, completed
                FROM micro_lessons
                WHERE user_id = ? AND lesson_id = ?
                """,
                (user_id, lesson_id),
            ).fetchone()
        if not row:
            return None
        lesson = json.loads(row["lesson_json"])
        lesson["completed"] = bool(row["completed"])
        return lesson

    def mark_micro_lesson_completed(self, user_id: str, lesson_id: str) -> Optional[Dict[str, Any]]:
        lesson = self.get_micro_lesson_by_id(user_id, lesson_id)
        if not lesson:
            return None
        if not lesson.get("completed"):
            lesson["completed"] = True
            now = _local_now().isoformat()
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE micro_lessons
                    SET lesson_json = ?, completed = 1, updated_at = ?
                    WHERE user_id = ? AND lesson_id = ?
                    """,
                    (json.dumps(lesson, ensure_ascii=False, default=str), now, user_id, lesson_id),
                )
                conn.execute(
                    """
                    UPDATE diagnostic_state
                    SET current_day = current_day + 1
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )
        return lesson

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
                    user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate,
                    latest_correct_count, latest_accuracy_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id, exercise_type) DO UPDATE SET
                    total_questions=excluded.total_questions,
                    correct_count=MAX(exercise_results.correct_count, excluded.correct_count),
                    accuracy_rate=MAX(exercise_results.accuracy_rate, excluded.accuracy_rate),
                    latest_correct_count=excluded.latest_correct_count,
                    latest_accuracy_rate=excluded.latest_accuracy_rate,
                    submitted_at=CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    lesson_id,
                    exercise_type,
                    total_questions,
                    correct_count,
                    accuracy_rate,
                    correct_count,
                    accuracy_rate,
                ),
            )

    def get_exercise_result(
        self,
        *,
        user_id: str,
        lesson_id: str,
        exercise_type: str,
    ) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT lesson_id, exercise_type, total_questions, correct_count, accuracy_rate,
                       latest_correct_count, latest_accuracy_rate, submitted_at
                FROM exercise_results
                WHERE user_id = ? AND lesson_id = ? AND exercise_type = ?
                """,
                (user_id, lesson_id, exercise_type),
            ).fetchone()
            return dict(row) if row else None

    def list_recent_exercise_results(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT lesson_id, exercise_type, total_questions, correct_count, accuracy_rate,
                       latest_correct_count, latest_accuracy_rate, submitted_at
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
                    task_data.get("created_at", _local_now().isoformat()),
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
        today = self._local_date_str()
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM lessons
                WHERE user_id = ? AND language = ?
                ORDER BY generated_at DESC
                LIMIT 20
                """,
                (user_id, language),
            ).fetchall()

        for row in rows:
            generated_at_raw = row["generated_at"]
            if not generated_at_raw:
                continue
            try:
                generated_at = datetime.fromisoformat(str(generated_at_raw))
            except ValueError:
                continue
            if self._local_date_str(generated_at) == today:
                return dict(row)
        return None

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
                    _local_now().isoformat(),
                ),
            )

    def get_due_srs_items(
        self,
        user_id: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM srs_vocabulary WHERE user_id = ? AND next_review <= ?"
        params: List[Any] = [user_id, _local_now().isoformat()]

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

    def count_due_srs_items(self, user_id: str, language: Optional[str] = None) -> int:
        query = "SELECT COUNT(1) AS count FROM srs_vocabulary WHERE user_id = ? AND next_review <= ?"
        params: List[Any] = [user_id, _local_now().isoformat()]
        if language:
            query += " AND language = ?"
            params.append(language)
        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["count"]) if row else 0

    def upsert_learning_item(
        self,
        *,
        user_id: str,
        item_type: str,
        item_key: str,
        language: str,
        level: Optional[str],
        lesson_id: Optional[str],
        content: Dict[str, Any],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized_key = str(item_key).strip()
        if not normalized_key:
            raise ValueError("item_key is required")

        now = _local_now().isoformat()
        content_json = json.dumps(content, ensure_ascii=False, default=str)
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        item_id: Optional[str] = None

        with self.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM learning_items
                WHERE user_id = ? AND item_type = ? AND item_key = ? AND language = ?
                """,
                (user_id, item_type, normalized_key, language),
            ).fetchone()
            item_id = str(existing["id"]) if existing else str(uuid4())
            conn.execute(
                """
                INSERT INTO learning_items (
                    id, user_id, item_type, item_key, language, level, lesson_id,
                    content_json, category, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, item_type, item_key, language) DO UPDATE SET
                    level = excluded.level,
                    lesson_id = excluded.lesson_id,
                    content_json = excluded.content_json,
                    category = excluded.category,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    user_id,
                    item_type,
                    normalized_key,
                    language,
                    level,
                    lesson_id,
                    content_json,
                    category,
                    tags_json,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO learning_item_srs (item_id, due_at)
                VALUES (?, ?)
                ON CONFLICT(item_id) DO NOTHING
                """,
                (item_id, now),
            )

        return self.get_learning_item(user_id=user_id, item_id=item_id) or {}

    def get_learning_item(self, *, user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                       ls.due_at, ls.last_reviewed_at, ls.mastery_state
                FROM learning_items AS li
                JOIN learning_item_srs AS ls ON ls.item_id = li.id
                WHERE li.user_id = ? AND li.id = ?
                """,
                (user_id, item_id),
            ).fetchone()
        return self._decode_learning_item_row(row) if row else None

    def get_learning_item_by_key(
        self,
        *,
        user_id: str,
        item_type: str,
        item_key: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                       ls.due_at, ls.last_reviewed_at, ls.mastery_state
                FROM learning_items AS li
                JOIN learning_item_srs AS ls ON ls.item_id = li.id
                WHERE li.user_id = ? AND li.item_type = ? AND li.item_key = ? AND li.language = ?
                """,
                (user_id, item_type, str(item_key).strip(), language),
            ).fetchone()
        return self._decode_learning_item_row(row) if row else None

    def _decode_learning_item_row(self, row: sqlite3.Row | None) -> Dict[str, Any]:
        if row is None:
            return {}
        item = dict(row)
        item["content"] = _json_loads_dict(item.pop("content_json", {}))
        item["tags"] = _json_loads_list(item.get("tags"))
        return item

    def record_learning_item_review(
        self,
        *,
        user_id: str,
        item_id: str,
        rating: int,
        correct: bool,
        response_time_ms: Optional[int] = None,
        source: str = "manual",
    ) -> Dict[str, Any]:
        existing = self.get_learning_item(user_id=user_id, item_id=item_id)
        if not existing:
            raise ValueError("learning item not found")

        from srs import srs_engine

        srs_data = srs_engine.calculate(
            quality=rating,
            prev_interval=int(existing.get("interval_days") or 0),
            prev_ease_factor=float(existing.get("ease_factor") or 2.5),
            repetition=int(existing.get("repetitions") or 0),
        )
        now = _local_now().isoformat()
        repetitions = int(srs_data["repetition"])
        lapses = int(existing.get("lapses") or 0) + (1 if rating < 3 else 0)
        if rating < 3:
            mastery_state = "weak" if lapses > 1 or not correct else "learning"
        elif repetitions >= 5:
            mastery_state = "mastered"
        elif repetitions >= 2:
            mastery_state = "review"
        else:
            mastery_state = "learning"

        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE learning_item_srs
                SET interval_days = ?, ease_factor = ?, repetitions = ?, lapses = ?,
                    due_at = ?, last_reviewed_at = ?, mastery_state = ?
                WHERE item_id = ?
                """,
                (
                    int(srs_data["interval"]),
                    float(srs_data["ease_factor"]),
                    repetitions,
                    lapses,
                    srs_data["next_review"].isoformat(),
                    now,
                    mastery_state,
                    item_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO learning_item_reviews (
                    id, item_id, rating, correct, response_time_ms, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    item_id,
                    rating,
                    1 if correct else 0,
                    response_time_ms,
                    source,
                    now,
                ),
            )

        updated = self.get_learning_item(user_id=user_id, item_id=item_id) or {}
        self._sync_imported_vocabulary_mastery(
            user_id=user_id,
            item_type=str(updated.get("item_type") or ""),
            item_key=str(updated.get("item_key") or ""),
            language=str(updated.get("language") or ""),
            mastery_state=str(updated.get("mastery_state") or "new"),
        )
        return updated

    def _sync_imported_vocabulary_mastery(
        self,
        *,
        user_id: str,
        item_type: str,
        item_key: str,
        language: str,
        mastery_state: str,
    ) -> None:
        if item_type != "vocabulary":
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE imported_vocabulary
                SET mastery_state = ?
                WHERE user_id = ? AND word = ? AND language = ?
                """,
                (mastery_state, user_id, item_key, language),
            )

    def list_due_learning_items(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        item_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        where = ["li.user_id = ?", "ls.due_at <= ?"]
        params: List[Any] = [user_id, _local_now().isoformat()]
        if language:
            where.append("li.language = ?")
            params.append(language)
        if item_type:
            where.append("li.item_type = ?")
            params.append(item_type)

        query = f"""
            SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                   ls.due_at, ls.last_reviewed_at, ls.mastery_state
            FROM learning_items AS li
            JOIN learning_item_srs AS ls ON ls.item_id = li.id
            WHERE {' AND '.join(where)}
            ORDER BY ls.due_at ASC, li.updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode_learning_item_row(row) for row in rows]

    def count_due_learning_items_by_type(self, *, user_id: str, language: Optional[str] = None) -> Dict[str, int]:
        where = ["li.user_id = ?", "ls.due_at <= ?"]
        params: List[Any] = [user_id, _local_now().isoformat()]
        if language:
            where.append("li.language = ?")
            params.append(language)
        with self.get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT li.item_type, COUNT(1) AS count
                FROM learning_items AS li
                JOIN learning_item_srs AS ls ON ls.item_id = li.id
                WHERE {' AND '.join(where)}
                GROUP BY li.item_type
                """,
                params,
            ).fetchall()
        return {str(row["item_type"]): int(row["count"]) for row in rows}

    def get_weak_learning_items(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        where = ["li.user_id = ?", "ls.mastery_state IN ('weak', 'learning')"]
        params: List[Any] = [user_id]
        if language:
            where.append("li.language = ?")
            params.append(language)
        query = f"""
            SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                   ls.due_at, ls.last_reviewed_at, ls.mastery_state
            FROM learning_items AS li
            JOIN learning_item_srs AS ls ON ls.item_id = li.id
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE ls.mastery_state WHEN 'weak' THEN 0 ELSE 1 END,
                ls.last_reviewed_at DESC,
                li.updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode_learning_item_row(row) for row in rows]

    def get_recent_learning_items(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        item_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        where = ["li.user_id = ?"]
        params: List[Any] = [user_id]
        if language:
            where.append("li.language = ?")
            params.append(language)
        if item_type:
            where.append("li.item_type = ?")
            params.append(item_type)
        query = f"""
            SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                   ls.due_at, ls.last_reviewed_at, ls.mastery_state
            FROM learning_items AS li
            JOIN learning_item_srs AS ls ON ls.item_id = li.id
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(ls.last_reviewed_at, li.updated_at) DESC
            LIMIT ?
        """
        params.append(limit)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode_learning_item_row(row) for row in rows]

    def get_learning_item_stats(self, *, user_id: str, language: Optional[str] = None) -> Dict[str, Any]:
        where = ["li.user_id = ?"]
        params: List[Any] = [user_id]
        if language:
            where.append("li.language = ?")
            params.append(language)
        with self.get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT li.item_type, ls.mastery_state, COUNT(1) AS count
                FROM learning_items AS li
                JOIN learning_item_srs AS ls ON ls.item_id = li.id
                WHERE {' AND '.join(where)}
                GROUP BY li.item_type, ls.mastery_state
                """,
                params,
            ).fetchall()
        summary: Dict[str, Dict[str, int]] = {}
        for row in rows:
            item_type = str(row["item_type"])
            mastery_state = str(row["mastery_state"])
            summary.setdefault(item_type, {})[mastery_state] = int(row["count"])
        return summary

    def get_reviewed_learning_items(
        self,
        *,
        user_id: str,
        item_type: str,
        limit: int = 5,
        weakest: bool = True,
    ) -> List[Dict[str, Any]]:
        order = (
            "SUM(CASE WHEN lir.correct = 0 THEN 1 ELSE 0 END) DESC, "
            "AVG(lir.rating) ASC, MAX(lir.created_at) DESC"
            if weakest
            else "MAX(lir.created_at) DESC"
        )
        with self.get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT li.*, ls.interval_days, ls.ease_factor, ls.repetitions, ls.lapses,
                       ls.due_at, ls.last_reviewed_at, ls.mastery_state,
                       COUNT(lir.id) AS review_count,
                       SUM(CASE WHEN lir.correct = 0 THEN 1 ELSE 0 END) AS incorrect_count,
                       AVG(lir.rating) AS average_rating
                FROM learning_items AS li
                JOIN learning_item_srs AS ls ON ls.item_id = li.id
                JOIN learning_item_reviews AS lir ON lir.item_id = li.id
                WHERE li.user_id = ? AND li.item_type = ?
                GROUP BY li.id
                ORDER BY {order}
                LIMIT ?
                """,
                (user_id, item_type, limit),
            ).fetchall()
        items = []
        for row in rows:
            item = self._decode_learning_item_row(row)
            item["review_count"] = int(row["review_count"] or 0)
            item["incorrect_count"] = int(row["incorrect_count"] or 0)
            item["average_rating"] = float(row["average_rating"] or 0)
            items.append(item)
        return items

    def get_recent_learning_item_review_counts(self, *, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        start_date = (_local_now() - timedelta(days=days - 1)).date().isoformat()
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT SUBSTR(lir.created_at, 1, 10) AS review_date, COUNT(1) AS count
                FROM learning_item_reviews AS lir
                JOIN learning_items AS li ON li.id = lir.item_id
                WHERE li.user_id = ? AND SUBSTR(lir.created_at, 1, 10) >= ?
                GROUP BY SUBSTR(lir.created_at, 1, 10)
                ORDER BY review_date ASC
                """,
                (user_id, start_date),
            ).fetchall()
        return [{"date": str(row["review_date"]), "count": int(row["count"])} for row in rows]

    def sync_lesson_items_to_learning_items(
        self,
        *,
        user_id: str,
        lesson_data: Dict[str, Any],
        language: str,
        level: Optional[str],
        lesson_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        synced: List[Dict[str, Any]] = []

        for vocab in lesson_data.get("vocabulary", []) or []:
            if not isinstance(vocab, dict):
                continue
            word = str(vocab.get("word", "")).strip()
            if not word:
                continue
            synced.append(
                self.upsert_learning_item(
                    user_id=user_id,
                    item_type="vocabulary",
                    item_key=word,
                    language=language,
                    level=level,
                    lesson_id=lesson_id,
                    content=vocab,
                    category=str(vocab.get("category")).strip() if vocab.get("category") else None,
                    tags=[str(tag) for tag in vocab.get("tags", []) if str(tag).strip()],
                )
            )

        grammar = lesson_data.get("grammar", {})
        if isinstance(grammar, dict):
            title = str(grammar.get("title", "")).strip()
            if title:
                synced.append(
                    self.upsert_learning_item(
                        user_id=user_id,
                        item_type="grammar",
                        item_key=title,
                        language=language,
                        level=level,
                        lesson_id=lesson_id,
                        content=grammar,
                        category="grammar",
                        tags=[],
                    )
                )

        for pattern in lesson_data.get("sentence_patterns", []) or []:
            if not isinstance(pattern, dict):
                continue
            item_key = str(pattern.get("pattern", "")).strip()
            if not item_key:
                continue
            synced.append(
                self.upsert_learning_item(
                    user_id=user_id,
                    item_type="sentence_pattern",
                    item_key=item_key,
                    language=language,
                    level=level,
                    lesson_id=lesson_id,
                    content=pattern,
                    category="sentence_pattern",
                    tags=[],
                )
            )

        return synced

    def save_feynman_feedback_history(
        self,
        *,
        user_id: str,
        lesson_id: str,
        explanation: str,
        feedback: Dict[str, Any],
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO feynman_feedback_history (
                    id, user_id, lesson_id, explanation, feedback_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user_id,
                    lesson_id,
                    explanation,
                    json.dumps(feedback, ensure_ascii=False, default=str),
                    _local_now().isoformat(),
                ),
            )

    def save_imported_vocabulary(self, user_id: str, language: str, item: Dict[str, Any]) -> None:
        word_family = item.get("word_family")
        tags = item.get("tags")
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO imported_vocabulary (
                    user_id, language, word, reading, definition_zh, example_sentence, example_translation,
                    part_of_speech, root, prefix, suffix, word_family, memory_tip, category, tags,
                    source_lesson_id, mastery_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, language, word) DO UPDATE SET
                    reading=excluded.reading,
                    definition_zh=excluded.definition_zh,
                    example_sentence=excluded.example_sentence,
                    example_translation=excluded.example_translation,
                    part_of_speech=excluded.part_of_speech,
                    root=excluded.root,
                    prefix=excluded.prefix,
                    suffix=excluded.suffix,
                    word_family=excluded.word_family,
                    memory_tip=excluded.memory_tip,
                    category=excluded.category,
                    tags=excluded.tags,
                    source_lesson_id=excluded.source_lesson_id,
                    mastery_state=excluded.mastery_state
                """,
                (
                    user_id,
                    language,
                    item["word"],
                    item.get("reading"),
                    item["definition_zh"],
                    item.get("example_sentence", ""),
                    item.get("example_translation", ""),
                    item.get("part_of_speech"),
                    item.get("root"),
                    item.get("prefix"),
                    item.get("suffix"),
                    json.dumps(word_family, ensure_ascii=False) if isinstance(word_family, list) else None,
                    item.get("memory_tip"),
                    item.get("category"),
                    json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else None,
                    item.get("source_lesson_id"),
                    item.get("mastery_state", "new"),
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
            search_columns = (
                "word",
                "definition_zh",
                "root",
                "prefix",
                "suffix",
                "category",
                "tags",
                "memory_tip",
                "part_of_speech",
            )
            where.append("(" + " OR ".join(f"{column} LIKE ?" for column in search_columns) + ")")
            like = f"%{q}%"
            params.extend([like] * len(search_columns))

        where_sql = " AND ".join(where)
        with self.get_connection() as conn:
            count_row = conn.execute(f"SELECT COUNT(1) AS c FROM imported_vocabulary WHERE {where_sql}", params).fetchone()
            rows = conn.execute(
                f"""
                SELECT id, user_id, language, word, reading, definition_zh, example_sentence,
                       example_translation, part_of_speech, root, prefix, suffix, word_family,
                       memory_tip, category, tags, source_lesson_id,
                       COALESCE(mastery_state, 'new') AS mastery_state, created_at
                FROM imported_vocabulary
                WHERE {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                for key in ("word_family", "tags"):
                    raw = item.get(key)
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            item[key] = parsed if isinstance(parsed, list) else []
                        except Exception:
                            item[key] = []
                    else:
                        item[key] = []
                items.append(item)
            return items, int(count_row["c"]) if count_row else 0

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
                    (json.dumps(stats, ensure_ascii=False, default=str), _local_now().isoformat(), user_id),
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
        now = _local_now().isoformat()
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
        now = _local_now().isoformat()
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
        now = _local_now().isoformat()
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
        created_at = created_at or _local_now().isoformat()

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
