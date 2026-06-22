"""Startup and collection behavior when RAG is disabled or chromadb is unavailable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
SUBPROCESS_TIMEOUT_SECONDS = 60
pytestmark = pytest.mark.startup_isolation


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
    for key in list(env):
        if key.startswith("PYTEST_"):
            env.pop(key, None)
    pythonpath_parts = [str(tmp_path), str(BACKEND_DIR)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["ENABLE_RAG"] = "true" if enable_rag else "false"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _run_subprocess(command: list[str], *, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_output(exc.stdout)
        stderr = _decode_output(exc.stderr)
        raise AssertionError(
            "Subprocess timed out.\n"
            f"Command: {' '.join(command)}\n"
            f"Timeout: {timeout}s\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        ) from exc

    if result.returncode != 0:
        raise AssertionError(
            "Subprocess failed.\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def _decode_output(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output or ""


def test_import_main_without_chromadb_when_rag_disabled(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=False)
    result = _run_subprocess(
        [sys.executable, "-c", "import main; print('import-ok')"],
        env=env,
        timeout=30,
    )

    assert "import-ok" in result.stdout


def test_pytest_collection_succeeds_without_chromadb_when_rag_disabled(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=False)
    result = _run_subprocess(
        [sys.executable, "-m", "pytest", "--collect-only", "tests/test_ai_tools.py", "-q"],
        env=env,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert "collected" in result.stdout


def test_import_main_when_rag_enabled_but_chromadb_missing_reports_clear_error(tmp_path):
    env = _blocked_chromadb_env(tmp_path, enable_rag=True)
    code = (
        "import main\n"
        "from routers import imports\n"
        "print(f'ENABLED={imports.rag_manager.enabled}')\n"
        "print(f'ERROR={imports.rag_manager.init_error}')\n"
    )
    result = _run_subprocess([sys.executable, "-c", code], env=env, timeout=30)

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    enabled_line = next(line for line in lines if line.startswith("ENABLED="))
    error_line = next(line for line in lines if line.startswith("ERROR="))
    assert enabled_line == "ENABLED=False"
    assert "chromadb" in error_line.lower()
