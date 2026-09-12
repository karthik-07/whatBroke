# Tests

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` from the repository root.

The Pacman tests cover package actions, original evidence, malformed records,
encoding errors, chronological history bounds, legacy timestamps, empty/missing
files, read failures, configuration discovery, and CLI behavior. Permission errors
are simulated so tests work consistently without root or an Arch installation.
No tests read the developer's system logs.
