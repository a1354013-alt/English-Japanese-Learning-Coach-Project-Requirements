"""Run the delivery verification command set used by CI and release checks."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import os
import subprocess
import sys
import threading
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"
RELEASE_ARCHIVE = REPO_ROOT / "dist" / f"english-japanese-learning-coach-v{VERSION}.zip"
RELEASE_EXCLUDED_PREFIXES = (
    "backend/.playwright-data/",
    "data/chroma_db/",
    "data/audio/",
    "data/exports/",
    "data/lessons/",
    "frontend/test-results/",
    "frontend/playwright-report/",
    "frontend/coverage/",
    "node_modules/",
    "frontend/node_modules/",
)
RELEASE_EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm")


class StepFailed(RuntimeError):
    """Raised when a verification step exits unsuccessfully."""


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _stream_reader(stream, tail: collections.deque[str], sink) -> None:
    try:
        for line in iter(stream.readline, ""):
            tail.append(line.rstrip("\n"))
            _safe_sink_write(sink, line)
    finally:
        stream.close()


def _safe_sink_write(sink, text: str) -> None:
    try:
        sink.write(text)
    except UnicodeEncodeError:
        if hasattr(sink, "buffer"):
            encoded = text.encode(getattr(sink, "encoding", "utf-8") or "utf-8", errors="replace")
            sink.buffer.write(encoded)
        else:
            sink.write(text.encode("ascii", errors="replace").decode("ascii"))
    sink.flush()


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def run_step(
    label: str,
    command: list[str],
    cwd: Path | None = None,
    timeout: int = 900,
) -> None:
    print(f"\n==> {label}")
    print(" ".join(command))
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    process = subprocess.Popen(
        command,
        cwd=cwd or REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    stdout_tail: collections.deque[str] = collections.deque(maxlen=40)
    stderr_tail: collections.deque[str] = collections.deque(maxlen=40)
    stdout_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stdout, stdout_tail, sys.stdout),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stderr, stderr_tail, sys.stderr),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        _print_tail("stdout", stdout_tail)
        _print_tail("stderr", stderr_tail)
        raise StepFailed(f"{label} timed out after {timeout}s") from exc

    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    if return_code != 0:
        _print_tail("stdout", stdout_tail)
        _print_tail("stderr", stderr_tail)
        raise StepFailed(f"{label} failed with exit code {return_code}")


def _print_tail(name: str, tail: collections.deque[str]) -> None:
    if not tail:
        print(f"\n--- {name} tail: <empty> ---", file=sys.stderr)
        return
    print(f"\n--- {name} tail ---", file=sys.stderr)
    for line in tail:
        print(line, file=sys.stderr)


def run_standard_verification() -> None:
    run_step("Compile backend", [sys.executable, "-m", "compileall", "-q", "backend"])
    run_step("Ruff backend/tests", [sys.executable, "-m", "ruff", "check", "backend", "tests"])
    run_step("Mypy backend", [sys.executable, "-m", "mypy", "backend"])
    run_step(
        "Pytest backend (standard, non-RAG)",
        [sys.executable, "-m", "pytest", "backend/tests", "-q", "-m", "not rag"],
    )

    npm = npm_command()
    run_step("Frontend install", [npm, "ci"], cwd=FRONTEND_DIR)
    run_step("Frontend typecheck", [npm, "run", "typecheck"], cwd=FRONTEND_DIR)
    run_step("Frontend lint", [npm, "run", "lint"], cwd=FRONTEND_DIR)
    run_step("Frontend format check", [npm, "run", "format:check"], cwd=FRONTEND_DIR)
    run_step("Frontend tests", [npm, "run", "test:ci"], cwd=FRONTEND_DIR)
    run_step("Frontend build", [npm, "run", "build"], cwd=FRONTEND_DIR)
    run_step("Create release zip", [sys.executable, "scripts/make_release_zip.py"])
    verify_release_archive()


def require_rag_dependencies() -> None:
    if importlib.util.find_spec("chromadb") is None:
        raise SystemExit(
            "RAG verification requires chromadb. Install optional dependencies first with "
            "`pip install -r backend/requirements-rag.txt`."
        )


def run_rag_verification() -> None:
    require_rag_dependencies()
    run_step(
        "Pytest backend (optional RAG)",
        [sys.executable, "-m", "pytest", "backend/tests", "-q", "-m", "rag"],
        cwd=REPO_ROOT,
    )


def verify_release_archive() -> None:
    if not RELEASE_ARCHIVE.exists():
        raise StepFailed(f"Release archive not found: {RELEASE_ARCHIVE}")

    with ZipFile(RELEASE_ARCHIVE) as archive:
        names = archive.namelist()

    for name in names:
        if name.endswith(RELEASE_EXCLUDED_SUFFIXES):
            raise StepFailed(f"Release archive contains excluded runtime DB artifact: {name}")
        if any(name.startswith(prefix) for prefix in RELEASE_EXCLUDED_PREFIXES):
            raise StepFailed(f"Release archive contains excluded artifact: {name}")
        if "/node_modules/" in name:
            raise StepFailed(f"Release archive contains excluded artifact: {name}")

    print(f"Verified release archive contents: {RELEASE_ARCHIVE}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run delivery verification. Standard mode excludes optional RAG tests."
    )
    parser.add_argument(
        "--mode",
        choices=("standard", "rag", "full"),
        default="standard",
        help="standard: default backend/frontend checks; rag: optional RAG tests only; full: standard + rag.",
    )
    parser.add_argument(
        "--include-rag",
        "--rag",
        action="store_true",
        dest="include_rag",
        help="Also run the optional RAG pytest lane after the standard checks.",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdio()
    args = parse_args()
    try:
        if args.mode in {"standard", "full"}:
            run_standard_verification()
        if args.mode in {"rag", "full"} or args.include_rag:
            run_rag_verification()
    except StepFailed as exc:
        print(f"\nVerification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
