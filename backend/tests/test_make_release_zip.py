"""Release zip should exclude sensitive env files and runtime artifacts."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFE_ENV_TEMPLATES = (
    ".env.example",
    ".env.sample",
    ".env.template",
)
SENSITIVE_CREDENTIAL_CASES = (
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "service-account.json",
    "keys/private.pem",
    "keys/private.key",
    "keys/client.p12",
    "keys/client.pfx",
)
SENSITIVE_ENV_CASES = (
    ".env",
    ".envrc",
    ".env.local",
    ".ENV.PRODUCTION.LOCAL",
    "app.env",
    "config.env",
    "qa.env",
    "uat.env",
    "env.qa",
    "env.uat",
    "env.production",
    "env.staging",
    "env.local",
    "frontend/service.env.qa",
    "backend/config.env",
    "backend/.env.backup",
    "backend/.env.vault",
    "service.env.uat",
)
REQUIRED_RELEASE_FILES = (
    "README.md",
    "VERSION",
    "backend/.env.example",
    "backend/docker-entrypoint.sh",
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


def _load_module(module_name: str, relative_path: str) -> ModuleType:
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load release script: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_file_policy = _load_module("release_file_policy", "scripts/release_file_policy.py")
make_release_zip = _load_module("make_release_zip", "scripts/make_release_zip.py")
verify_delivery = _load_module("verify_delivery", "scripts/verify_delivery.py")


def _write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def assert_directory_missing_or_empty(path: Path) -> None:
    assert not path.exists() or list(path.iterdir()) == []


def _seed_release_repo(repo_root: Path) -> None:
    _write_text(repo_root / "VERSION", "9.9.9")
    _write_text(repo_root / "README.md", "keep me")
    _write_text(repo_root / "start_backend.sh", "#!/usr/bin/env bash\ncd backend\ncp .env.example .env\n")
    _write_text(repo_root / "start_frontend.sh", "#!/usr/bin/env bash\ncd frontend\nnpm ci\n")
    _write_text(repo_root / "docker-compose.yml", "services: {}\n")
    _write_text(repo_root / ".vscode" / "launch.json", "{}")
    _write_text(repo_root / ".vscode" / "tasks.json", "{}")
    _write_text(repo_root / ".env.example", "ROOT_TEMPLATE=1\n")
    _write_text(repo_root / ".env.sample", "ROOT_SAMPLE=1\n")
    _write_text(repo_root / ".env.template", "ROOT_TEMPLATE=1\n")
    _write_text(repo_root / "backend" / ".env.example", "BACKEND_TEMPLATE=1\n")
    _write_text(repo_root / "backend" / "docker-entrypoint.sh", "#!/bin/sh\nset -eu\nexec \"$@\"\n")
    _write_text(repo_root / "backend" / "requirements.txt", "fastapi\n")
    _write_text(repo_root / "backend" / "main.py", "app = object()\n")
    _write_text(repo_root / "frontend" / "package.json", "{\"name\":\"frontend\"}")
    _write_text(repo_root / "frontend" / "package-lock.json", "{\"name\":\"frontend\",\"lockfileVersion\":3}")
    _write_text(repo_root / "frontend" / "src" / "env.d.ts", "/// <reference types=\"vite/client\" />\n")
    _write_text(repo_root / "data" / ".gitkeep", "")


def _seed_runtime_artifacts(repo_root: Path) -> None:
    _write_text(repo_root / "backend" / "api.log", "log")
    _write_text(repo_root / "backend" / "data" / "runtime.json", "{}")
    _write_text(repo_root / "data" / "language_coach.db", "db")
    _write_text(repo_root / "data" / "language_coach.sqlite", "db")
    _write_text(repo_root / "data" / "language_coach.sqlite3", "db")
    _write_text(repo_root / "data" / "language_coach.db-wal", "wal")
    _write_text(repo_root / "data" / "language_coach.db-shm", "shm")
    _write_text(repo_root / "data" / "chroma" / "index.bin", "vector")
    _write_text(repo_root / "data" / "chroma_db" / "index.bin", "vector")
    _write_text(repo_root / "data" / "audio" / "sample.wav", "audio")
    _write_text(repo_root / "data" / "exports" / "lesson.pdf", "pdf")
    _write_text(repo_root / "data" / "lessons" / "lesson.json", "{}")
    _write_text(repo_root / "frontend" / "test-results" / "result.txt", "test")
    _write_text(repo_root / "frontend" / "dist" / "index.html", "build")
    _write_text(repo_root / "frontend" / "playwright-report" / "index.html", "report")
    _write_text(repo_root / "frontend" / "coverage" / "lcov.info", "coverage")
    _write_text(repo_root / "frontend" / "node_modules" / "dep.js", "dep")
    _write_text(repo_root / ".direnv" / "python-version", "3.11")
    _write_text(repo_root / ".cache" / "tool" / "state", "cache")
    _write_text(repo_root / "htmlcov" / "index.html", "coverage")
    _write_text(repo_root / "coverage" / "coverage.xml", "coverage")
    _write_text(repo_root / "backend" / ".playwright-data" / "language_coach.db", "db")
    _write_text(repo_root / "backend" / ".pytest_cache" / "state", "cache")
    _write_text(repo_root / "__pycache__" / "module.pyc", "pyc")


def _write_release_archive(archive_path: Path, extra_files: dict[str, str] | None = None) -> None:
    extra_files = extra_files or {}
    with ZipFile(archive_path, "w") as archive:
        for name in REQUIRED_RELEASE_FILES:
            if name == "README.md":
                archive.writestr(name, "keep")
            elif name == "VERSION":
                archive.writestr(name, "9.9.9")
            elif name == "backend/.env.example":
                archive.writestr(name, "BACKEND_TEMPLATE=1\n")
            elif name == "backend/docker-entrypoint.sh":
                archive.writestr(name, "#!/bin/sh\nset -eu\nexec \"$@\"\n")
            elif name == "backend/requirements.txt":
                archive.writestr(name, "fastapi\n")
            elif name == "backend/main.py":
                archive.writestr(name, "app = object()\n")
            elif name == "frontend/package.json":
                archive.writestr(name, "{\"name\":\"frontend\"}")
            elif name == "frontend/package-lock.json":
                archive.writestr(name, "{\"name\":\"frontend\",\"lockfileVersion\":3}")
            elif name == "start_backend.sh":
                archive.writestr(name, "#!/usr/bin/env bash\ncd backend\ncp .env.example .env\n")
            elif name == "start_frontend.sh":
                archive.writestr(name, "#!/usr/bin/env bash\ncd frontend\nnpm ci\n")
            elif name == ".vscode/launch.json":
                archive.writestr(name, "{}")
            elif name == ".vscode/tasks.json":
                archive.writestr(name, "{}")
            elif name == "docker-compose.yml":
                archive.writestr(name, "services: {}\n")
        archive.writestr("frontend/src/env.d.ts", "/// <reference types=\"vite/client\" />\n")
        for name, content in extra_files.items():
            archive.writestr(name, content)


def test_release_zip_excludes_sensitive_env_files_and_runtime_artifacts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    _seed_release_repo(repo_root)
    _seed_runtime_artifacts(repo_root)

    for relative_path in SENSITIVE_ENV_CASES:
        _write_text(repo_root / relative_path, "SECRET=1\n")
    for relative_path in SENSITIVE_CREDENTIAL_CASES:
        _write_text(repo_root / relative_path, "PRIVATE=1\n")

    dummy_secret_name = "backend/.env.staging.local"
    dummy_secret_value = "DUMMY_RELEASE_SECRET=super-secret-value-12345\n"
    _write_text(repo_root / dummy_secret_name, dummy_secret_value)

    monkeypatch.setattr(make_release_zip, "REPO_ROOT", repo_root)
    monkeypatch.setattr(make_release_zip, "DIST_DIR", dist_dir)
    monkeypatch.setattr(make_release_zip, "VERSION", "9.9.9")

    assert make_release_zip.main() == 0

    archive_path = dist_dir / "english-japanese-learning-coach-v9.9.9.zip"
    assert archive_path.exists()
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    for required_name in REQUIRED_RELEASE_FILES:
        assert required_name in names
    for safe_template in SAFE_ENV_TEMPLATES:
        assert safe_template in names
    assert "data/.gitkeep" in names
    assert "frontend/src/env.d.ts" in names

    for relative_path in SENSITIVE_ENV_CASES + (dummy_secret_name,):
        assert relative_path not in names
    for relative_path in SENSITIVE_CREDENTIAL_CASES:
        assert relative_path not in names
    assert "backend/api.log" not in names
    assert "data/language_coach.db" not in names
    assert "data/language_coach.sqlite" not in names
    assert "data/language_coach.sqlite3" not in names
    assert "data/language_coach.db-wal" not in names
    assert "data/language_coach.db-shm" not in names
    assert not any(name.startswith("backend/data/") for name in names)
    assert not any(name.startswith("data/chroma/") for name in names)
    assert not any(name.startswith("data/chroma_db/") for name in names)
    assert not any(name.startswith("data/audio/") for name in names)
    assert not any(name.startswith("data/exports/") for name in names)
    assert not any(name.startswith("data/lessons/") for name in names)
    assert not any(name.startswith("frontend/dist/") for name in names)
    assert not any(name.startswith("frontend/test-results/") for name in names)
    assert not any(name.startswith("frontend/playwright-report/") for name in names)
    assert not any(name.startswith("frontend/coverage/") for name in names)
    assert not any(name.startswith("frontend/node_modules/") for name in names)
    assert not any(name.startswith(".direnv/") for name in names)
    assert not any(name.startswith(".cache/") for name in names)
    assert not any(name.startswith("htmlcov/") for name in names)
    assert not any(name.startswith("coverage/") for name in names)
    assert not any(name.startswith("backend/.playwright-data/") for name in names)
    assert dummy_secret_name.encode("utf-8") not in archive_path.read_bytes()
    assert dummy_secret_value.encode("utf-8") not in archive_path.read_bytes()


@pytest.mark.parametrize("relative_path", SENSITIVE_ENV_CASES)
def test_shared_policy_marks_sensitive_env_files(relative_path):
    assert release_file_policy.is_sensitive_env_file(Path(relative_path))
    assert make_release_zip.should_skip(Path(relative_path))
    assert verify_delivery.is_excluded_release_env_file(Path(relative_path))


@pytest.mark.parametrize("relative_path", SENSITIVE_CREDENTIAL_CASES)
def test_shared_policy_marks_sensitive_credential_files(relative_path):
    assert release_file_policy.is_sensitive_credential_file(Path(relative_path))
    assert make_release_zip.should_skip(Path(relative_path))
    assert verify_delivery.is_excluded_release_credential_file(Path(relative_path))


@pytest.mark.parametrize(
    "relative_path",
    SAFE_ENV_TEMPLATES + ("backend/.env.example", "frontend/src/env.d.ts"),
)
def test_shared_policy_preserves_safe_templates(relative_path):
    if relative_path.endswith("env.d.ts"):
        assert release_file_policy.is_safe_source_env_declaration(Path(relative_path))
    else:
        assert release_file_policy.is_safe_env_template(Path(relative_path))
    assert not release_file_policy.is_sensitive_env_file(Path(relative_path))
    assert not make_release_zip.should_skip(Path(relative_path))
    assert not verify_delivery.is_excluded_release_env_file(Path(relative_path))


def test_shared_policy_covers_required_artifact_patterns():
    assert make_release_zip.should_skip(Path("backend/api.log"))
    assert make_release_zip.should_skip(Path("data/language_coach.db"))
    assert make_release_zip.should_skip(Path("data/language_coach.sqlite"))
    assert make_release_zip.should_skip(Path("data/language_coach.sqlite3"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-wal"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-shm"))
    assert make_release_zip.should_skip(Path("data/chroma/index.bin"))
    assert make_release_zip.should_skip(Path("data/chroma_db/index.bin"))
    assert make_release_zip.should_skip(Path("frontend/dist/index.html"))
    assert make_release_zip.should_skip(Path("frontend/test-results/index.html"))
    assert make_release_zip.should_skip(Path("frontend/playwright-report/index.html"))
    assert make_release_zip.should_skip(Path("frontend/node_modules/pkg/index.js"))
    assert make_release_zip.should_skip(Path(".direnv/python-version"))
    assert make_release_zip.should_skip(Path(".cache/tool/state"))
    assert make_release_zip.should_skip(Path("htmlcov/index.html"))
    assert make_release_zip.should_skip(Path("coverage/coverage.xml"))
    assert make_release_zip.should_skip(Path("backend/data/runtime.json"))
    assert make_release_zip.should_skip(Path("backend/.playwright-data/language_coach.db"))
    assert make_release_zip.should_skip(Path("backend/.pytest_cache/state"))
    assert make_release_zip.should_skip(Path("__pycache__/module.pyc"))
    assert not make_release_zip.should_skip(Path("data/.gitkeep"))


@pytest.mark.parametrize("sensitive_name", SENSITIVE_ENV_CASES)
def test_verify_release_archive_rejects_sensitive_env_files(tmp_path, monkeypatch, sensitive_name):
    archive_path = tmp_path / "release.zip"
    secret_value = "SUPER_SECRET_RELEASE_VALUE=do-not-print-me\n"
    _write_release_archive(archive_path, {sensitive_name: secret_value})

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    with pytest.raises(verify_delivery.StepFailed, match="excluded local env file") as exc_info:
        verify_delivery.verify_release_archive()
    assert sensitive_name in str(exc_info.value)
    assert secret_value not in str(exc_info.value)


@pytest.mark.parametrize("sensitive_name", SENSITIVE_CREDENTIAL_CASES)
def test_verify_release_archive_rejects_sensitive_credential_files(tmp_path, monkeypatch, sensitive_name):
    archive_path = tmp_path / "release.zip"
    secret_value = "PRIVATE_KEY_MATERIAL=do-not-print-me\n"
    _write_release_archive(archive_path, {sensitive_name: secret_value})

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    with pytest.raises(verify_delivery.StepFailed, match="excluded credential file") as exc_info:
        verify_delivery.verify_release_archive()
    assert sensitive_name in str(exc_info.value)
    assert secret_value not in str(exc_info.value)


def test_verify_release_archive_rejects_missing_required_files(tmp_path, monkeypatch):
    archive_path = tmp_path / "release.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("README.md", "keep")
        archive.writestr("VERSION", "9.9.9")

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    with pytest.raises(verify_delivery.StepFailed, match="missing required files"):
        verify_delivery.verify_release_archive()


def test_release_archive_extraction_bootstrap_smoke(tmp_path, monkeypatch):
    archive_path = tmp_path / "release.zip"
    _write_release_archive(archive_path)

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    verify_delivery.verify_release_archive()
    verify_delivery.verify_release_archive_bootstrap_smoke()

    extract_root = tmp_path / "manual-extract"
    with ZipFile(archive_path) as archive:
        archive.extractall(extract_root)
    shutil.copyfile(
        extract_root / "backend" / ".env.example",
        extract_root / "backend" / ".env",
    )
    assert (extract_root / "backend" / ".env").read_text(encoding="utf-8") == "BACKEND_TEMPLATE=1\n"
    assert (extract_root / "backend" / "main.py").exists()
    assert (extract_root / "frontend" / "src" / "env.d.ts").exists()


def test_shell_syntax_validation_runs_when_supported(tmp_path, monkeypatch):
    extract_root = tmp_path / "extract"
    for relative_path in (
        "start_backend.sh",
        "start_frontend.sh",
        "backend/docker-entrypoint.sh",
    ):
        _write_text(extract_root / relative_path, "#!/bin/sh\nexit 0\n")

    recorded_calls: list[tuple[str, list[str], Path | None, int]] = []

    def _record_run_step(label: str, command: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
        recorded_calls.append((label, command, cwd, timeout))

    monkeypatch.setattr(verify_delivery.os, "name", "posix", raising=False)
    monkeypatch.setattr(verify_delivery.shutil, "which", lambda name: "/bin/bash" if name == "bash" else None)
    monkeypatch.setattr(verify_delivery, "run_step", _record_run_step)

    verify_delivery.verify_release_archive_shell_syntax(extract_root)

    assert [call[0] for call in recorded_calls] == [
        "Shell syntax check: start_backend.sh",
        "Shell syntax check: start_frontend.sh",
        "Shell syntax check: backend/docker-entrypoint.sh",
    ]
    assert all(call[1][0:2] == ["/bin/bash", "-n"] for call in recorded_calls)
    assert all(call[2] == extract_root for call in recorded_calls)


def _seed_symlink_repo(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path, Path]:
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    outside_root = tmp_path / "outside"
    _seed_release_repo(repo_root)
    outside_root.mkdir(parents=True, exist_ok=True)
    target = outside_root / "secret.txt"
    target.write_text("TOP_SECRET_VALUE=never-package-me\n", encoding="utf-8")
    symlink_path = repo_root / "backend" / "linked-secret.txt"

    try:
        symlink_path.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Symlink creation is unavailable on this host: {exc}")

    monkeypatch.setattr(make_release_zip, "REPO_ROOT", repo_root)
    monkeypatch.setattr(make_release_zip, "DIST_DIR", dist_dir)
    monkeypatch.setattr(make_release_zip, "VERSION", "9.9.9")
    return repo_root, dist_dir, target, symlink_path


def test_make_release_zip_rejects_includable_symlink(tmp_path, monkeypatch):
    _repo_root, dist_dir, target, _symlink_path = _seed_symlink_repo(tmp_path, monkeypatch)

    with pytest.raises(make_release_zip.ReleasePackagingError, match="backend/linked-secret.txt") as exc_info:
        make_release_zip.build_release_archive()

    assert str(target) not in str(exc_info.value)
    assert "TOP_SECRET_VALUE=never-package-me" not in str(exc_info.value)
    assert not (dist_dir / "english-japanese-learning-coach-v9.9.9.zip").exists()


def test_make_release_zip_failure_leaves_no_new_final_or_temp_archive(tmp_path, monkeypatch):
    _repo_root, dist_dir, _target, _symlink_path = _seed_symlink_repo(tmp_path, monkeypatch)

    with pytest.raises(make_release_zip.ReleasePackagingError):
        make_release_zip.build_release_archive()

    assert_directory_missing_or_empty(dist_dir)


def test_make_release_zip_failure_preserves_previous_archive_bytes(tmp_path, monkeypatch):
    repo_root, dist_dir, _target, _symlink_path = _seed_symlink_repo(tmp_path, monkeypatch)
    archive_path = dist_dir / "english-japanese-learning-coach-v9.9.9.zip"
    dist_dir.mkdir(parents=True, exist_ok=True)
    original_bytes = b"previous-good-archive"
    archive_path.write_bytes(original_bytes)

    with pytest.raises(make_release_zip.ReleasePackagingError):
        make_release_zip.build_release_archive()

    assert archive_path.read_bytes() == original_bytes
    assert [path.name for path in dist_dir.iterdir()] == [archive_path.name]


def test_make_release_zip_success_replaces_previous_archive_atomically(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    _seed_release_repo(repo_root)
    monkeypatch.setattr(make_release_zip, "REPO_ROOT", repo_root)
    monkeypatch.setattr(make_release_zip, "DIST_DIR", dist_dir)
    monkeypatch.setattr(make_release_zip, "VERSION", "9.9.9")

    dist_dir.mkdir(parents=True, exist_ok=True)
    archive_path = dist_dir / "english-japanese-learning-coach-v9.9.9.zip"
    archive_path.write_bytes(b"old-archive")
    original_bytes = archive_path.read_bytes()

    _write_text(repo_root / "README.md", "new content for replacement")
    built_path = make_release_zip.build_release_archive()

    assert built_path == archive_path
    assert archive_path.read_bytes() != original_bytes
    with ZipFile(archive_path) as archive:
        assert archive.read("README.md").decode("utf-8") == "new content for replacement"
    assert [path.name for path in dist_dir.iterdir()] == [archive_path.name]


def test_make_release_zip_main_redacts_symlink_target_from_output(tmp_path, monkeypatch, capsys):
    _repo_root, dist_dir, target, _symlink_path = _seed_symlink_repo(tmp_path, monkeypatch)

    assert make_release_zip.main() == 1

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    assert "backend/linked-secret.txt" in combined_output
    assert str(target) not in combined_output
    assert "TOP_SECRET_VALUE=never-package-me" not in combined_output
    assert not (dist_dir / "english-japanese-learning-coach-v9.9.9.zip").exists()
    assert_directory_missing_or_empty(dist_dir)


def _write_version_reference_files(root: Path, version: str) -> tuple[Path, Path, Path, Path]:
    frontend_dir = root / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    package_json_path = frontend_dir / "package.json"
    package_json_path.write_text(
        f'{{"name":"frontend","version":"{version}"}}',
        encoding="utf-8",
    )

    readme_path = root / "README.md"
    readme_path.write_text(
        "\n".join(
            (
                f"Current release: `v{version}`.",
                f"Version `{version}` turns the additive learning-intelligence work into a coherent adaptive study flow:",
            )
        ),
        encoding="utf-8",
    )

    checklist_path = root / "RELEASE_CHECKLIST.md"
    checklist_path.write_text(
        "\n".join(
            (
                f"- Review `CHANGELOG.md` and confirm the release-facing notes for `v{version}`.",
                f"- Update root `VERSION`; it is the source of truth for backend app metadata and release archives. Keep `frontend/package.json` in sync at `{version}`; `scripts/verify_delivery.py` checks this.",
            )
        ),
        encoding="utf-8",
    )

    demo_guide_path = root / "docs" / "DEMO_GUIDE.md"
    demo_guide_path.parent.mkdir(parents=True, exist_ok=True)
    demo_guide_path.write_text(
        "\n".join(
            (
                f"Use this guide when you want to present the `v{version}` Adaptive Learning project as a polished portfolio demo instead of only a developer handoff.",
                f"- Real recording and speech comparison are not part of the `v{version}` release.",
            )
        ),
        encoding="utf-8",
    )
    return package_json_path, readme_path, checklist_path, demo_guide_path


@pytest.mark.parametrize(
    ("stale_path_name", "old_text", "new_text"),
    (
        ("README.md", "Current release: `v9.9.9`.", "Current release: `v9.9.8`."),
        (
            "RELEASE_CHECKLIST.md",
            "- Review `CHANGELOG.md` and confirm the release-facing notes for `v9.9.9`.",
            "- Review `CHANGELOG.md` and confirm the release-facing notes for `v9.9.8`.",
        ),
        (
            "DEMO_GUIDE.md",
            "Use this guide when you want to present the `v9.9.9` Adaptive Learning project as a polished portfolio demo instead of only a developer handoff.",
            "Use this guide when you want to present the `v9.9.8` Adaptive Learning project as a polished portfolio demo instead of only a developer handoff.",
        ),
    ),
)
def test_verify_version_consistency_rejects_stale_current_release_reference(
    tmp_path,
    monkeypatch,
    stale_path_name,
    old_text,
    new_text,
):
    version = "9.9.9"
    package_json_path, readme_path, checklist_path, demo_guide_path = _write_version_reference_files(
        tmp_path, version
    )
    target_map = {
        "README.md": readme_path,
        "RELEASE_CHECKLIST.md": checklist_path,
        "DEMO_GUIDE.md": demo_guide_path,
    }
    target_path = target_map[stale_path_name]
    target_path.write_text(
        target_path.read_text(encoding="utf-8").replace(old_text, new_text),
        encoding="utf-8",
    )

    monkeypatch.setattr(verify_delivery, "VERSION", version)
    monkeypatch.setattr(verify_delivery, "FRONTEND_DIR", package_json_path.parent)
    monkeypatch.setattr(verify_delivery, "README_PATH", readme_path)
    monkeypatch.setattr(verify_delivery, "RELEASE_CHECKLIST_PATH", checklist_path)
    monkeypatch.setattr(verify_delivery, "DEMO_GUIDE_PATH", demo_guide_path)
    monkeypatch.setattr(verify_delivery, "REPO_ROOT", tmp_path)

    with pytest.raises(verify_delivery.StepFailed, match=stale_path_name) as exc_info:
        verify_delivery.verify_version_consistency()
    assert "9.9.8" in str(exc_info.value)
    assert "9.9.9" in str(exc_info.value)
