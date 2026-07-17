from __future__ import annotations

import sqlite3

import pytest
from sqlite_maintenance import (
    SQLiteMaintenanceError,
    backup_sqlite_database,
    restore_sqlite_database,
    validate_sqlite_database,
)


def _seed_database(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO sample (value) VALUES ('kept')")


def test_backup_uses_sqlite_copy_and_preserves_data(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "backup.sqlite3"
    _seed_database(source)

    result = backup_sqlite_database(source_path=source, target_path=target)

    assert result == target.resolve()
    with sqlite3.connect(target) as conn:
        row = conn.execute("SELECT value FROM sample").fetchone()
    assert row[0] == "kept"


def test_backup_dry_run_does_not_create_output(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "backup.sqlite3"
    _seed_database(source)

    result = backup_sqlite_database(source_path=source, target_path=target, dry_run=True)

    assert result == target.resolve()
    assert not target.exists()


def test_restore_refuses_to_overwrite_existing_target_without_force(tmp_path):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    _seed_database(backup)
    _seed_database(target)

    with pytest.raises(SQLiteMaintenanceError, match="Refusing to overwrite existing target"):
        restore_sqlite_database(backup_path=backup, target_path=target)


def test_restore_dry_run_validates_migrations_on_temp_database(tmp_path):
    backup = tmp_path / "restorable.sqlite3"
    _seed_database(backup)

    result = restore_sqlite_database(backup_path=backup, target_path=tmp_path / "target.sqlite3", dry_run=True)

    assert "schema_migrations" in result.tables
    assert "0007_micro_lesson_reward_events.sql" in result.applied_migrations
    assert not (tmp_path / "target.sqlite3").exists()


def test_restore_force_replaces_target_and_runs_validation(tmp_path):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    _seed_database(backup)
    _seed_database(target)

    result = restore_sqlite_database(backup_path=backup, target_path=target, force=True)

    assert result.source_path == target.resolve()
    with sqlite3.connect(target) as conn:
        row = conn.execute("SELECT value FROM sample").fetchone()
    assert row[0] == "kept"
    validation = validate_sqlite_database(target)
    assert "schema_migrations" in validation.tables
