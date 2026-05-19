# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Backend quality gates with `ruff`, `mypy`, and a shared `pyproject.toml`.
- Frontend `eslint` and `prettier` setup with `lint`, `lint:fix`, `format`, and `format:check` scripts.
- Reusable Vue state components: `LoadingState.vue`, `ErrorState.vue`, and `EmptyState.vue`.
- Release handoff docs in `RELEASE_CHECKLIST.md`.
- `scripts/verify_delivery.py` and `scripts/make_release_zip.py` for release verification and packaging.
- A dedicated `ENABLE_RAG=true` smoke test for real Chroma-backed CRUD coverage.
- A CI full-stack smoke job that checks backend startup, frontend startup, demo seed reset, and real review-to-progress flow.

### Changed

- CI now validates backend compile, lint, typecheck, and pytest from repository root.
- CI now validates frontend typecheck, lint, format, tests, and build.
- Mocked Playwright E2E remains the default CI gate, while a shorter full-stack smoke now runs automatically on PRs, pushes to `main`/`master`, and the nightly schedule.
- The broader full-stack E2E remains available through `workflow_dispatch`.
- Full-stack E2E now asserts the deterministic demo seed and resets demo data again after the scenario.
- README and usage docs now explain mocked E2E versus full-stack E2E and how to run each path.
- Backend `pip-audit` now runs in a separate security job with a five-minute timeout so core build/test signals stay readable.

### Fixed

- Removed the backend `mypy` ignore override for `lesson_generator`, `routers.imports`, `export_service`, and `scheduler`.
- Rebuilt fallback lesson content so degraded-mode EN/JP lessons stay readable and typed.
- Repeated loading/error/empty rendering patterns across large Vue views without changing API flow or layout structure.
