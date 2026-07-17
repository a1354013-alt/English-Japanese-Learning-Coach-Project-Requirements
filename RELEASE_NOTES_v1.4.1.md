# Release Notes v1.4.1

Date: 2026-07-16

## Maintenance release summary

- Added reproducible Python 3.11 dependency lock files for core runtime, development/test, and optional RAG-enabled installs.
- Updated CI and release verification to install and validate against the locked Python dependency set.
- Added backend and frontend coverage reporting with terminal output plus CI-friendly artifacts.
- Added SQLite-safe backup, restore, and validation commands for local-first maintenance.
- Added protocol boundaries and an ADR to prepare incremental repository extraction in `v1.5` without changing runtime behavior.
- Finalized release identity to `1.4.1` across versioned docs and metadata.
