# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Added structured learning-session storage with additive schema `0012`, including typed session lifecycle state, append-only event logs, partial unique active-session enforcement, and deterministic server-side summaries that do not call an AI provider in Phase 1.
- Added a dedicated learning-session repository and typed REST API surface for session creation, event append/list, completion, abandonment, active-session lookup, summary generation, and cursor-based history pagination.

### Changed

- Kept the existing lesson, review, SRS, chat tutor, Feynman, and micro-lesson flows unchanged in Phase 1; they are not automatically linked to learning sessions yet and remain available without requiring an active session.
- Hardened the Learning Session Phase 1 contract with a shared semantic validation table, canonical post-finalization event retries, state-idempotent abandonment, snapshot-consistent summaries, and demo-reset cleanup through the repository clear path.
- Extended backend regression coverage to include migration `0012`, repository idempotency rules, 50-round concurrency races, semantic-contract enforcement, demo-reset cleanup, and OpenAPI/API contract checks for the new learning-session boundary.
- Updated delivery verification so development versions such as `1.6.0-dev.1` use explicit README development markers while stable release checklist and demo-guide references remain pinned to `v1.5.0`.

## [1.5.0] - 2026-07-21

### Added

- Added persisted conversations and messages for Chat Tutor, including learner-facing conversation creation, selection, rename, delete, reload restore, and EN/JP isolation flows.
- Added canonical persisted WebSocket chat events with optimistic-message reconciliation, reconnect continuity, retry-safe `client_message_id` handling, and bounded persisted context for provider prompts.
- Added additive migrations `0008`, `0009`, `0010`, and `0011` for conversation/message storage, summary checkpoints, canonical summary trigger recovery, and persisted scenario continuity.
- Added mocked and full-stack persisted-chat browser coverage that does not require a live Ollama runtime for ordinary frontend verification.
- Added regressions covering turn ordering, context bounding, validation errors, provider failure retry behavior, and WebSocket cleanup under retry/concurrency pressure.

### Changed

- Chat Tutor now restores persisted history through the typed REST + WebSocket contract, preserves scenario continuity across reconnects, and uses canonical persisted conversation/message IDs without duplicate optimistic rows after retry.
- Persisted-chat storage now spans additive schemas `0008` through `0011`, while runtime turn processing keeps per-conversation ordering stable in the supported local single-process deployment model.
- Release and dependency hardening now keep version metadata aligned, preserve the clean npm audit gate, and extend delivery verification for nested archives, secret scanning, extraction/bootstrap smoke, and shell syntax validation.

## [1.4.3] - 2026-07-17

### Added

- Added `RELEASE_NOTES_v1.4.3.md` for this release-hygiene and SQLite-lifecycle hotfix.
- Added regression coverage for virtual-environment archive exclusion variants, all-thread SQLite connection shutdown, and short-lived worker-thread SQLite lifecycle pressure.

### Changed

- Release packaging and archive verification now share a broader virtual-environment classifier so dirty local working trees cannot ship `.venv*` or `venv*` directories by accident.
- Release verification now fails early when generated cache, coverage, or the mistakenly committed `.venv311_hotfix2` tree is still present in the source checkout.

### Fixed

- Removed committed/generated local artifacts including the tracked Windows virtual environment and backend coverage output from the source tree and future release archives.
- FastAPI lifespan shutdown and test teardown now close every tracked SQLite connection by connection identity instead of thread identifier, including worker-thread/TestClient connections, so pytest unraisable unclosed-database warnings stay gone in both the supported Python 3.11 lane and the Python 3.13 warning gate.

## [1.4.2] - 2026-07-17

### Added

- Added deterministic lock portability checks that reject machine-specific paths, index directives, and embedded credentials in committed Python lock files.
- Added read-only SQLite validation regressions plus atomic backup/restore failure-path tests.
- Added `RELEASE_NOTES_v1.4.2.md` for this maintenance hotfix.

### Changed

- Version-consistency verification now uses stable current-release markers for release-facing docs instead of binding itself to a full README prose sentence.
- Backend coverage now excludes `backend/tests/*` so the reported baseline reflects application code only.
- FastAPI shutdown and pytest teardown now close SQLite database connections more consistently, including worker-thread cleanup in concurrency tests.

### Fixed

- Python lock verification is now deterministic across Windows and Linux and no longer depends on byte-comparing freshly re-resolved transitive dependency output in ordinary CI runs.
- SQLite validation no longer mutates the file it inspects; backup and restore now validate temporary copies and atomically replace only after success.
- Repeated unclosed SQLite connection warnings are now treated as regressions in the supported backend coverage lane.

## [1.4.1] - 2026-07-16

### Added

