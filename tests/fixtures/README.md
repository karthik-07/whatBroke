# Log fixtures

Add small synthetic or sanitized examples as collectors are implemented.
Suggested subdirectories are `pacman/` and `journal/`. Preserve source formats
so the real parsers can consume them.

Document each scenario's expected result, boot coverage, and deliberately malformed
records. Replace personal identifiers and secrets before committing any logs.
