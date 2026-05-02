"""Startup and collection behavior when RAG is disabled or chromadb is unavailable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _blocked_chromadb_env(tmp_path: Path, enable_rag: bool) -> dict[str, str]:
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "\n".join(
            [
                "import builtins",
                "_real_import = builtins.__import__",
                "def _blocked_import(name, globals=None, locals=None, fromlist=(), level=0):",
                "    if name == 'chromadb' or name.startswith('chromadb.'):",
                "        raise ModuleNotFoundError(\"No module named 'chromadb'\")",
                "    return _real_import(name, globals, locals, fromlist, level)",
                "builtins.__import__ = _blocked_import",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    pythonpath_parts = [str(tmp_path), str(BACKEND_DIR)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["ENABLE_RAG"] = "true" if enable_rag else "false"
    return env


def test_import_main_without_chromadb_when_rag_disabled(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=False)
    result = subprocess.run(
        [sys.executable, "-c", "import main; print('import-ok')"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "import-ok" in result.stdout


def test_pytest_collection_succeeds_without_chromadb_when_rag_disabled(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=False)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "tests/test_ai_tools.py", "-q"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "collected" in result.stdout


def test_import_main_when_rag_enabled_but_chromadb_missing_reports_clear_error(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=True)
    code = (
        "import main\n"
        "from routers import imports\n"
        "print(f'ENABLED={imports.rag_manager.enabled}')\n"
        "print(f'ERROR={imports.rag_manager.init_error}')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    enabled_line = next(line for line in lines if line.startswith("ENABLED="))
    error_line = next(line for line in lines if line.startswith("ERROR="))
    assert enabled_line == "ENABLED=False"
    assert "chromadb" in error_line.lower()
