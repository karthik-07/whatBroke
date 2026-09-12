# Journal fixtures

`boots.json` is a synthetic journalctl JSON boot table with two boots on January
1–2, 2026. Each has one hour of observed records; the first timestamp includes
a microsecond to verify precision. No actual machine boot IDs are included.

`errors.jsonl` contains two synthetic error-or-higher records for the first fixture
boot: a service error and a kernel driver message. No live journal data is used.
