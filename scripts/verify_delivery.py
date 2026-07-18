"""Run the delivery verification command set used by CI and release checks."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import release_file_policy as _release_file_policy  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"
RELEASE_ARCHIVE = REPO_ROOT / "dist" / f"english-japanese-learning-coach-v{VERSION}.zip"
README_PATH = REPO_ROOT / "README.md"
RELEASE_CHECKLIST_PATH = REPO_ROOT / "RELEASE_CHECKLIST.md"
DEMO_GUIDE_PATH = REPO_ROOT / "docs" / "DEMO_GUIDE.md"
REQUIRED_RELEASE_FILES = (
    "README.md",
    "VERSION",
    "backend/.env.example",
    "backend/docker-entrypoint.sh",
    "backend/requirements-core.lock.txt",
    "backend/requirements.txt",
    "backend/main.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "start_backend.sh",
    "start_frontend.sh",
    ".vscode/launch.json",
    ".vscode/tasks.json",
    "docker-compose.yml",
)
PYTHON_VERSION = (3, 11)
NODE_VERSION = "22.18.0"
CORE_LOCK = BACKEND_DIR / "requirements-core.lock.txt"
DEV_LOCK = BACKEND_DIR / "requirements-dev.lock.txt"
RAG_LOCK = BACKEND_DIR / "requirements-rag.lock.txt"
REQUIRED_BACKEND_MODULES = (
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic-settings", "pydantic_settings"),
    ("python-dotenv", "dotenv"),
    ("httpx", "httpx"),
    ("pandas", "pandas"),
    ("openpyxl", "openpyxl"),
    ("redis", "redis"),
    ("reportlab", "reportlab"),
    ("apscheduler", "apscheduler"),
    ("pytz", "pytz"),
    ("websockets", "websockets"),
    ("python-multipart", "multipart"),
    ("pypdf", "pypdf"),
    ("pytest", "pytest"),
    ("pytest-asyncio", "pytest_asyncio"),
    ("pytest-cov", "pytest_cov"),
    ("httpx2", "httpx2"),
    ("pip-tools", "piptools"),
    ("ruff", "ruff"),
    ("mypy", "mypy"),
)

is_excluded_runtime_artifact = _release_file_policy.is_excluded_runtime_artifact
is_safe_env_template = _release_file_policy.is_safe_env_template
is_sensitive_credential_file = _release_file_policy.is_sensitive_credential_file
is_sensitive_env_file = _release_file_policy.is_sensitive_env_file
is_virtualenv_artifact = _release_file_policy.is_virtualenv_artifact

SOURCE_TREE_ARTIFACT_PATHS = (
    REPO_ROOT / ".mypy_cache",
    REPO_ROOT / ".ruff_cache",
    REPO_ROOT / ".pytest_cache",
    REPO_ROOT / ".coverage",
    REPO_ROOT / "coverage",
    REPO_ROOT / ".venv311_hotfix2",
    FRONTEND_DIR / "coverage",
)
SECRET_SCAN_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"OPENAI_API_KEY\s*="),
    re.compile(r"AWS_SECRET_ACCESS_KEY\s*="),
    re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*="),
)


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
            encoded = text.encode(
                getattr(sink, "encoding", "utf-8") or "utf-8",
                errors="replace",
            )
            sink.buffer.write(encoded)
        else:
            sink.write(text.encode("ascii", errors="replace").decode("ascii"))
    sink.flush()


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


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
        raise StepFailed(
            f"Unable to read Node.js version with `{' '.join(command)}`: {stderr or 'unknown error'}"
        )

    version = completed.stdout.strip().removeprefix("v")
    if version != NODE_VERSION:
        raise StepFailed(
            f"Node.js {NODE_VERSION} is required for release verification; found {version or 'unknown'}"
        )


def require_backend_dependencies() -> None:
    missing = [package for package, module in REQUIRED_BACKEND_MODULES if importlib.util.find_spec(module) is None]
    if missing:
        raise StepFailed(
            "Backend dependency preflight failed; missing importable packages: "
            f"{', '.join(missing)}. Install them with "
            "`python -m pip install -r backend/requirements-dev.lock.txt`."
        )

    run_step("Backend dependency consistency preflight", [sys.executable, "-m", "pip", "check"], timeout=300)


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


def is_safe_release_env_template(path: Path) -> bool:
    return is_safe_env_template(path)


def is_excluded_release_env_file(path: Path) -> bool:
    return is_sensitive_env_file(path)


def is_excluded_release_credential_file(path: Path) -> bool:
    return is_sensitive_credential_file(path)


def _current_release_reference_checks() -> tuple[tuple[str, Path, str, str], ...]:
    return (
        ("README current release marker", README_PATH, r"release:current=(?P<version>v[^\s>]+)", f"v{VERSION}"),
        ("README current release line", README_PATH, r"Current release: `(?P<version>v[^`]+)`\.", f"v{VERSION}"),
        (
            "Release checklist changelog reference",
            RELEASE_CHECKLIST_PATH,
            r"Review `CHANGELOG\.md` and confirm the release-facing notes for `(?P<version>v[^`]+)`\.",
            f"v{VERSION}",
        ),
        (
            "Release checklist current release marker",
            RELEASE_CHECKLIST_PATH,
            r"release:current=(?P<version>v[^\s>]+)",
            f"v{VERSION}",
        ),
        (
            "Demo guide current release marker",
            DEMO_GUIDE_PATH,
            r"release:current=(?P<version>v[^\s>]+)",
            f"v{VERSION}",
        ),
        (
            "Demo guide release limitation",
            DEMO_GUIDE_PATH,
            r"not part of the `(?P<version>v[^`]+)` release\.",
            f"v{VERSION}",
        ),
    )


def verify_version_consistency() -> None:
    package_json = json.loads((FRONTEND_DIR / "package.json").read_text(encoding="utf-8"))
    frontend_version = str(package_json.get("version", "")).strip()
    if frontend_version != VERSION:
        raise StepFailed(
            f"Frontend package.json version ({frontend_version or '<missing>'}) "
            f"does not match root VERSION ({VERSION})"
        )
    package_lock = json.loads((FRONTEND_DIR / "package-lock.json").read_text(encoding="utf-8"))
    package_lock_version = str(package_lock.get("version", "")).strip()
    package_lock_root_version = str(package_lock.get("packages", {}).get("", {}).get("version", "")).strip()
    if package_lock_version != VERSION:
        raise StepFailed(
            f"Frontend package-lock.json version ({package_lock_version or '<missing>'}) "
            f"does not match root VERSION ({VERSION})"
        )
    if package_lock_root_version and package_lock_root_version != VERSION:
        raise StepFailed(
            f"Frontend package-lock.json root package version ({package_lock_root_version}) "
            f"does not match root VERSION ({VERSION})"
        )

    for label, path, pattern, expected_version in _current_release_reference_checks():
        content = path.read_text(encoding="utf-8")
        match = re.search(pattern, content)
        if match is None:
            raise StepFailed(f"{label} is missing in {path.relative_to(REPO_ROOT).as_posix()}")
        found_version = match.group("version").strip()
        if found_version != expected_version:
            raise StepFailed(
                f"{label} in {path.relative_to(REPO_ROOT).as_posix()} references {found_version} "
                f"but expected {expected_version}"
            )
    print(f"Verified version consistency: {VERSION}")


def verify_clean_source_tree_artifacts() -> None:
    found: list[str] = []
    for artifact_path in SOURCE_TREE_ARTIFACT_PATHS:
        if artifact_path.exists():
            found.append(artifact_path.relative_to(REPO_ROOT).as_posix())
    if found:
        unique = sorted(set(found))
        raise StepFailed(
            "Generated local artifacts are present in the source tree: " + ", ".join(unique)
        )
    print("Verified clean source tree artifact check.")


def run_standard_verification() -> None:
    require_python_version()
    require_node_version()
    verify_clean_source_tree_artifacts()
    require_backend_dependencies()
    verify_version_consistency()
    run_step(
        "Python dependency locked-install verification",
        [sys.executable, "scripts/python_dependency_locks.py", "check"],
        cwd=REPO_ROOT,
    )
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
    run_step(
        "Pytest backend (excluding RAG and startup isolation)",
        [sys.executable, "-m", "pytest", "-q", "-m", "not rag and not startup_isolation"],
        cwd=REPO_ROOT,
    )
    run_step(
        "Pytest backend startup isolation",
        [sys.executable, "-m", "pytest", "backend/tests/test_rag_disabled_startup.py", "-q"],
        cwd=REPO_ROOT,
    )
    run_step(
        "Pytest backend coverage baseline",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "not rag and not startup_isolation",
            "--cov=backend",
            "--cov-branch",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml:coverage/backend/coverage.xml",
            "--cov-report=json:coverage/backend/coverage.json",
            "--cov-report=html:coverage/backend/html",
            "-W",
            "error::ResourceWarning",
        ],
        cwd=REPO_ROOT,
    )

    npm = npm_command()
    run_step("Frontend install", [npm, "ci"], cwd=FRONTEND_DIR)
    run_audit_step("Frontend production audit", [npm, "audit", "--omit=dev", "--json"])
    run_audit_step("Frontend full audit", [npm, "audit", "--json"])
    run_step("Frontend typecheck", [npm, "run", "typecheck"], cwd=FRONTEND_DIR)
    run_step("Frontend lint", [npm, "run", "lint"], cwd=FRONTEND_DIR)
    run_step("Frontend format check", [npm, "run", "format:check"], cwd=FRONTEND_DIR)
    run_step("Frontend unit tests", [npm, "run", "test:unit"], cwd=FRONTEND_DIR)
    run_step("Frontend component tests", [npm, "run", "test:component"], cwd=FRONTEND_DIR)
    run_step("Frontend coverage baseline", [npm, "run", "test:coverage"], cwd=FRONTEND_DIR)
    run_step("Frontend build", [npm, "run", "build"], cwd=FRONTEND_DIR)
    run_step("Create release zip", [sys.executable, "scripts/make_release_zip.py"])
    verify_release_archive()
    verify_release_archive_secret_patterns()
    verify_release_archive_bootstrap_smoke()


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
        [sys.executable, "-m", "pytest", "backend/tests", "-q", "-m", "rag"],
        cwd=REPO_ROOT,
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
            "Run `cd frontend && npm run e2e:install` to verify E2E locally.",
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

    command = ["pip-audit", "-r", str(CORE_LOCK)]
    if shutil.which("pip-audit") is None:
        command = [sys.executable, "-m", "pip_audit", "-r", str(CORE_LOCK)]
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
    result = subprocess.run(
        ["docker", "compose", "version"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        warn_skipped("Docker compose", "docker compose is not available.")
        return
    run_step("Docker compose config (optional)", ["docker", "compose", "config"], timeout=300)


def verify_release_archive() -> None:
    if not RELEASE_ARCHIVE.exists():
        raise StepFailed(f"Release archive not found: {RELEASE_ARCHIVE}")

    with ZipFile(RELEASE_ARCHIVE) as archive:
        names = archive.namelist()
    name_set = set(names)

    missing_required = [required for required in REQUIRED_RELEASE_FILES if required not in name_set]
    if missing_required:
        raise StepFailed(
            "Release archive is missing required files: " + ", ".join(missing_required)
        )

    for name in sorted(name_set):
        path = Path(name)
        if is_excluded_release_env_file(path):
            raise StepFailed(f"Release archive contains excluded local env file: {name}")
        if is_excluded_release_credential_file(path):
            raise StepFailed(f"Release archive contains excluded credential file: {name}")
        if is_virtualenv_artifact(path):
            raise StepFailed(f"Release archive contains excluded virtual-environment artifact: {name}")
        if is_excluded_runtime_artifact(path):
            raise StepFailed(f"Release archive contains excluded artifact: {name}")

    print(f"Verified release archive contents: {RELEASE_ARCHIVE}")


def verify_release_archive_secret_patterns() -> None:
    if not RELEASE_ARCHIVE.exists():
        raise StepFailed(f"Release archive not found: {RELEASE_ARCHIVE}")

    text_suffixes = {".md", ".txt", ".json", ".toml", ".ini", ".cfg", ".yml", ".yaml", ".py", ".ts", ".js", ".css", ".html", ".sh"}
    with ZipFile(RELEASE_ARCHIVE) as archive:
        for member in archive.infolist():
            if Path(member.filename).suffix.lower() not in text_suffixes:
                continue
            content = archive.read(member).decode("utf-8", errors="ignore")
            for pattern in SECRET_SCAN_PATTERNS:
                if pattern.search(content):
                    raise StepFailed(
                        f"Release archive secret-pattern scan matched {pattern.pattern!r} in {member.filename}"
                    )
    print(f"Verified release archive secret-pattern scan: {RELEASE_ARCHIVE}")


def verify_release_archive_shell_syntax(extract_root: Path) -> None:
    if os.name == "nt":
        print("Skipped shell-script syntax validation on Windows host.")
        return

    bash = shutil.which("bash")
    if bash is None:
        print("Skipped shell-script syntax validation because bash is unavailable.")
        return

    for script_path in (
        extract_root / "start_backend.sh",
        extract_root / "start_frontend.sh",
        extract_root / "backend" / "docker-entrypoint.sh",
    ):
        run_step(
            f"Shell syntax check: {script_path.relative_to(extract_root).as_posix()}",
            [bash, "-n", str(script_path)],
            cwd=extract_root,
            timeout=60,
        )


def verify_release_archive_bootstrap_smoke() -> None:
    if not RELEASE_ARCHIVE.exists():
        raise StepFailed(f"Release archive not found: {RELEASE_ARCHIVE}")

    with TemporaryDirectory(prefix="release-archive-smoke-") as temp_dir:
        extract_root = Path(temp_dir)
        with ZipFile(RELEASE_ARCHIVE) as archive:
            archive.extractall(extract_root)

        missing_paths = [relative for relative in REQUIRED_RELEASE_FILES if not (extract_root / relative).exists()]
        if missing_paths:
            raise StepFailed(
                "Extracted release archive is missing required files: " + ", ".join(missing_paths)
            )

        backend_dir = extract_root / "backend"
        env_template = backend_dir / ".env.example"
        env_copy = backend_dir / ".env"
        if not env_template.exists():
            raise StepFailed("Extracted release archive is missing backend/.env.example")
        shutil.copyfile(env_template, env_copy)
        if not env_copy.exists():
            raise StepFailed("Backend bootstrap smoke could not create backend/.env from backend/.env.example")

        startup_paths = (
            extract_root / "start_backend.sh",
            backend_dir / "requirements.txt",
            backend_dir / "main.py",
            extract_root / "start_frontend.sh",
            extract_root / "frontend" / "package.json",
            extract_root / "frontend" / "package-lock.json",
        )
        unresolved = [str(path.relative_to(extract_root)).replace("\\", "/") for path in startup_paths if not path.exists()]
        if unresolved:
            raise StepFailed(
                "Release archive extraction smoke found unresolved startup paths: " + ", ".join(unresolved)
            )
        verify_release_archive_shell_syntax(extract_root)

    print(f"Verified release archive extraction/bootstrap smoke: {RELEASE_ARCHIVE}")


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
