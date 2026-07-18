from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
import sqlite_maintenance as maintenance_module
from database import Database
from sqlite_maintenance import (
    SQLiteMaintenanceError,
    backup_sqlite_database,
    restore_sqlite_database,
    validate_sqlite_database,
)


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _create_valid_database(path: Path) -> None:
    db = Database(str(path))
    with db.get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("DELETE FROM sample")
        conn.execute("INSERT INTO sample (value) VALUES ('kept')")
    db.close()


def test_validate_is_byte_for_byte_read_only(tmp_path):
    source = tmp_path / "source.sqlite3"
    _create_valid_database(source)
    before_hash = _file_digest(source)
    before_size = source.stat().st_size

    result = validate_sqlite_database(source)

    assert result.source_path == source.resolve()
    assert source.stat().st_size == before_size
    assert _file_digest(source) == before_hash


def test_validate_reports_missing_migrations_without_modifying_source(tmp_path):
    source = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(source)
    try:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP)")
        conn.commit()
    finally:
        conn.close()
    before_hash = _file_digest(source)
    before_size = source.stat().st_size

    with pytest.raises(SQLiteMaintenanceError, match="missing applied migrations"):
        validate_sqlite_database(source)

    assert source.stat().st_size == before_size
    assert _file_digest(source) == before_hash


def test_backup_uses_sqlite_copy_and_preserves_data(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "backup.sqlite3"
    _create_valid_database(source)

    result = backup_sqlite_database(source_path=source, target_path=target)

    assert result == target.resolve()
    conn = sqlite3.connect(target)
    try:
        row = conn.execute("SELECT value FROM sample").fetchone()
    finally:
        conn.close()
    assert row[0] == "kept"


def test_backup_dry_run_does_not_create_output(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "backup.sqlite3"
    _create_valid_database(source)
    source_hash = _file_digest(source)

    result = backup_sqlite_database(source_path=source, target_path=target, dry_run=True)

    assert result == target.resolve()
    assert not target.exists()
    assert _file_digest(source) == source_hash


def test_backup_failure_preserves_existing_target_and_cleans_temp_files(tmp_path, monkeypatch):
    from sqlite_maintenance import validate_sqlite_database as real_validate

    source = tmp_path / "source.sqlite3"
    target = tmp_path / "backup.sqlite3"
    _create_valid_database(source)
    _create_valid_database(target)
    original_hash = _file_digest(target)

    def _fail_validation(path):
        if Path(path).name.endswith(".backup.tmp"):
            raise SQLiteMaintenanceError("forced backup validation failure")
        return real_validate(path)

    monkeypatch.setattr(maintenance_module, "validate_sqlite_database", _fail_validation)

    with pytest.raises(SQLiteMaintenanceError, match="forced backup validation failure"):
        backup_sqlite_database(source_path=source, target_path=target, force=True)

    assert _file_digest(target) == original_hash
    assert list(tmp_path.glob("*.backup.tmp")) == []


def test_restore_refuses_to_overwrite_existing_target_without_force(tmp_path):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    _create_valid_database(backup)
    _create_valid_database(target)

    with pytest.raises(SQLiteMaintenanceError, match="Refusing to overwrite existing target"):
        restore_sqlite_database(backup_path=backup, target_path=target)


def test_restore_dry_run_validates_temp_copy_without_writing_target(tmp_path):
    backup = tmp_path / "restorable.sqlite3"
    target = tmp_path / "target.sqlite3"
    _create_valid_database(backup)
    backup_hash = _file_digest(backup)

    result = restore_sqlite_database(backup_path=backup, target_path=target, dry_run=True)

    assert "schema_migrations" in result.tables
    assert "0007_micro_lesson_reward_events.sql" in result.applied_migrations
    assert not target.exists()
    assert _file_digest(backup) == backup_hash
    assert list(tmp_path.glob("*.restore.tmp")) == []


def test_restore_force_replaces_target_and_runs_validation(tmp_path):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    _create_valid_database(backup)
    _create_valid_database(target)

    conn = sqlite3.connect(backup)
    try:
        conn.execute("UPDATE sample SET value = 'restored'")
        conn.commit()
    finally:
        conn.close()

    result = restore_sqlite_database(backup_path=backup, target_path=target, force=True)

    assert result.source_path == target.resolve()
    conn = sqlite3.connect(target)
    try:
        row = conn.execute("SELECT value FROM sample").fetchone()
    finally:
        conn.close()
    assert row[0] == "restored"
    validation = validate_sqlite_database(target)
    assert "schema_migrations" in validation.tables


def test_restore_failure_preserves_existing_target_and_cleans_temp_files(tmp_path, monkeypatch):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    _create_valid_database(backup)
    _create_valid_database(target)
    original_hash = _file_digest(target)

    def _fail_validation(path):
        raise SQLiteMaintenanceError(f"forced restore validation failure for {Path(path).name}")

    monkeypatch.setattr(maintenance_module, "_validate_restore_candidate", _fail_validation)

    with pytest.raises(SQLiteMaintenanceError, match="forced restore validation failure"):
        restore_sqlite_database(backup_path=backup, target_path=target, force=True)

    assert _file_digest(target) == original_hash
    assert list(tmp_path.glob("*.restore.tmp")) == []
