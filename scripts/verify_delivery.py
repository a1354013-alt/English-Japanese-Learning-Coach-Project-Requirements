"""Run the full release verification command set."""

from __future__ import annotations

import argparse
import importlib.util
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
    run_step("Frontend tests", [npm, "run", "test:unit", "--", "--run"], cwd=FRONTEND_DIR)
    run_step("Frontend build", [npm, "run", "build"], cwd=FRONTEND_DIR)


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode in {"standard", "full"}:
        run_standard_verification()
    if args.mode in {"rag", "full"}:
        run_rag_verification()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
