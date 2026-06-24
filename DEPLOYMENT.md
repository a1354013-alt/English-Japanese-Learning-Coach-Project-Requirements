# Deployment Notes

Use these notes when recreating the app in a clean environment or demo container.

## Toolchain

The release-verified toolchain is:

- Python `3.11.x`
- Node.js `22.18.0`

Local frontend setup should match CI:

```bash
nvm install
nvm use
node -v
cd frontend
npm ci
```

## Backend Container

The backend Docker image installs the runtime packages required for PDF export, including:

- `fonts-noto-cjk`
- `fontconfig`

This lets ReportLab render Japanese and Chinese lesson content without relying on Helvetica fallback.

## PDF Export Font Behavior

The PDF exporter searches for an installed CJK-capable font first. Current deployment behavior is:

1. Prefer a detected CJK font such as Noto Sans CJK.
2. If no supported CJK font is available, log a warning.
3. Fall back to Helvetica so the export still completes, even though CJK glyph coverage may be incomplete.

If you build a custom runtime image, keep an equivalent CJK font package installed or PDF output for Japanese and Chinese text may degrade.

## Frontend E2E

Install the Playwright Chromium browser once before the first local E2E run:

```bash
cd frontend
npm run e2e:install
npm run test:e2e -- --project=chromium
```

CI uses the same frontend install flow and the same `e2e:install` script, with `--with-deps` added on Linux runners.

## Release Verification

For a clean checkout release verification:

```bash
python scripts/verify_delivery.py
```

This checks:

- Python version
- Node version
- backend compile, lint, typecheck, and tests
- frontend `npm ci`
- frontend production and full audits
- frontend typecheck, lint, format, tests, and build
- release zip creation and archive validation
