"""DB init/migration smoke test (ensures migrations apply cleanly on a fresh DB)."""

from database import Database


def test_db_init_and_migrations_smoke(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    # Basic smoke: core tables exist and migrations table populated (at least created).
    with db.get_connection() as conn:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "lessons" in tables
    assert "schema_migrations" in tables
    assert "exercise_results" in tables

