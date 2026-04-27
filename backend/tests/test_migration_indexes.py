"""Critical lesson indexes should exist even on partially migrated databases."""

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
