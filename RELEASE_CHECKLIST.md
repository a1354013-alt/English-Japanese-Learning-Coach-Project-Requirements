# Release Checklist

Use this checklist for every release so a new maintainer can ship confidently without tribal knowledge.

<!-- release:current=v1.5.0 -->

## 1. Prepare the release

- Confirm the target branch is up to date and CI is green.
- Review `CHANGELOG.md` and confirm the release-facing notes for `v1.5.0`.
- Update root `VERSION`; it is the source of truth for backend app metadata and release archives. Keep `frontend/package.json` in sync at `1.5.0`; `scripts/verify_delivery.py` checks this.
- Confirm release notes still state that the project is a single-user/local demo learning coach, not production multi-user SaaS.
- Confirm README demo limitations still say authentication, authorization, user isolation, rate limiting, and audit logging are intentionally out of scope.

## 2. Backend verification

- Confirm `python --version` reports `3.11.x`. Python `3.11.x` is required for release verification.
- Run `python scripts/verify_delivery.py` with that same Python `3.11.x` interpreter; do not treat another Python runtime as equivalent.
- Install backend dependencies from the generated Python 3.11 lock file: `python -m pip install -r backend/requirements-dev.lock.txt`
- Run `python scripts/python_dependency_locks.py check`
- Run `python -m compileall backend scripts tests`
- Run `python -m ruff check backend scripts tests`
- Run `python -m mypy backend`
- Run `python -m pytest -q -m "not rag and not startup_isolation"` from the repository root for the main backend test lane.
- Run `python -m pytest backend/tests/test_rag_disabled_startup.py -q` as the separate startup isolation lane.
- Run `python -m pytest -q -m "not rag and not startup_isolation" --cov=backend --cov-branch --cov-report=term-missing:skip-covered --cov-report=xml:coverage/backend/coverage.xml --cov-report=json:coverage/backend/coverage.json --cov-report=html:coverage/backend/html -W error::ResourceWarning`
- Run `python -m pytest backend/tests/test_sqlite_lifecycle.py -q -W error::pytest.PytestUnraisableExceptionWarning` to keep all-thread SQLite shutdown regressions visible.
- Optional RAG verification requires `backend/requirements-rag.lock.txt`. Run `python -m pip install -r backend/requirements-rag.lock.txt` and then `python -m pytest backend/tests -q -m rag` only when you are validating the RAG lane.
- Run `python scripts/sqlite_backup_restore.py backup --target data/backups/release-check.sqlite3 --dry-run`
- Run `python scripts/sqlite_backup_restore.py restore --source data/backups/release-check.sqlite3 --target data/language_coach.db --dry-run` after creating a real local backup file.
- Stop the app before replacing an active SQLite database with the non-dry-run restore command.
- If Docker is part of the release, confirm backend env defaults still boot with `ENABLE_RAG=false`.
- On Linux CI or Linux release hosts, install `fonts-noto-cjk` plus `fontconfig` before strict CJK PDF verification.
- If Docker is part of the release, confirm the backend image still installs CJK-capable PDF fonts (`fonts-noto-cjk` plus `fontconfig` or equivalent) so Japanese and Chinese exports do not silently regress to broken glyph rendering.
- For local Windows PDF smoke checks, use an installed CJK font or set `PDF_CJK_FONT_PATH` to a known font such as `C:\Windows\Fonts\msjh.ttc`.
- Confirm `/api/health` succeeds with only app + DB available, and `/api/ready` reports optional Ollama / RAG dependency state without crashing.

## 3. Frontend verification

- Run `nvm install`
- Run `nvm use`
- Confirm `node -v` reports `22.18.0`. Node `22.18.0` is required for release verification.
- Run `cd frontend && npm ci`
- Run `npm audit --omit=dev`
- Run `npm audit`
- Run `npm run typecheck`
- Run `npm run lint`
- Run `npm run format:check`
- Run `npm run test:unit`
- Run `npm run test:component`
- Run `npm run test:coverage`
- Run `npm run build`

## 4. E2E verification

- Run mocked smoke coverage with `cd frontend && npm ci && npm run e2e:install && RUN_E2E=1 npm run test:e2e -- --project=chromium`
- Run auto-CI-equivalent full-stack smoke coverage with `cd frontend && npm ci && npm run e2e:install && npm run test:e2e:fullstack:smoke -- --project=chromium`
- Run full-stack smoke coverage with `cd frontend && npm ci && npm run e2e:install && npm run test:e2e:fullstack -- --project=chromium`
- Confirm persisted-chat coverage includes create/select, reload/history restore, retry-safe canonical reconciliation, EN/JP isolation, rename, and delete flows without live Ollama.
- If Playwright browsers are missing on Windows, run `cd frontend && npx playwright install chromium` after `npm ci`, then repeat the E2E command.
- Confirm the full-stack run resets deterministic demo data before the scenario and leaves the demo resettable afterward.
- Confirm the stable lesson flow coverage still demonstrates `lesson generate -> review submit -> progress updated` without relying on a live Ollama model.

