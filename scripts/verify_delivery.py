"""Run the delivery verification command set used by CI and release checks."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"
RELEASE_ARCHIVE = REPO_ROOT / "dist" / f"english-japanese-learning-coach-v{VERSION}.zip"
RELEASE_EXCLUDED_PREFIXES = (
    "backend/.playwright-data/",
    "data/chroma/",
    "data/chroma_db/",
    "data/audio/",
    "data/exports/",
    "data/lessons/",
    "frontend/dist/",
    "frontend/test-results/",
    "frontend/playwright-report/",
    "frontend/coverage/",
    "node_modules/",
    "frontend/node_modules/",
)
RELEASE_EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm")
PYTHON_VERSION = (3, 11)
NODE_VERSION = "22.18.0"


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


<<<<<<< Updated upstream
def npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"
=======
def require_python_version() -> None:
    current = sys.version_info[:2]
    if current != PYTHON_VERSION:
        raise StepFailed(
            f"Python {PYTHON_VERSION[0]}.{PYTHON_VERSION[1]}.x is required for release verification; "
            f"found {sys.version.split()[0]}"
        )


def require_node_version() -> None:
    command = ["node", "--version"]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise StepFailed(f"Unable to read Node.js version with `{' '.join(command)}`: {stderr or 'unknown error'}")

    version = completed.stdout.strip().removeprefix("v")
    if version != NODE_VERSION:
        raise StepFailed(
            f"Node.js {NODE_VERSION} is required for release verification; found {version or 'unknown'}"
        )
>>>>>>> Stashed changes


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


def run_audit_step(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    print(" ".join(command))
    completed = subprocess.run(
        command,
        cwd=FRONTEND_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.stdout:
        _safe_sink_write(sys.stdout, completed.stdout)
    if completed.stderr:
        _safe_sink_write(sys.stderr, completed.stderr)
    if completed.returncode != 0:
        raise StepFailed(f"{label} failed with exit code {completed.returncode}")

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise StepFailed(f"{label} did not return valid JSON output") from exc

    vulnerabilities = payload.get("metadata", {}).get("vulnerabilities", {})
    total = vulnerabilities.get("total")
    if total not in (0, None):
        raise StepFailed(f"{label} reported unresolved vulnerabilities: {vulnerabilities}")


def _print_tail(name: str, tail: collections.deque[str]) -> None:
    if not tail:
        print(f"\n--- {name} tail: <empty> ---", file=sys.stderr)
        return
    print(f"\n--- {name} tail ---", file=sys.stderr)
    for line in tail:
        print(line, file=sys.stderr)


def warn_skipped(label: str, reason: str) -> None:
    print(f"\n[SKIPPED] {label}: {reason}")


def warn_optional(label: str, reason: str) -> None:
    print(f"\n[WARNING] {label}: {reason}")


def verify_version_consistency() -> None:
    package_json = json.loads((FRONTEND_DIR / "package.json").read_text(encoding="utf-8"))
    frontend_version = str(package_json.get("version", "")).strip()
    if frontend_version != VERSION:
        raise StepFailed(
            f"Frontend package.json version ({frontend_version or '<missing>'}) "
            f"does not match root VERSION ({VERSION})"
        )
    print(f"Verified version consistency: {VERSION}")


def run_standard_verification() -> None:
<<<<<<< Updated upstream
    verify_version_consistency()
    run_step("Compile backend", [sys.executable, "-m", "compileall", "backend"])
    run_step("Ruff backend", [sys.executable, "-m", "ruff", "check", "."], cwd=BACKEND_DIR)
    run_step("Mypy backend", [sys.executable, "-m", "mypy", "."], cwd=BACKEND_DIR)
=======
    require_python_version()
    require_node_version()
    run_step(
        "Compile backend",
        [sys.executable, "-m", "compileall", "backend", "scripts", "tests"],
        cwd=REPO_ROOT,
    )
    run_step(
        "Ruff backend",
        [sys.executable, "-m", "ruff", "check", "backend", "scripts", "tests"],
        cwd=REPO_ROOT,
    )
    run_step("Mypy backend", [sys.executable, "-m", "mypy", "backend"], cwd=REPO_ROOT)
>>>>>>> Stashed changes
    run_step(
        "Pytest backend",
        [sys.executable, "-m", "pytest"],
        cwd=REPO_ROOT,
    )

    npm = npm_command()
    run_step("Frontend install", [npm, "ci"], cwd=FRONTEND_DIR)
    run_audit_step("Frontend production audit", [npm, "audit", "--omit=dev", "--json"])
    run_audit_step("Frontend full audit", [npm, "audit", "--json"])
    run_step("Frontend typecheck", [npm, "run", "typecheck"], cwd=FRONTEND_DIR)
    run_step("Frontend lint", [npm, "run", "lint"], cwd=FRONTEND_DIR)
    run_step("Frontend format check", [npm, "run", "format:check"], cwd=FRONTEND_DIR)
    run_step("Frontend tests", [npm, "run", "test:ci"], cwd=FRONTEND_DIR)
    run_step("Frontend build", [npm, "run", "build"], cwd=FRONTEND_DIR)
    run_step("Frontend production dependency audit", [npm, "audit", "--omit=dev"], cwd=FRONTEND_DIR)
    run_step("Frontend full dependency audit", [npm, "audit"], cwd=FRONTEND_DIR)
    run_step("Create release zip", [sys.executable, "scripts/make_release_zip.py"])
    verify_release_archive()


def require_rag_dependencies() -> None:
    if importlib.util.find_spec("chromadb") is None:
        raise StepFailed(
            "RAG verification requires `chromadb`. Install `backend/requirements-rag.txt` before running "
            "`scripts/verify_delivery.py --include-rag`, `--mode rag`, or `--full`."
        )


def run_rag_verification() -> None:
    require_rag_dependencies()
    run_step(
        "Pytest backend (optional RAG)",
        [sys.executable, "-m", "pytest", "tests", "-q", "-m", "rag"],
        cwd=BACKEND_DIR,
    )


def run_optional_advisory_checks() -> None:
    print(
        "\n==> Optional advisory checks\n"
        "These checks are environment-dependent. Skips here are reported explicitly and do not "
        "change the standard delivery gate result."
    )
    run_optional_playwright_check()
    run_optional_pip_audit_check()
    run_optional_docker_check()


def run_optional_playwright_check() -> None:
    npx = npx_command()
    if shutil.which(npx) is None:
        warn_skipped("Playwright E2E", "npx is not available.")
        return

    browser_root = (
        Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""))
        if os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        else _default_playwright_browser_root()
    )
    has_chromium = browser_root.exists() and any(browser_root.glob("chromium*"))
    if not has_chromium:
        warn_skipped(
            "Playwright E2E",
            f"Chromium browser executable is not installed under {browser_root}. "
            "Run `cd frontend && npx playwright install --with-deps chromium` to verify E2E locally.",
        )
        return
    run_step(
        "Playwright mocked E2E (optional)",
        [npm_command(), "run", "test:e2e", "--", "--project=chromium"],
        cwd=FRONTEND_DIR,
        timeout=900,
    )


def _default_playwright_browser_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def run_optional_pip_audit_check() -> None:
    if shutil.which("pip-audit") is None and importlib.util.find_spec("pip_audit") is None:
        warn_skipped("pip-audit", "pip-audit is not installed.")
        return

    command = ["pip-audit", "-r", str(BACKEND_DIR / "requirements.txt")]
    if shutil.which("pip-audit") is None:
        command = [sys.executable, "-m", "pip_audit", "-r", str(BACKEND_DIR / "requirements.txt")]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=300)
    if result.returncode != 0:
        warn_optional(
            "pip-audit",
            "audit could not complete or reported findings; standard delivery does not depend on this optional gate.",
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return
    print("[OK] pip-audit")


def run_optional_docker_check() -> None:
    if shutil.which("docker") is None:
        warn_skipped("Docker compose", "docker is not available.")
        return
    result = subprocess.run(["docker", "compose", "version"], cwd=REPO_ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        warn_skipped("Docker compose", "docker compose is not available.")
        return
    run_step("Docker compose config (optional)", ["docker", "compose", "config"], timeout=300)


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
        description="Run delivery verification. Standard mode excludes optional environment-dependent checks."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run standard delivery plus optional advisory checks and the optional RAG lane when available.",
    )
    parser.add_argument(
        "--mode",
        choices=("standard", "rag", "full"),
        default="standard",
        help="standard: backend/frontend/release gate; rag: optional RAG tests only; full: standard + optional advisory checks + rag.",
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
    selected_mode = "full" if args.full else args.mode
    try:
        if selected_mode in {"standard", "full"}:
            run_standard_verification()
        if selected_mode == "full":
            run_optional_advisory_checks()
        if selected_mode in {"rag", "full"} or args.include_rag:
            run_rag_verification()
    except StepFailed as exc:
        print(f"\nVerification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
