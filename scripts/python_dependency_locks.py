"""Refresh and verify Python dependency lock files generated for Python 3.11."""

from __future__ import annotations

import argparse
import hashlib
import re
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

LOCK_METADATA_PREFIX = "# lock-check: "
LOCK_POLICY_PATTERNS = (
    (re.compile(r"[A-Za-z]:[\\/][^\s]*"), "Windows drive path"),
    (re.compile(r"(?i)(?:^|[^\w])(?:/home/|/users/|\\\\users\\\\|~[\\/])"), "home-directory path"),
    (re.compile(r"--index-url\b"), "--index-url directive"),
    (re.compile(r"--trusted-host\b"), "--trusted-host directive"),
    (re.compile(r"https?://[^/\s:@]+:[^@\s/]+@"), "index credentials"),
    (re.compile(r"(?im)^\s*#\s+via\s+-r\s+[/\\\\]"), "absolute requirements path"),
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


def _input_fingerprint(spec: LockSpec) -> str:
    hasher = hashlib.sha256()
    hasher.update(f"python={PYTHON_TARGET[0]}.{PYTHON_TARGET[1]}".encode("utf-8"))
    hasher.update(f"output={spec.output_name}".encode("utf-8"))
    for input_name in spec.input_names:
        input_path = BACKEND_DIR / input_name
        hasher.update(input_name.encode("utf-8"))
        hasher.update(input_path.read_bytes())
    return hasher.hexdigest()


def _render_lock_with_metadata(spec: LockSpec, compiled_text: str) -> str:
    metadata_lines = (
        f"{LOCK_METADATA_PREFIX}python={PYTHON_TARGET[0]}.{PYTHON_TARGET[1]}",
        f"{LOCK_METADATA_PREFIX}inputs={','.join(spec.input_names)}",
        f"{LOCK_METADATA_PREFIX}sha256={_input_fingerprint(spec)}",
    )
    return "\n".join((*metadata_lines, compiled_text.rstrip(), "")) if compiled_text else "\n".join((*metadata_lines, ""))


def _parse_metadata(lock_text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lock_text.splitlines():
        if not line.startswith(LOCK_METADATA_PREFIX):
            continue
        key, _, value = line[len(LOCK_METADATA_PREFIX) :].partition("=")
        if key and value:
            metadata[key.strip()] = value.strip()
    return metadata


def _lock_policy_violations(lock_text: str) -> list[str]:
    violations: list[str] = []
    repo_path_markers = {
        str(REPO_ROOT).lower(),
        str(BACKEND_DIR).lower(),
        str(REPO_ROOT.as_posix()).lower(),
        str(BACKEND_DIR.as_posix()).lower(),
    }
    lowered = lock_text.lower()
    if any(marker and marker in lowered for marker in repo_path_markers):
        violations.append("repository absolute path")
    for pattern, label in LOCK_POLICY_PATTERNS:
        if pattern.search(lock_text):
            violations.append(label)
    return violations


def _compile_lock(spec: LockSpec, output_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        "--no-header",
        "--no-emit-index-url",
        "--no-emit-trusted-host",
        "--resolver=backtracking",
        "--output-file",
        str(output_path),
    ]
    command.extend(spec.input_names)
    completed = subprocess.run(
        command,
        cwd=BACKEND_DIR,
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
        with tempfile.TemporaryDirectory(prefix="python-lock-refresh-") as temp_dir:
            compiled_path = Path(temp_dir) / spec.output_name
            _compile_lock(spec, compiled_path)
            compiled_text = compiled_path.read_text(encoding="utf-8")
        rendered = _render_lock_with_metadata(spec, compiled_text)
        violations = _lock_policy_violations(rendered)
        if violations:
            joined = ", ".join(sorted(set(violations)))
            raise LockStepFailed(f"Refusing to write {spec.output_name}; lock contains disallowed content: {joined}.")
        output_path.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Refreshed {output_path.relative_to(REPO_ROOT).as_posix()} for {spec.description}.")


def check_locks() -> None:
    require_python_311()
    require_piptools()
    mismatches: list[str] = []
    for spec in LOCK_SPECS:
        expected_path = BACKEND_DIR / spec.output_name
        if not expected_path.exists():
            mismatches.append(f"Missing lock file: {expected_path.relative_to(REPO_ROOT).as_posix()}")
            continue

        expected = expected_path.read_text(encoding="utf-8")
        metadata = _parse_metadata(expected)
        expected_inputs = ",".join(spec.input_names)
        if metadata.get("python") != f"{PYTHON_TARGET[0]}.{PYTHON_TARGET[1]}":
            mismatches.append(
                f"{expected_path.relative_to(REPO_ROOT).as_posix()} is missing the Python 3.11 lock metadata."
            )
        if metadata.get("inputs") != expected_inputs:
            mismatches.append(
                f"{expected_path.relative_to(REPO_ROOT).as_posix()} does not match the expected input set "
                f"({expected_inputs})."
            )
        if metadata.get("sha256") != _input_fingerprint(spec):
            mismatches.append(
                f"{expected_path.relative_to(REPO_ROOT).as_posix()} is stale; run "
                f"`python scripts/python_dependency_locks.py refresh` with Python 3.11.x."
            )
        violations = _lock_policy_violations(expected)
        if violations:
            joined = ", ".join(sorted(set(violations)))
            mismatches.append(
                f"{expected_path.relative_to(REPO_ROOT).as_posix()} contains disallowed lock content: {joined}."
            )

    if mismatches:
        raise LockStepFailed("\n".join(mismatches))
    print("Python dependency lock files are current and portable.")


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