## 5. Demo and packaging checks

- Only for local demo validation, start the backend with `ALLOW_DEMO_RESET=true`, then call `POST /api/demo/reset` and confirm the summary returns the expected seeded lesson id plus item-level SRS demo data. Do not enable this in production.
- Confirm the v1.4 Adaptive Learning demo path works after reset: Today page opens, Today Mission Panel shows the Daily Study Mission, the deterministic micro lesson loads, due SRS / weak items are present, and Analytics shows weakest vocabulary, grammar, sentence patterns, plus recent 7-day review activity.
- Run `python scripts/verify_delivery.py`
- Optionally run `python scripts/verify_delivery.py --include-rag` after installing `backend/requirements-rag.txt`; skipped optional checks must print a clear reason.
- Run `python scripts/make_release_zip.py`
- Inspect the zip contents and confirm it preserves only `.env.example`, `.env.sample`, and `.env.template` while excluding `.envrc`, every filename beginning with `.env` except those templates, every filename ending with `.env`, every filename containing `.env.` or `.env-`, case-insensitive stage-style `env.*` / `env-*` variants such as `env.qa` or `env.production`, common credential files such as `.npmrc`, `.pypirc`, `.netrc`, `id_rsa`, `id_ed25519`, `service-account.json`, `.pem`, `.key`, `.p12`, and `.pfx`, plus local runtime directories such as `.direnv`, at any directory depth. Also confirm shared virtual-environment classification excludes `.venv`, `.venv311`, `.venv311_hotfix2`, `.venv-3.11`, `.venv_py311`, `venv`, `venv311`, and `venv-3.11` variants while preserving source files such as `frontend/src/env.d.ts`, and that `*.log`, any `*.sqlite`, `*.sqlite3`, `*.db`, `*.db-wal`, `*.db-shm`, runtime data directories, backup directories, root local validation directories such as `dist_phase1_check/`, `dist_test/`, and `dist-local/`, nested archive payloads such as `.zip`, `.tar`, `.tar.gz`, and `.tgz`, cache directories, `data/chroma/`, `data/chroma_db/`, `data/audio/`, `data/backups/`, `data/exports/`, `data/lessons/`, `frontend/dist/`, `frontend/test-results/`, `frontend/playwright-report/`, `frontend/coverage/`, and `frontend/node_modules/` remain excluded.

* Docker checks require local Docker availability. Run `docker compose config` when Docker is installed locally.
* If shipping containers and Docker is available locally, also run `docker compose build`
* Smoke-check PDF export with Japanese kana/kanji and Traditional Chinese content and confirm the extracted PDF text is not replacement characters or tofu boxes; if a CJK font is missing, the app should log a clear warning instead of failing silently.


- Verify the main portfolio/demo flow still works manually: lesson generate, review submit, progress updated.
- Verify the v1.4 Adaptive Learning demo path still works manually: item-level SRS due items load, weak items group correctly, micro lessons do not require a live LLM, snowball-aware lesson generation still succeeds, and Feynman feedback returns either AI output or deterministic fallback without breaking the page.
- Confirm runtime data remains untracked: keep only `data/.gitkeep` in git, and never release local env files, runtime DBs, logs, user data, test reports, or cache directories.
- Create temporary validation archives outside the repository working tree so generated local checks cannot be recursively repackaged.
- Treat `npm audit --omit=dev` and `npm audit` as required release gates while the locked dependency tree remains vulnerability-free. If a future upstream toolchain regression affects only dev dependencies, downgrade that lane only after updating CI, docs, and `scripts/verify_delivery.py` together.

## 6. Finalize the release

- Bump version numbers and confirm `CHANGELOG.md` reflects the release contents.
- Create the git tag for the release version.
- Draft release notes using the changelog summary plus any known limitations.
- Do not publish final `v1.5` release notes from this development branch until release scope is complete and approved.
- Known limitations should include: TTS is integration-ready but disabled by default; immersion is text shadowing only; real recording and speech comparison are not part of this release; auth, authorization, user isolation, rate limiting, and audit logging are out of scope for the local demo; core mode works without RAG dependencies; RAG mode requires additional dependencies and separate verification.

- Publish the release only after all checks above pass.
