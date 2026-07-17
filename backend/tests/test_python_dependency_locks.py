from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_lock_module():
    module_path = REPO_ROOT / "scripts" / "python_dependency_locks.py"
    spec = importlib.util.spec_from_file_location("python_dependency_locks", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load lock script: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


python_dependency_locks = _load_lock_module()


@pytest.mark.parametrize(
    ("text", "expected_fragment"),
    (
        ("# via -r C:/Users/example/project/backend/requirements.txt", "Windows drive path"),
        ("# via -r /home/example/project/backend/requirements.txt", "home-directory path"),
        ("--index-url https://pypi.org/simple", "--index-url directive"),
        ("--trusted-host pypi.example.test", "--trusted-host directive"),
        ("https://token:secret@example.test/simple", "index credentials"),
        ("# via -r /tmp/repo/backend/requirements.txt", "absolute requirements path"),
    ),
)
def test_lock_policy_violations_detect_machine_specific_or_sensitive_content(text, expected_fragment):
    violations = python_dependency_locks._lock_policy_violations(text)

    assert expected_fragment in violations


def test_lock_policy_violations_detect_repository_absolute_paths():
    text = f"# generated on {python_dependency_locks.REPO_ROOT}"

    violations = python_dependency_locks._lock_policy_violations(text)

    assert "repository absolute path" in violations


def test_parse_metadata_extracts_lock_contract():
    metadata = python_dependency_locks._parse_metadata(
        "\n".join(
            (
                "# lock-check: python=3.11",
                "# lock-check: inputs=requirements.txt,requirements-dev.txt",
                "# lock-check: sha256=abc123",
            )
        )
    )

    assert metadata == {
        "python": "3.11",
        "inputs": "requirements.txt,requirements-dev.txt",
        "sha256": "abc123",
    }
