"""SQLite-safe backup, restore, and validation helpers for local maintenance workflows."""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from config import settings
from database import Database

DEFAULT_BACKUP_DIR = settings.data_path / "backups"


class SQLiteMaintenanceError(RuntimeError):
    """Raised when a backup or restore operation cannot complete safely."""


@dataclass(frozen=True)
class ValidationResult:
    source_path: Path
    tables: tuple[str, ...]
    applied_migrations: tuple[str, ...]


def _resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _cleanup_sqlite_sidecars(target: Path) -> None:
    for suffix in ("-wal", "-shm"):
        target.with_name(f"{target.name}{suffix}").unlink(missing_ok=True)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _ensure_source_exists(path: Path) -> None:
    if not path.exists():
        raise SQLiteMaintenanceError(f"SQLite source file does not exist: {path}")


def _ensure_target_writable(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise SQLiteMaintenanceError(
            f"Refusing to overwrite existing target without --force: {path}"
        )


def _expected_migrations() -> tuple[str, ...]:
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    return tuple(path.name for path in sorted(migrations_dir.glob("*.sql")))


def validate_sqlite_database(path: str | Path) -> ValidationResult:
    resolved = _resolve_path(path)
    _ensure_source_exists(resolved)
    db = Database(str(resolved))
    expected_migrations = _expected_migrations()
    db.close()

    with sqlite3.connect(str(resolved), timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        tables = tuple(
            sorted(
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            )
        )
        applied_migrations = tuple(
            row["version"]
            for row in conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        )

    missing = [version for version in expected_migrations if version not in applied_migrations]
    if missing:
        raise SQLiteMaintenanceError(
            f"Database validation failed; missing applied migrations: {', '.join(missing)}"
        )

    return ValidationResult(
        source_path=resolved,
        tables=tables,
        applied_migrations=applied_migrations,
    )


def backup_sqlite_database(
    *,
    source_path: str | Path | None = None,
    target_path: str | Path,
    force: bool = False,
    dry_run: bool = False,
) -> Path:
    source = _resolve_path(source_path or settings.db_path)
    target = _resolve_path(target_path)
    _ensure_source_exists(source)
    _ensure_target_writable(target, force=force)
    _ensure_parent(target)

    if dry_run:
        return target

    _cleanup_sqlite_sidecars(target)
    with sqlite3.connect(str(source), timeout=30.0) as source_conn:
        with sqlite3.connect(str(target), timeout=30.0) as target_conn:
            source_conn.backup(target_conn)
    return target


def restore_sqlite_database(
    *,
    backup_path: str | Path,
    target_path: str | Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> ValidationResult:
    source = _resolve_path(backup_path)
    target = _resolve_path(target_path or settings.db_path)
    _ensure_source_exists(source)
    _ensure_target_writable(target, force=force)
    _ensure_parent(target)

    with tempfile.TemporaryDirectory(prefix="sqlite-restore-", ignore_cleanup_errors=True) as temp_dir:
        temp_target = Path(temp_dir) / target.name
        with sqlite3.connect(str(source), timeout=30.0) as source_conn:
            with sqlite3.connect(str(temp_target), timeout=30.0) as target_conn:
                source_conn.backup(target_conn)

        validation = validate_sqlite_database(temp_target)
        if dry_run:
            return validation

        with sqlite3.connect(str(temp_target), timeout=30.0) as source_conn:
            with sqlite3.connect(str(target), timeout=30.0) as target_conn:
                source_conn.backup(target_conn)
        _cleanup_sqlite_sidecars(target)

    return validate_sqlite_database(target)
