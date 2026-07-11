"""Shared release-archive policy for sensitive files and local artifacts."""

from __future__ import annotations

from pathlib import Path

SAFE_ENV_TEMPLATE_NAMES = frozenset({".env.example", ".env.sample", ".env.template"})
SAFE_SOURCE_ENV_DECLARATION_NAMES = frozenset({"env.d.ts"})
SENSITIVE_CREDENTIAL_EXACT_NAMES = frozenset(
    {
        ".netrc",
        ".npmrc",
        ".pypirc",
        "id_ed25519",
        "id_rsa",
        "service-account.json",
    }
)
SENSITIVE_CREDENTIAL_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".direnv",
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


def normalize_relative_path(relative_path: Path | str) -> Path:
    return relative_path if isinstance(relative_path, Path) else Path(relative_path)


def is_safe_env_template(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    return path.name.lower() in SAFE_ENV_TEMPLATE_NAMES


def is_safe_source_env_declaration(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    return path.name.lower() in SAFE_SOURCE_ENV_DECLARATION_NAMES


def _is_env_stage_variant(path_name: str) -> bool:
    if path_name.startswith("env."):
        return path_name[4:] not in SAFE_SOURCE_ENV_DECLARATION_NAMES
    if path_name.startswith("env-"):
        return True
    return False


def is_sensitive_env_file(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    name = path.name.lower()
    if is_safe_env_template(path) or is_safe_source_env_declaration(path):
        return False
    if name == ".envrc":
        return True
    if name.startswith(".env"):
        return True
    return (
        name.endswith(".env")
        or ".env." in name
        or ".env-" in name
        or _is_env_stage_variant(name)
    )


def is_sensitive_credential_file(relative_path: Path | str) -> bool:
    path = normalize_relative_path(relative_path)
    name = path.name.lower()
    return name in SENSITIVE_CREDENTIAL_EXACT_NAMES or path.suffix.lower() in SENSITIVE_CREDENTIAL_SUFFIXES


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
    return (
        not is_sensitive_env_file(path)
        and not is_sensitive_credential_file(path)
        and not is_excluded_runtime_artifact(path)
    )