- Added reproducible Python 3.11 dependency lock files for core runtime, development/test, and optional RAG-enabled maintenance installs, plus a documented `scripts/python_dependency_locks.py refresh` workflow.
- Added backend pytest coverage and frontend Vitest coverage reporting with terminal summaries and CI-friendly XML/JSON/HTML/Cobertura artifacts.
- Added SQLite-safe local backup, restore, and validation utilities plus temporary-database regression coverage.
- Added repository-boundary protocols and an ADR that documents the incremental `v1.5` extraction path for future persisted-chat and learning-session storage.
- Added release notes for `v1.4.1` in `RELEASE_NOTES_v1.4.1.md`.

### Changed

- CI and release verification now install backend dependencies from the generated Python 3.11 lock files, and they check lock consistency before shipping.
- Release packaging policy now excludes backup directories in addition to other runtime SQLite artifacts and local build outputs.
- Version metadata is aligned to `1.4.1` across root, frontend package metadata, README, release checklist, and demo guide.

### Fixed

- Backend test lanes now guard against the deprecated `httpx` `app` shortcut returning silently by asserting that `TestClient` creation emits no deprecation warning under the supported dependency set.

## [1.4.0] - 2026-07-14

### Added

- Final v1.4 Adaptive Learning release with adaptive English and Japanese study missions, diagnostic placement, daily micro lessons, date-gated progression, item-level SRS learning intelligence, and Feynman learning support.
- Traditional Chinese localization, CJK-safe PDF export behavior, and explicit TTS availability UI for provider-ready voice integration.

### Changed

- Release delivery now includes secure atomic ZIP packaging, version consistency checks, safe environment-template handling, forbidden-file validation, extraction/bootstrap smoke coverage, and common secret-pattern scanning.
- Micro-lesson generation now resolves to one canonical concurrent lesson for each user/day.

### Fixed

- Micro-lesson completion, XP, progress counters, learning activity, and reward events now commit atomically with retry-safe and rollback-safe behavior.
- Release hardening covers retry, rollback, migration, and legacy-upgrade safety, including additive idempotent migration behavior for micro-lesson reward events.

## [1.4.0-rc9] - 2026-07-14

### Changed

- Version metadata is aligned to `1.4.0-rc9` across root, frontend package metadata, and release-facing documentation including `docs/DEMO_GUIDE.md`.

### Fixed

- Correct micro-lesson answers now complete the lesson, write the unique reward event, increment English progress counters, recalculate accuracy, add 10 XP, apply existing level/unlock rules, and record learning activity inside one `BEGIN IMMEDIATE` transaction.
- Legacy completed micro lessons that predate reward events are treated as already resolved for reward purposes; upgrading cannot grant duplicate XP only because a completed lesson has no reward-event row.

### Tests

- Added trigger-based rollback regressions for reward-event and progress-write failures, post-commit retry idempotency, legacy completed-lesson upgrade compatibility, and migration smoke coverage for the tracked reward-event table.

## [1.4.0-rc8] - 2026-07-13

### Changed

- Version metadata is aligned to `1.4.0-rc8` across root, frontend package metadata, and release-facing documentation including `docs/DEMO_GUIDE.md`.

### Fixed

- Concurrent `POST /api/micro-lessons/generate` calls now use insert-once persistence and return the same canonical saved lesson for a user/day instead of returning stale generated UUIDs.
- Correct micro-lesson answers now use an atomic database-level completion claim so only the request that changes the lesson from incomplete to complete can apply completion rewards.
- Micro-lesson completion rewards are protected by a persisted unique reward event, keeping XP, progress counters, learning activity, and streak updates retry-safe under concurrent correct-answer requests.

### Tests

- Added real ThreadPoolExecutor-based concurrency regressions for simultaneous micro-lesson generation, next-day advancement, concurrent correct answers, completion timestamp preservation, reward-event uniqueness, and retrying an already completed lesson.

## [1.4.0-rc7] - 2026-07-13

### Changed

- Version metadata is aligned to `1.4.0-rc7` across root, frontend package metadata, and release-facing documentation including `docs/DEMO_GUIDE.md`.
- Completed final-day micro lessons now show a plan-completed message instead of telling the learner to unlock a next day that does not exist.

### Fixed

- `POST /api/micro-lessons/generate` now advances the daily micro-lesson day if due, returns an existing current-day lesson unchanged, and only creates a lesson when the resolved day has no saved lesson.
- Micro-lesson generation no longer downgrades completed lessons or clears completion timestamps, and the database save helper refuses ordinary incomplete upserts over already completed micro lessons.
- Legacy completed micro lessons without `completed_local_date` or `completed_at` now use the persisted row timestamp as a deterministic advancement fallback instead of the current request date.
- Replaced a mixed-script beginner pronunciation hint in the micro-lesson template bank.

### Tests

- Added regression coverage for same-day generate idempotency after completion, preserved lesson IDs and completion timestamps, unchanged XP/progress/activity/streak state, one-day-only advancement after the local date changes, legacy completion-date fallback, final-day bounds, and both completion messages.

