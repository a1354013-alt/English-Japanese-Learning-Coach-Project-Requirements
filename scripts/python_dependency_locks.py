"""Refresh and verify Python dependency lock files generated for Python 3.11."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
PYTHON_TARGET = (3, 11)


class LockStepFailed(RuntimeError):
    """Raised when lock refresh or verification fails."""


@dataclass(frozen=True)
class LockSpec:
    output_name: str
    input_names: tuple[str, ...]
    description: str


LOCK_SPECS = (
    LockSpec(
        output_name="requirements-core.lock.txt",
        input_names=("requirements.txt",),
        description="core backend runtime",
    ),
    LockSpec(
        output_name="requirements-dev.lock.txt",
        input_names=("requirements.txt", "requirements-dev.txt"),
        description="development and test",
    ),
    LockSpec(
        output_name="requirements-rag.lock.txt",
        input_names=("requirements.txt", "requirements-dev.txt", "requirements-rag.txt"),
        description="optional RAG-enabled development",
    ),
)


def require_python_311() -> None:
    if sys.version_info[:2] != PYTHON_TARGET:
        raise LockStepFailed(
            f"Lock generation targets Python {PYTHON_TARGET[0]}.{PYTHON_TARGET[1]}.x; "
            f"found {sys.version.split()[0]}"
        )


def require_piptools() -> None:
    if shutil.which("pip-compile") is None:
        try:
            __import__("piptools")
        except ModuleNotFoundError as exc:  # pragma: no cover - import failure path
            raise LockStepFailed(
                "pip-tools is not installed. Install backend/requirements-dev.txt before refreshing locks."
            ) from exc


def _compile_lock(spec: LockSpec, output_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        "--no-header",
        "--resolver=backtracking",
        "--output-file",
        str(output_path),
    ]
    command.extend(str(BACKEND_DIR / input_name) for input_name in spec.input_names)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise LockStepFailed(
            f"Failed to compile {spec.output_name}.\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def refresh_locks() -> None:
    require_python_311()
    require_piptools()
    for spec in LOCK_SPECS:
        output_path = BACKEND_DIR / spec.output_name
        _compile_lock(spec, output_path)
        print(f"Refreshed {output_path.relative_to(REPO_ROOT).as_posix()} for {spec.description}.")


def check_locks() -> None:
    require_python_311()
    require_piptools()
    mismatches: list[str] = []
    with tempfile.TemporaryDirectory(prefix="python-lock-check-") as temp_dir:
        temp_root = Path(temp_dir)
        for spec in LOCK_SPECS:
            expected_path = BACKEND_DIR / spec.output_name
            if not expected_path.exists():
                mismatches.append(f"Missing lock file: {expected_path.relative_to(REPO_ROOT).as_posix()}")
                continue

            generated_path = temp_root / spec.output_name
            _compile_lock(spec, generated_path)
            expected = expected_path.read_text(encoding="utf-8")
            generated = generated_path.read_text(encoding="utf-8")
            if expected != generated:
                mismatches.append(
                    f"{expected_path.relative_to(REPO_ROOT).as_posix()} is stale; run "
                    f"`python scripts/python_dependency_locks.py refresh` with Python 3.11.x."
                )

    if mismatches:
        raise LockStepFailed("\n".join(mismatches))
    print("Python dependency lock files are up to date.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("refresh", "check"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "refresh":
            refresh_locks()
        else:
            check_locks()
    except LockStepFailed as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
