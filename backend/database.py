"""Database operations for Language Coach."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from models import UserRPGStats


class Database:
    """SQLite database handler."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.db_path).resolve()
        self._ensure_db_directory()
        self.init_database()

    def _ensure_db_directory(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def check_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def init_database(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id TEXT PRIMARY KEY,
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

    def save_lesson(self, lesson_data: Dict[str, Any], file_path: str) -> str:
        metadata = lesson_data["metadata"]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO lessons (
                    lesson_id, language, level, topic, generated_at,
                    estimated_duration_minutes, key_points, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["lesson_id"],
                    metadata["language"],
                    metadata["level"],
                    metadata["topic"],
                    metadata["generated_at"],
                    metadata.get("estimated_duration_minutes"),
                    json.dumps(metadata.get("key_points", []), ensure_ascii=False),
                    str(Path(file_path).resolve()),
                ),
            )
        return metadata["lesson_id"]

    def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)).fetchone()
            return dict(row) if row else None

    def query_lessons(
        self,
        language: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        level: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM lessons WHERE 1=1"
        params: List[Any] = []
        if language:
            query += " AND language = ?"
            params.append(language)
        if start_date:
            query += " AND DATE(generated_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(generated_at) <= ?"
            params.append(end_date)
        if level:
            query += " AND level = ?"
            params.append(level)
        if topic:
            query += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        query += " ORDER BY generated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

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

    def get_progress(self, user_id: str = "default_user") -> Dict[str, Any]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            progress = self.create_default_progress(user_id)
            self.save_progress(progress)
            return progress

        result = dict(row)
        result["english_progress"] = json.loads(result["english_progress"])
        result["japanese_progress"] = json.loads(result["japanese_progress"])
        result["rpg_stats"] = json.loads(result["rpg_stats"]) if result.get("rpg_stats") else UserRPGStats().model_dump(mode="json")
        return result

    def save_progress(self, progress_data: Dict[str, Any]) -> None:
        user_id = progress_data.get("user_id", "default_user")
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

    def get_rpg_stats(self, user_id: str = "default_user") -> Dict[str, Any]:
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
                """,
                (user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate),
            )

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
                    task_data.get("user_id", "default_user"),
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

    def get_today_lesson(self, language: str) -> Optional[Dict[str, Any]]:
        today = datetime.now().date().isoformat()
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM lessons
                WHERE language = ? AND DATE(generated_at) = ?
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                (language, today),
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

    def get_due_srs_items(self, user_id: str, language: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
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


# Global database instance
_db_path = Path(settings.db_path)
_db_path.parent.mkdir(parents=True, exist_ok=True)
db = Database(str(_db_path))
