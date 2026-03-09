"""
Database operations for Language Coach
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from config import settings


class Database:
    """SQLite database handler"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._ensure_db_directory()
        self.init_database()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Lessons table
            cursor.execute("""
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
            """)
            
            # Progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS progress (
                    user_id TEXT PRIMARY KEY,
                    english_progress TEXT NOT NULL,
                    japanese_progress TEXT NOT NULL,
                    rpg_stats TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Achievements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    icon TEXT,
                    rarity TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Word Cards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_cards (
                    word TEXT NOT NULL,
                    language TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (word, language)
                )
            """)

            # Generation Tasks table
            cursor.execute("""
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
            """)
            
            # Exercise results table
            cursor.execute("""
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
            """)
            
            # SRS Vocabulary table
            cursor.execute("""
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
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_language ON lessons(language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(generated_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_level ON lessons(level)")
            
            conn.commit()
    
    def save_lesson(self, lesson_data: Dict[str, Any], file_path: str) -> str:
        """Save lesson metadata to database"""
        metadata = lesson_data['metadata']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lessons (
                    lesson_id, language, level, topic, generated_at,
                    estimated_duration_minutes, key_points, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata['lesson_id'],
                metadata['language'],
                metadata['level'],
                metadata['topic'],
                metadata['generated_at'],
                metadata['estimated_duration_minutes'],
                json.dumps(metadata['key_points'], ensure_ascii=False),
                file_path
            ))
        
        return metadata['lesson_id']
    
    def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get lesson by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
        return None
    
    def query_lessons(
        self,
        language: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        level: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query lessons with filters"""
        query = "SELECT * FROM lessons WHERE 1=1"
        params = []
        
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
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_progress(self, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
        """Get user progress"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['english_progress'] = json.loads(result['english_progress'])
                result['japanese_progress'] = json.loads(result['japanese_progress'])
                result['rpg_stats'] = json.loads(result['rpg_stats']) if result.get('rpg_stats') else None
                return result
        return None
    
    def save_progress(self, progress_data: Dict[str, Any]) -> None:
        """Save or update user progress"""
        user_id = progress_data.get('user_id', 'default_user')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO progress (
                    user_id, english_progress, japanese_progress, rpg_stats, updated_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                json.dumps(progress_data['english_progress'], ensure_ascii=False, default=str),
                json.dumps(progress_data['japanese_progress'], ensure_ascii=False, default=str),
                json.dumps(progress_data.get('rpg_stats', {}), ensure_ascii=False, default=str),
                datetime.now().isoformat()
            ))
    
    def save_exercise_result(
        self,
        user_id: str,
        lesson_id: str,
        exercise_type: str,
        total_questions: int,
        correct_count: int,
        accuracy_rate: float
    ) -> None:
        """Save exercise result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO exercise_results (
                    user_id, lesson_id, exercise_type, total_questions,
                    correct_count, accuracy_rate
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, lesson_id, exercise_type, total_questions, correct_count, accuracy_rate))
    
    def get_today_lesson(self, language: str) -> Optional[Dict[str, Any]]:
        """Get today's lesson for a specific language"""
        today = datetime.now().date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM lessons 
                WHERE language = ? AND DATE(generated_at) = ?
                ORDER BY generated_at DESC LIMIT 1
            """, (language, today))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
        return None

    def save_generation_task(self, task_data: Dict[str, Any]):
        """Save or update a generation task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO generation_tasks (
                    task_id, user_id, status, model_used, duration_ms, 
                    error_message, retry_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['task_id'], task_data['user_id'], task_data['status'],
                task_data['model_used'], task_data.get('duration_ms', 0),
                task_data.get('error_message'), task_data.get('retry_count', 0),
                task_data.get('created_at', datetime.now().isoformat())
            ))

    def get_generation_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent generation tasks for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM generation_tasks 
                WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# Global database instance
db = Database()

    def update_srs_item(self, user_id: str, word: str, language: str, srs_data: Dict[str, Any], vocab_info: Dict[str, Any]) -> None:
        """Update or insert SRS item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
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
            """, (
                user_id, word, language, json.dumps(vocab_info, ensure_ascii=False),
                srs_data['repetition'], srs_data['ease_factor'], srs_data['interval'],
                srs_data['next_review'].isoformat(), datetime.now().isoformat()
            ))

    def get_due_srs_items(self, user_id: str, language: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get items due for review"""
        query = "SELECT * FROM srs_vocabulary WHERE user_id = ? AND next_review <= ?"
        params = [user_id, datetime.now().isoformat()]
        
        if language:
            query += " AND language = ?"
            params.append(language)
            
        query += " ORDER BY next_review ASC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