## [1.4.0-rc6] - 2026-07-12

### Changed

- Version metadata is aligned to `1.4.0-rc6` across root, frontend package metadata, and release-facing documentation including `docs/DEMO_GUIDE.md`.
- Release verification now checks current-release references in `README.md`, `RELEASE_CHECKLIST.md`, and `docs/DEMO_GUIDE.md` in addition to root `VERSION` and `frontend/package.json`, while leaving historical `CHANGELOG.md` entries untouched.
- Daily micro lessons now advance by local date after completion instead of immediately replacing the completed day.
- Micro lessons include Traditional Chinese copy throughout the beginner template bank, including sentence translations, dialogue, reading support, comic-panel translations, and example-sentence translations.
- Beginner pronunciation hints and IPA are shown with vocabulary items.
- Incorrect micro-lesson answers show an explanation in the UI.
- Completed-today messaging keeps the completed lesson visible until the next local day unlocks.

### Fixed

- Release ZIP creation is now atomic: includable symlink rejection happens before the final archive is touched, archive writes go through a temporary file in `dist`, successful builds replace the final ZIP atomically, failed builds clean up temporary files, and previously valid archives remain unchanged when a later build fails.
- Release packaging and crafted-archive verification now also reject common credential files such as `.npmrc`, `.pypirc`, `.netrc`, `id_rsa`, `id_ed25519`, `service-account.json`, `.pem`, `.key`, `.p12`, and `.pfx`, and local runtime directories such as `.direnv`.
- Traditional Chinese Analytics placeholders were corrected so localized metric text renders with values.

### Tests

- Added regression coverage for atomic archive failure cleanup and replacement behavior, stale current-release reference verification failures, common credential-file exclusion in packaging and crafted archives, and CLI-output redaction for symlink rejection.
- Added i18n placeholder regression coverage to keep English and Traditional Chinese interpolation keys aligned.

## [1.4.0-rc5] - 2026-07-11

### Changed

- Version metadata is aligned to `1.4.0-rc5` across root, frontend package, and release-facing documentation.
- Release documentation now states the exact env-file classification rules enforced by packaging and archive verification, including the `env.*` / `env-*` stage-variant handling and the explicit `frontend/src/env.d.ts` allowlist.

### Fixed

- Release env-file filtering now excludes `.envrc`, every filename beginning with `.env` except `.env.example`, `.env.sample`, and `.env.template`, every filename ending with `.env`, and every filename containing `.env.` or `.env-`, with case-insensitive matching at any directory depth.
- Release env-file filtering now rejects stage-style `env.*` and `env-*` variants generically instead of relying on a finite stage-token denylist, while still preserving `frontend/src/env.d.ts`.
- Release ZIP creation no longer follows symlinks and now fails clearly with only the repository-relative symlink path when an otherwise includable symlink is encountered.

### Tests

- Added adversarial release regression coverage for `.envrc`, `app.env`, `config.env`, `qa.env`, `uat.env`, `frontend/service.env.qa`, `backend/config.env`, `backend/.env.backup`, `backend/.env.vault`, uppercase variants such as `.ENV.PRODUCTION.LOCAL`, preserved env templates, `frontend/src/env.d.ts`, crafted-archive rejection, extraction/bootstrap smoke, shell syntax validation, secret-redaction assertions, and symlink rejection.

## [1.4.0-rc4] - 2026-07-11

### Changed

- Version metadata is aligned to `1.4.0-rc4` across root, frontend package, and release-facing documentation.
- Learning-item review requests still accept the legacy `correct` field for backward compatibility, but the schema now marks it deprecated and the backend continues to ignore it in favor of rating-derived correctness.
- Automated frontend i18n completeness coverage keeps Traditional Chinese keys aligned with English.

### Fixed

- Added missing Traditional Chinese Feynman feedback translations.
- Release packaging and archive verification now share one release-file policy so sensitive env files stay excluded consistently at any depth.
- Release packaging now preserves safe environment templates such as `.env.example`, `.env.sample`, and `.env.template` while rejecting `.env.*.local`, `production.env`, `local.env`, `secrets.env`, and similar secret-oriented env variants.
- Release archive verification now fails clearly when required startup and delivery files are missing instead of only checking for forbidden artifacts.
- Release extraction smoke now proves `backend/.env.example` can bootstrap `backend/.env`, that required startup paths resolve from the extracted archive, and that shipped shell scripts pass `bash -n` on non-Windows hosts when `bash` is available.
- `frontend/e2e/lesson-flow.spec.ts` now matches the repository Prettier string style and no longer blocks `npm run format:check`.

### Tests

- Added backend regression coverage for preserved env templates, required-file archive validation, sensitive env variants such as `.env.development.local` and `production.env`, extraction/bootstrap smoke, shell syntax checks, and secret-redaction-safe archive assertions while keeping the contradictory-client-correctness regression in place.

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
