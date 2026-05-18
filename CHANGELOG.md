# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Backend quality gates with `ruff`, `mypy`, and a shared `pyproject.toml`.
- Frontend `eslint` and `prettier` setup with `lint`, `lint:fix`, `format`, and `format:check` scripts.
- Reusable Vue state components: `LoadingState.vue`, `ErrorState.vue`, and `EmptyState.vue`.
- Release handoff docs in `RELEASE_CHECKLIST.md`.

### Changed

- CI now validates backend compile, lint, typecheck, and pytest from repository root.
- CI now validates frontend typecheck, lint, format, tests, and build.
- Mocked Playwright E2E remains the default CI gate; full-stack E2E stays in a separate `workflow_dispatch` job.
- Full-stack E2E now asserts the deterministic demo seed and resets demo data again after the scenario.
- README and usage docs now explain mocked E2E versus full-stack E2E and how to run each path.

### Fixed

- Several backend typing issues that blocked maintainable `mypy` adoption.
- Repeated loading/error/empty rendering patterns across large Vue views without changing API flow or layout structure.
