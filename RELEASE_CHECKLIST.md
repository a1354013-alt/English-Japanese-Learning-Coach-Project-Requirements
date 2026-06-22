# Release Checklist

Use this checklist for every release so a new maintainer can ship confidently without tribal knowledge.

## 1. Prepare the release candidate

- Confirm the target branch is up to date and CI is green.
- Review `CHANGELOG.md` and add release-facing notes under the upcoming version.
- Update root `VERSION`; it is the source of truth for backend app metadata and release archives. Keep `frontend/package.json` in sync; `scripts/verify_delivery.py` checks this.
- Confirm release notes still state that the project is a single-user/local demo learning coach, not production multi-user SaaS.

## 2. Backend verification

- Run `python -m compileall -q backend`
- Run `python -m ruff check backend tests`
- Run `python -m mypy backend`
- Run `python -m pytest backend/tests -q -m "not rag and not startup_isolation"`
- Run `python -m pytest backend/tests/test_rag_disabled_startup.py -q`
- Run `python -m pip install -r backend/requirements-rag.txt` and then `python -m pytest backend/tests -q -m rag` for the optional RAG smoke gate
- If Docker is part of the release, confirm backend env defaults still boot with `ENABLE_RAG=false`.
- Confirm `/api/health` succeeds with only app + DB available, and `/api/ready` reports optional Ollama / RAG dependency state without crashing.

## 3. Frontend verification

- Confirm `node -v` reports `22.18.0` or newer.
- Run `cd frontend && npm ci`
- Run `npm audit --omit=dev`
- Run `npm audit`
- Run `npm run typecheck`
- Run `npm run lint`
- Run `npm run format:check`
- Run `npm run test:ci`
- Run `npm run build`

## 4. E2E verification

- Run mocked smoke coverage with `cd frontend && npm ci && npx playwright install --with-deps chromium && RUN_E2E=1 npm run test:e2e -- --project=chromium`
- Run auto-CI-equivalent full-stack smoke coverage with `cd frontend && npm ci && npx playwright install --with-deps chromium && npm run test:e2e:fullstack:smoke -- --project=chromium`
- Run full-stack smoke coverage with `cd frontend && npm ci && npx playwright install --with-deps chromium && npm run test:e2e:fullstack -- --project=chromium`
- Confirm the full-stack run resets deterministic demo data before the scenario and leaves the demo resettable afterward.
- Confirm the stable lesson flow coverage still demonstrates `lesson generate -> review submit -> progress updated` without relying on a live Ollama model.

## 5. Demo and packaging checks

- Only for local demo validation, start the backend with `ALLOW_DEMO_RESET=true`, then call `POST /api/demo/reset` and confirm the summary returns the expected seeded lesson id. Do not enable this in production.
- Run `python scripts/verify_delivery.py`
- Optionally run `python scripts/verify_delivery.py --include-rag` after installing `backend/requirements-rag.txt`; skipped optional checks must print a clear reason.
- Run `python scripts/make_release_zip.py`
- Inspect the zip contents and confirm it does not contain `data/language_coach.db`, any `*.db`, `*.db-wal`, `*.db-shm`, `data/chroma/`, `data/chroma_db/`, `data/audio/`, `data/exports/`, `data/lessons/`, `frontend/dist/`, `frontend/test-results/`, `frontend/playwright-report/`, `frontend/coverage/`, or `frontend/node_modules/`
- Run `docker compose config`
- If shipping containers, also run `docker compose build`
- Verify the main portfolio/demo flow still works manually: lesson generate, review submit, progress updated.
- Confirm runtime data remains untracked: keep only `data/.gitkeep` in git, and never release runtime DBs, user data, test reports, or cache directories.

## 6. Finalize the release

- Bump version numbers and confirm `CHANGELOG.md` reflects the release contents.
- Create the git tag for the release version.
- Draft release notes using the changelog summary plus any known limitations.
- Known limitations should include: TTS is integration-ready but disabled by default; core mode works without RAG dependencies; RAG mode requires additional dependencies and separate verification.
- Publish the release only after all checks above pass.
