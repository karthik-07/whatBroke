# What Broke?

**What changed before your Linux system started breaking?**

What Broke? is a lightweight, local CLI project designed to identify newly observed
Linux failures and show the system changes that preceded them. The first target is
**Arch Linux with systemd and Pacman**.

**Status: early development.** The package scaffold, informational CLI, and project
documentation exist. Log collection, boot comparison, and correlation are planned.

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

## Try the scaffold

Requires Python 3.11 or newer. No third-party runtime dependencies are declared.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
whatbroke --help
whatbroke --version
```

Running `whatbroke` currently prints development status. It does not read logs or
diagnose failures. To run directly from source without installing:

```sh
PYTHONPATH=src python3 -m whatbroke --help
```

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
