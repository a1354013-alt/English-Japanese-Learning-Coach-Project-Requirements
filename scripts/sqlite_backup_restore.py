"""CLI for SQLite-safe local backup, restore, and validation operations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
for path in (REPO_ROOT, BACKEND_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from sqlite_maintenance import (  # noqa: E402
    DEFAULT_BACKUP_DIR,
    SQLiteMaintenanceError,
    backup_sqlite_database,
    restore_sqlite_database,
    validate_sqlite_database,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Create a SQLite-safe backup using sqlite3 backup().")
    backup.add_argument("--source", help="Source SQLite database path. Defaults to backend settings DB_PATH.")
    backup.add_argument(
        "--target",
        default=str(DEFAULT_BACKUP_DIR / "language_coach-backup.sqlite3"),
        help="Backup destination path.",
    )
    backup.add_argument("--force", action="store_true", help="Allow overwriting an existing target.")
    backup.add_argument("--dry-run", action="store_true", help="Validate inputs without writing the backup file.")

    restore = subparsers.add_parser(
        "restore",
        help="Restore a backup into a target SQLite file, then validate migrations before replacing the target.",
    )
    restore.add_argument("--source", required=True, help="Backup SQLite file to restore from.")
    restore.add_argument("--target", help="Restore destination path. Defaults to backend settings DB_PATH.")
    restore.add_argument("--force", action="store_true", help="Allow replacing an existing target database.")
    restore.add_argument("--dry-run", action="store_true", help="Validate the restore path and migrations without writing.")

    validate = subparsers.add_parser(
        "validate",
        help="Validate that a SQLite file opens cleanly and has all tracked migrations applied.",
    )
    validate.add_argument("--source", required=True, help="SQLite database or backup file to validate.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "backup":
            target = backup_sqlite_database(
                source_path=args.source,
                target_path=args.target,
                force=args.force,
                dry_run=args.dry_run,
            )
            mode = "validated only" if args.dry_run else "created"
            print(f"Backup {mode}: {target}")
            return 0

        if args.command == "restore":
            result = restore_sqlite_database(
                backup_path=args.source,
                target_path=args.target,
                force=args.force,
                dry_run=args.dry_run,
            )
            mode = "validated only" if args.dry_run else "restored"
            print(
                f"Restore {mode}: {result.source_path}\n"
                f"Applied migrations: {len(result.applied_migrations)}\n"
                f"Tables: {', '.join(result.tables[:8])}"
            )
            return 0

        result = validate_sqlite_database(args.source)
        print(
            f"Validated SQLite file: {result.source_path}\n"
            f"Applied migrations: {len(result.applied_migrations)}\n"
            f"Tables: {', '.join(result.tables[:8])}"
        )
        return 0
    except SQLiteMaintenanceError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
