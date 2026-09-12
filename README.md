# What Broke?

**What changed before your Linux system started breaking?**

What Broke? is a lightweight, local CLI project designed to identify newly observed
Linux failures and show the system changes that preceded them. The first target is
**Arch Linux with systemd and Pacman**.

**Status: early development.** Pacman package-history collection is implemented,
including log availability, observed history ranges, and package changes. Journal
collection, boot comparison, and failure correlation are still planned.

## How it will work

```text
Linux logs + package history → normalized events → compare boots
                            → detect new failures → show preceding changes
```

Illustrative output — not current functionality:

```text
NEWLY OBSERVED ERROR
mt7921e: Timeout for driver own

Current boot: 17 occurrences
Previous 15 boots with available logs: 0 occurrences

Recent changes before the first observed failure:
  linux-firmware upgraded
  linux upgraded
  NetworkManager upgraded

These changes are investigation candidates, not proven causes.
```

The goal is to explain **what is new and what changed before it**, saving users
from manually comparing thousands of log lines.

## Principles

- CLI only, local only, no cloud or AI dependency.
- Runs on demand: no daemon, kernel module, or eBPF.
- Reads existing logs with minimal permissions; never modifies system packages.
- Shows evidence and missing history rather than claiming certainty.
- Separates distro-specific integration from the comparison engine.

## Try it

Requires Python 3.11 or newer. No third-party runtime dependencies are declared.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
whatbroke --help
whatbroke --version
whatbroke packages
```

`whatbroke packages` resolves the log path with `pacman-conf LogFile`, falling back
with a notice to `/var/log/pacman.log` if configuration discovery fails. It reads
one plain-text file and displays its last 20 package events in file order.

You can also inspect a supplied file, including on a non-Arch development machine:

```sh
whatbroke packages --log-file tests/fixtures/pacman/transactions.log --limit 5
```

To run directly from source without installing:

```sh
PYTHONPATH=src python3 -m whatbroke packages --log-file tests/fixtures/pacman/transactions.log
```

The report includes:

- Installs, upgrades, downgrades, reinstalls, and removals, with package versions.
- Earliest and latest valid log timestamps, including non-package records.
- Source status: available, partial, permission denied, not found, or read error.
- Counts of ignored and malformed/unrecognized lines, with sample skipped line numbers.

History bounds do **not** guarantee continuous coverage. Legacy timestamps without
an offset are retained and reported separately as local history with an unknown
timezone. Unrecognized records are skipped and disclosed. Rotated/compressed logs
and the system journal are not yet collected.

The tool suggests sudo only for a permission-denied log read; missing files and
empty logs do not trigger that suggestion. Configuration discovery failures get a
fallback notice and an explicit-path suggestion. No privileges are requested
automatically. No command diagnoses failures yet.

Exit codes: `0` for a readable file without malformed records (including empty
files), `1` for partial collection or a source error, and `2` for invalid CLI arguments.

## Structure

```text
src/whatbroke/
├── cli.py          # CLI entry point
├── models/         # Shared event and result contracts
├── collectors/     # Log and package-history readers
├── distros/        # Distribution-specific integration
│   └── arch/       # Initial Arch Linux namespace
├── analysis/       # Normalization, boot comparison, correlation
└── reporting/      # CLI output
tests/fixtures/     # Sanitized log scenarios
docs/               # Architecture and roadmap
```

See the [architecture](docs/architecture.md) for the extension approach,
[roadmap](docs/roadmap.md) for upcoming milestones, and [changelog](CHANGELOG.md)
for completed work. Development guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).
