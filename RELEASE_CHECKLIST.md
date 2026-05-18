# Release Checklist

Use this checklist for every release so a new maintainer can ship confidently without tribal knowledge.

## 1. Prepare the release candidate

- Confirm the target branch is up to date and CI is green.
- Review `CHANGELOG.md` and add release-facing notes under the upcoming version.
- Update `VERSION` and any user-visible version strings that must stay in sync.

## 2. Backend verification

- Run `python -m compileall backend`
- Run `ruff check backend tests`
- Run `mypy backend`
- Run `ENABLE_RAG=false MAX_UPLOAD_SIZE_MB=10 pytest`
- If Docker is part of the release, confirm backend env defaults still boot with `ENABLE_RAG=false`.

## 3. Frontend verification

- Confirm `node -v` reports `22.18.0` or newer.
- Run `cd frontend && npm ci`
- Run `npm run typecheck`
- Run `npm run lint`
- Run `npm run format:check`
- Run `npm run test:ci`
- Run `npm run build`

## 4. E2E verification

- Run mocked smoke coverage with `cd frontend && npm ci && npx playwright install --with-deps chromium && RUN_E2E=1 npm run test:e2e -- --project=chromium`
- Run full-stack smoke coverage with `cd frontend && npm ci && npx playwright install --with-deps chromium && npm run test:e2e:fullstack -- --project=chromium`
- Confirm the full-stack run resets deterministic demo data before the scenario and leaves the demo resettable afterward.

## 5. Demo and packaging checks

- Call `POST /api/demo/reset` and confirm the summary returns the expected seeded lesson id.
- Run `docker compose config`
- If shipping containers, also run `docker compose build`
- Verify the main portfolio/demo flow still works manually: lesson generate, review submit, progress updated.
- Confirm runtime data remains untracked: keep only `data/.gitkeep` in git, and never release committed `data/*.db`, `data/lessons/`, `data/audio/`, `data/exports/`, or `data/chroma_db/`.

## 6. Finalize the release

- Bump version numbers and confirm `CHANGELOG.md` reflects the release contents.
- Create the git tag for the release version.
- Draft release notes using the changelog summary plus any known limitations.
- Publish the release only after all checks above pass.
