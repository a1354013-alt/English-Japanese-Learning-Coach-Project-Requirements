# Release Checklist

Use this checklist for every release so a new maintainer can ship confidently without tribal knowledge.

## 1. Prepare the release candidate

- Confirm the target branch is up to date and CI is green.
- Review `CHANGELOG.md` and add release-facing notes under the upcoming version.
- Update root `VERSION`; it is the source of truth for backend app metadata and release archives. Keep `frontend/package.json` in sync; `scripts/verify_delivery.py` checks this.
- Confirm release notes still state that the project is a single-user/local demo learning coach, not production multi-user SaaS.

## 2. Backend verification

- Confirm `python --version` reports `3.11.x`. Python `3.11.x` is required for release verification.
- Run `python scripts/verify_delivery.py` with that same Python `3.11.x` interpreter; do not treat another Python runtime as equivalent.
- Run `python -m compileall backend scripts tests`
- Run `python -m ruff check backend scripts tests`
- Run `python -m mypy backend`
- Run `python -m pytest -q -m "not rag and not startup_isolation"` from the repository root for the main backend test lane.
- Run `python -m pytest backend/tests/test_rag_disabled_startup.py -q` as the separate startup isolation lane.
- Optional RAG verification requires `backend/requirements-rag.txt`. Run `python -m pip install -r backend/requirements-rag.txt` and then `python -m pytest backend/tests -q -m rag` only when you are validating the RAG lane.
- If Docker is part of the release, confirm backend env defaults still boot with `ENABLE_RAG=false`.
- If Docker is part of the release, confirm the backend image still installs CJK-capable PDF fonts (`fonts-noto-cjk` plus `fontconfig` or equivalent) so Japanese and Chinese exports do not silently regress to broken glyph rendering.
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
- Run `npm run build`

## 4. E2E verification

- Run mocked smoke coverage with `cd frontend && npm ci && npm run e2e:install && RUN_E2E=1 npm run test:e2e -- --project=chromium`
- Run auto-CI-equivalent full-stack smoke coverage with `cd frontend && npm ci && npm run e2e:install && npm run test:e2e:fullstack:smoke -- --project=chromium`
- Run full-stack smoke coverage with `cd frontend && npm ci && npm run e2e:install && npm run test:e2e:fullstack -- --project=chromium`
- Confirm the full-stack run resets deterministic demo data before the scenario and leaves the demo resettable afterward.
- Confirm the stable lesson flow coverage still demonstrates `lesson generate -> review submit -> progress updated` without relying on a live Ollama model.

## 5. Demo and packaging checks

- Only for local demo validation, start the backend with `ALLOW_DEMO_RESET=true`, then call `POST /api/demo/reset` and confirm the summary returns the expected seeded lesson id. Do not enable this in production.
- Run `python scripts/verify_delivery.py`
- Optionally run `python scripts/verify_delivery.py --include-rag` after installing `backend/requirements-rag.txt`; skipped optional checks must print a clear reason.
- Run `python scripts/make_release_zip.py`
- Inspect the zip contents and confirm it does not contain `data/language_coach.db`, any `*.db`, `*.db-wal`, `*.db-shm`, `data/chroma/`, `data/chroma_db/`, `data/audio/`, `data/exports/`, `data/lessons/`, `frontend/dist/`, `frontend/test-results/`, `frontend/playwright-report/`, `frontend/coverage/`, or `frontend/node_modules/`
- Docker checks require local Docker availability. Run `docker compose config` when Docker is installed locally.
- If shipping containers and Docker is available locally, also run `docker compose build`
- Smoke-check PDF export with Japanese or Chinese content and confirm it completes without backend errors; if a CJK font is missing, the app should log a clear warning instead of failing silently.
- Verify the main portfolio/demo flow still works manually: lesson generate, review submit, progress updated.
- Confirm runtime data remains untracked: keep only `data/.gitkeep` in git, and never release runtime DBs, user data, test reports, or cache directories.
- Treat `npm audit --omit=dev` and `npm audit` as required release gates while the locked dependency tree remains vulnerability-free. If a future upstream toolchain regression affects only dev dependencies, downgrade that lane only after updating CI, docs, and `scripts/verify_delivery.py` together.

## 6. Finalize the release

- Bump version numbers and confirm `CHANGELOG.md` reflects the release contents.
- Create the git tag for the release version.
- Draft release notes using the changelog summary plus any known limitations.
- Known limitations should include: TTS is integration-ready but disabled by default; core mode works without RAG dependencies; RAG mode requires additional dependencies and separate verification.
- Publish the release only after all checks above pass.
