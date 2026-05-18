Root-level placeholder so shared CI commands like `ruff check backend tests`
have a stable `tests/` path even though the Python test suite currently lives in
`backend/tests/`.
