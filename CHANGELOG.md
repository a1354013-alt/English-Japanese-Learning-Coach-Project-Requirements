# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Automated frontend i18n completeness coverage to keep Traditional Chinese keys aligned with English.

### Fixed

- Added missing Traditional Chinese Feynman feedback translations.

## [1.4.0-rc3] - 2026-07-11

### Changed

- Version metadata is aligned to `1.4.0-rc3` across root, frontend package, and release-facing documentation.
- Learning-item review requests still accept the legacy `correct` field for backward compatibility, but the schema now marks it deprecated and the backend continues to ignore it in favor of rating-derived correctness.

### Fixed

- Release packaging now preserves safe environment templates such as `.env.example`, `.env.sample`, and `.env.template` while continuing to exclude real local env files and explicit secret-oriented env variants.
- Release archive verification now fails clearly when required startup and delivery files are missing instead of only checking for forbidden artifacts.
- Release extraction smoke now proves `backend/.env.example` can bootstrap `backend/.env` and that the documented relative startup paths resolve from the extracted archive.
- `frontend/e2e/lesson-flow.spec.ts` now matches the repository Prettier string style and no longer blocks `npm run format:check`.

### Tests

- Added backend regression coverage for preserved env templates, required-file archive validation, extraction/bootstrap smoke, and deprecated learning-item review schema metadata while keeping the contradictory-client-correctness regression in place.

## [1.4.0-rc2] - 2026-07-11

### Changed

- Version metadata is aligned to `1.4.0-rc2` across root and frontend package metadata.
- Daily Study Mission now accepts a validated `language` query and uses language-specific due counts, weak items, progress, and suggested lesson metadata.
- Feynman feedback now always loads the persisted lesson by `lesson_id` and ignores any client-provided lesson snapshot payload.

### Fixed

- `/api/srs/items/review` now converts missing learning-item lookups into the standard structured `404` response with code `learning_item_not_found`.
- Learning-item review correctness is now derived from rating so `3`, `4`, and `5` are recorded consistently as successful reviews.
- Diagnostic question responses no longer expose answer keys, and diagnostic submissions now reject duplicate, unknown, blank, or partial question-id sets.
- Japanese study missions no longer silently surface the English-only micro lesson flow as if it were a Japanese mission.

### Tests

- Added backend regression coverage for valid and missing learning-item reviews, rating-derived learning outcomes for ratings `0`, `3`, `4`, and `5`, public diagnostic-question contracts, invalid diagnostic submissions, language-aware study missions, and Feynman lesson-source enforcement.
- Added frontend regression coverage for language-aware study mission reloads, SRS review payload semantics, and Feynman feedback requests without client lesson snapshots.

## [1.4.0-rc1] - 2026-07-10

### Added

- v1.4 Adaptive Learning Intelligence release candidate documentation and demo flow.
- Deterministic demo reset review history for weak vocabulary, grammar, sentence patterns, and recent 7-day Analytics activity.
- Analytics UI block for recent 7-day learning item review activity.

### Changed

- Shared micro lesson template and learning-plan construction now lives in `backend/services/micro_lesson_service.py` for both micro lesson and study mission routers.
- Version metadata is aligned to `1.4.0-rc1` across root and frontend package metadata.

### Fixed

- Demo reset now produces immediately meaningful Analytics 2.0 weakest-item and review-activity data.

## [1.3.0] - 2026-07-05

### Added

- Item-level SRS for vocabulary, grammar, and sentence patterns.
- New additive learning item tables and review history.
- `/api/srs/items/due` endpoint.
- `/api/srs/items/review` endpoint.
- `/api/srs/items/weak` endpoint.
- Snowball lesson generation context that can reuse weak and recent items.
- Feynman feedback endpoint with AI provider support and deterministic fallback.
- Feynman feedback history persistence.
- SRS review UI filters for vocabulary, grammar, and sentence patterns.
- Review rating buttons: Forgot, Hard, Good, Easy.
- Demo reset compatibility with the micro lesson diagnostic flow.

### Changed

- Lesson review can update related learning items when exercises include `related_vocabulary`, `related_grammar`, or `related_sentence_patterns`.
- Legacy lesson-wide SRS fallback remains available when no item-level references exist.
- README and `docs/DEMO_GUIDE.md` now explain the v1.3 learning-intelligence demo path.

### Fixed

- Mocked E2E now handles `/api/micro-lessons/today`.
- Full-stack smoke no longer gets blocked by `DiagnosticFlow` after demo reset.
- `pip-audit` issues fixed by upgrading `pydantic-settings` and `pypdf`.

## [1.2.0] - 2026-06-26

### Added

- Textbook-style lesson units that present objectives, vocabulary, word roots, sentence patterns, grammar, dialogue, reading, immersion shadowing, a Feynman prompt, and a review plan in one lesson flow.
- Vocabulary metadata support across lesson content and imports for roots, categories, tags, prefixes, suffixes, and memory tips.
- Backend quality gates with `ruff`, `mypy`, and a shared `pyproject.toml`.
- Frontend `eslint` and `prettier` setup with `lint`, `lint:fix`, `format`, and `format:check` scripts.
- Reusable Vue state components: `LoadingState.vue`, `ErrorState.vue`, and `EmptyState.vue`.
- Release handoff docs in `RELEASE_CHECKLIST.md`.
- `scripts/verify_delivery.py` and `scripts/make_release_zip.py` for release verification and packaging.
- A dedicated `ENABLE_RAG=true` smoke test for real Chroma-backed CRUD coverage.
- A CI full-stack smoke job that checks backend startup, frontend startup, demo seed reset, and real review-to-progress flow.

### Changed

- The vocabulary page now surfaces part of speech, root, prefix, suffix, memory tip, category, and tags for imported entries.
- Imported vocabulary search now matches `root`, `prefix`, `suffix`, `category`, `tags`, `memory_tip`, and `part_of_speech` in addition to the base fields.
- CI now validates backend compile, lint, typecheck, and pytest from repository root.
- CI now validates frontend typecheck, lint, format, tests, and build.
- Mocked Playwright E2E remains the default CI gate, while a shorter full-stack smoke now runs automatically on PRs, pushes to `main`/`master`, and the nightly schedule.
- The broader full-stack E2E remains available through `workflow_dispatch`.
- Full-stack E2E now asserts the deterministic demo seed and resets demo data again after the scenario.
- README and usage docs now explain mocked E2E versus full-stack E2E and how to run each path.
- Backend `pip-audit` now runs in a separate security job with a five-minute timeout so core build/test signals stay readable.

### Fixed

- Backend `ruff` and `mypy` release gates now pass in the pinned local verification environment.
- Frontend typecheck, lint, format check, tests, and build release gates now pass in the pinned local verification environment.
- Removed the backend `mypy` ignore override for `lesson_generator`, `routers.imports`, `export_service`, and `scheduler`.
- Rebuilt fallback lesson content so degraded-mode EN/JP lessons stay readable and typed.
- Repeated loading/error/empty rendering patterns across large Vue views without changing API flow or layout structure.
