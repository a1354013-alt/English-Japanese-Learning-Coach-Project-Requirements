# Release Notes v1.4.3

`v1.4.3` is a maintenance hotfix focused on release hygiene and SQLite lifecycle safety. It does not add learner-facing features or begin the planned `v1.5` extraction work.

Highlights:

- Removes mistakenly committed generated artifacts, including the tracked `.venv311_hotfix2` virtual environment and generated coverage output.
- Hardens release packaging and archive verification so common `.venv*` and `venv*` variants are excluded consistently from local dirty-tree release builds.
- Tracks SQLite connections by connection identity rather than thread identifier, so short-lived worker-thread reuse cannot orphan older open connections.
- Closes all tracked SQLite connections during FastAPI shutdown and test teardown, including worker-thread connections created through sync `TestClient` paths.
- Treats pytest unraisable unclosed-SQLite warnings as regressions and adds deterministic coverage for the all-thread shutdown path plus the Python 3.13 warning-as-error lane.

The adaptive learning, demo, RAG, and voice-provider boundaries from `v1.4.2` remain unchanged.
