"""SQLite-safe backup, restore, and validation helpers for local maintenance workflows."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

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


def _open_read_only_connection(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30.0)


def _temporary_output_path(target: Path, *, suffix: str) -> Path:
    with NamedTemporaryFile(
        prefix=f"{target.name}.",
        suffix=suffix,
        dir=target.parent,
        delete=False,
    ) as handle:
        return Path(handle.name)


def _validate_restore_candidate(path: Path) -> ValidationResult:
    db = Database(str(path))
    db.close()
    return validate_sqlite_database(path)


def validate_sqlite_database(path: str | Path) -> ValidationResult:
    resolved = _resolve_path(path)
    _ensure_source_exists(resolved)
    expected_migrations = _expected_migrations()

    with closing(_open_read_only_connection(resolved)) as conn:
        conn.row_factory = sqlite3.Row
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise SQLiteMaintenanceError(
                f"Database validation failed; integrity_check returned {integrity[0] if integrity else '<empty>'}."
            )
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise SQLiteMaintenanceError(
                f"Database validation failed; foreign_key_check returned {len(foreign_key_errors)} row(s)."
            )
        tables = tuple(
            sorted(
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            )
        )
        if "schema_migrations" not in tables:
            raise SQLiteMaintenanceError("Database validation failed; schema_migrations table is missing.")
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

    temp_target = _temporary_output_path(target, suffix=".backup.tmp")
    try:
        _cleanup_sqlite_sidecars(temp_target)
        with closing(sqlite3.connect(str(source), timeout=30.0)) as source_conn:
            with closing(sqlite3.connect(str(temp_target), timeout=30.0)) as target_conn:
                source_conn.backup(target_conn)
        validate_sqlite_database(temp_target)
        _cleanup_sqlite_sidecars(target)
        replace(temp_target, target)
        return target
    except Exception:
        temp_target.unlink(missing_ok=True)
        _cleanup_sqlite_sidecars(temp_target)
        raise


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

    temp_target = _temporary_output_path(target, suffix=".restore.tmp")
    try:
        with closing(sqlite3.connect(str(source), timeout=30.0)) as source_conn:
            with closing(sqlite3.connect(str(temp_target), timeout=30.0)) as target_conn:
                source_conn.backup(target_conn)

        validation = _validate_restore_candidate(temp_target)
        if dry_run:
            temp_target.unlink(missing_ok=True)
            _cleanup_sqlite_sidecars(temp_target)
            return validation

        _cleanup_sqlite_sidecars(target)
        replace(temp_target, target)
        _cleanup_sqlite_sidecars(target)
        return validate_sqlite_database(target)
    except Exception:
        temp_target.unlink(missing_ok=True)
        _cleanup_sqlite_sidecars(temp_target)
        raise
