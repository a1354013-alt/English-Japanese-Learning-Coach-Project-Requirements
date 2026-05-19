"""Run the full release verification command set."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def run_step(label: str, command: list[str], cwd: Path | None = None) -> None:
    print(f"\n==> {label}")
    print(" ".join(command))
    subprocess.run(command, cwd=cwd or REPO_ROOT, check=True)


def main() -> int:
    run_step("Compile backend", [sys.executable, "-m", "compileall", "-q", "backend"])
    run_step("Ruff backend/tests", ["ruff", "check", "backend", "tests"])
    run_step("Mypy backend", ["mypy", "backend"])
    run_step("Pytest backend", ["pytest", "backend/tests", "-q"])

    npm = npm_command()
    run_step("Frontend install", [npm, "ci"], cwd=FRONTEND_DIR)
    run_step("Frontend typecheck", [npm, "run", "typecheck"], cwd=FRONTEND_DIR)
    run_step("Frontend lint", [npm, "run", "lint"], cwd=FRONTEND_DIR)
    run_step("Frontend format check", [npm, "run", "format:check"], cwd=FRONTEND_DIR)
    run_step("Frontend tests", [npm, "run", "test:ci"], cwd=FRONTEND_DIR)
    run_step("Frontend build", [npm, "run", "build"], cwd=FRONTEND_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
