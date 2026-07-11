"""Shared release-archive policy for sensitive files and local artifacts."""

from __future__ import annotations

from pathlib import Path

SAFE_ENV_TEMPLATE_NAMES = frozenset({".env.example", ".env.sample", ".env.template"})
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        ".cache",
        "node_modules",
        "__pycache__",
        ".coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".playwright-data",
        "cache",
        "caches",
        "coverage",
        "dist",
        "htmlcov",
        "playwright-report",
        "test-results",
    }
)
EXCLUDED_FILE_SUFFIXES = frozenset(
    {
        ".db",
        ".db-shm",
        ".db-wal",
        ".log",
        ".pyc",
        ".pyo",
        ".sqlite",
        ".sqlite3",
    }
)
EXCLUDED_RUNTIME_PREFIXES = (
    ("backend", ".playwright-data"),
    ("backend", ".pytest_cache"),
    ("backend", "data"),
    ("data", "chroma"),
    ("data", "chroma_db"),
    ("data", "audio"),
    ("data", "exports"),
    ("data", "lessons"),
    ("frontend", "dist"),
    ("frontend", "test-results"),
    ("frontend", "playwright-report"),
    ("frontend", "coverage"),
)
SENSITIVE_ENV_EXACT_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        "local.env",
        "production.env",
        "prod.env",
        "secrets.env",
        "secret.env",
    }
)
SENSITIVE_ENV_FRAGMENTS = (
    ".env.",
    ".env-",
    "env.",
    "env-",
)
SENSITIVE_ENV_TOKENS = frozenset(
    {
        "credential",
        "credentials",
        "dev",
        "development",
        "local",
        "private",
        "prod",
        "production",
        "secret",
        "secrets",
        "staging",
        "test",
    }
)


def normalize_relative_path(relative_path: Path | str) -> Path:
    return relative_path if isinstance(relative_path, Path) else Path(relative_path)


def is_safe_env_template(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    return path.name.lower() in SAFE_ENV_TEMPLATE_NAMES


def _path_name_tokens(path_name: str) -> set[str]:
    lowered = path_name.lower()
    tokenized = lowered.replace(".", "_").replace("-", "_")
    return {token for token in tokenized.split("_") if token}


def is_sensitive_env_file(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    name = path.name.lower()
    if is_safe_env_template(path):
        return False
    if name in SENSITIVE_ENV_EXACT_NAMES:
        return True
    if name.startswith(".env") and name != ".envrc":
        return True
    if name.endswith(".env"):
        tokens = _path_name_tokens(name)
        return len(tokens) > 1 and any(token in SENSITIVE_ENV_TOKENS for token in tokens)
    if any(fragment in name for fragment in SENSITIVE_ENV_FRAGMENTS):
        tokens = _path_name_tokens(name)
        if "env" in tokens and any(token in SENSITIVE_ENV_TOKENS for token in tokens):
            return True
    return False


def is_excluded_runtime_artifact(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    parts = path.parts
    if set(parts) & EXCLUDED_DIR_NAMES:
        return True
    if any(part.endswith(".egg-info") for part in parts):
        return True
    if path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True
    return any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_RUNTIME_PREFIXES)


def may_include_in_release_archive(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    return not is_sensitive_env_file(path) and not is_excluded_runtime_artifact(path)
