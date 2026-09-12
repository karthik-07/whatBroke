# What Broke?

**What changed before your Linux system started breaking?**

What Broke? is a lightweight, local CLI project designed to identify newly observed
Linux failures and show the system changes that preceded them. The first target is
**Arch Linux with systemd and Pacman**.

**Status: early development.** Pacman package-history collection is implemented,
including log availability, observed history ranges, and package changes. System
journal boot-history, per-boot errors, and error-signature comparison are available.
Package-change correlation is still planned.

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
whatbroke boots
whatbroke errors
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
are not yet collected by the package command. Use `boots` for journal boot history.

The tool suggests sudo only for a permission-denied log read; missing files and
empty logs do not trigger that suggestion. Configuration discovery failures get a
fallback notice and an explicit-path suggestion. No privileges are requested
automatically. These commands collect evidence; no command diagnoses causes yet.

Exit codes: `0` for a readable file without malformed records (including empty
files), `1` for partial collection or a source error, and `2` for invalid CLI arguments.

## Boot history

```sh
whatbroke boots
whatbroke boots --limit 5
```

Lists the last 20 visible system-journal boots by default. `--limit` changes display
length; the total count and observed history still use all collected boots.
Each boot includes its journal index, boot ID, and first/last retained entry times
in UTC. These are not exact boot/shutdown times or proof of continuous coverage.
Index `0` means the latest listed boot, which is not necessarily the current boot.

The command queries the default system journal namespace using `journalctl` and
includes retained rotated journals accessible to that command. It reports missing
history, unavailable `journalctl`, malformed output, and command failures. Privilege
hints and permission errors trigger a restricted-access notice and sudo guidance;
other diagnostic messages are preserved and mark results incomplete. No escalation
happens automatically. Readable records do not prove every journal file is accessible.

Requires a `journalctl` version supporting JSON output for `--list-boots`. Unsupported
output produces an explicit error. Exit codes are `0` for available boot history,
`1` for missing/incomplete history or collection errors, and `2` for invalid arguments.

## Errors within a boot

```sh
whatbroke errors                         # Current running boot
whatbroke errors --boot -1               # Previous recorded boot
whatbroke errors --boot 0 --limit 50     # Latest recorded boot, show 50 errors
```

`--boot` accepts `current` (the default), a journal index, or a 32-character boot ID
from `whatbroke boots`. Positive offsets count from the oldest visible boot starting
at 1. Current-boot selection reads the kernel boot ID rather than assuming the
latest retained boot is current. The selected ID is resolved against visible boot
history before querying errors.

The collector reads system-journal priorities **0–3** (emergency through error).
It retains timestamps, messages, boot IDs, and service/source identifiers when
available. The default display limit is 20; changing it does not change the collected
count. Warnings, separate user journals, and other journal namespaces are excluded.
Driver names embedded in messages are preserved, but not yet extracted or correlated.

No matching errors in a visible boot is reported separately from unavailable
history or restricted access. Boot-history ranges describe retained records at
lookup time, not continuous coverage or exact uptime. Logs may change during a query.
Malformed records, binary messages, and ambiguous repeated fields are skipped and
counted explicitly. Original JSON is retained for accepted records, including cursors
when present; output escapes terminal control characters.

Exit codes are `0` for available collection (including zero matching errors), `1`
for incomplete or unavailable collection, and `2` for invalid arguments. As with
`boots`, sudo is suggested only when journal diagnostics indicate restricted access.

## Compare boots

```sh
whatbroke compare                         # Current boot vs up to 5 earlier boots
whatbroke compare --previous 15
whatbroke compare --boot -1 --previous 5  # An earlier target and its predecessors
```

Groups target errors by service/source and normalized message, then reports each
signature as **newly observed**, **recurring**, or **insufficient history**. Reports
include target counts, individual baseline-boot counts, original example messages,
boot IDs, observed time ranges, and requested/selected/usable boot counts.

Normalization currently strips surrounding whitespace and replaces embedded
NetworkManager timestamps and object pointers in recognized formats. Device names,
paths, error codes, and other numbers remain distinct. This conservative approach
can leave related variants in separate groups; it does not infer root causes.
Known Wi-Fi patterns also get a failure family: missing `/usr/bin/iw` from udev,
IWD “not a Wifi device,” and IWD `if_nametoindex` failures. A new exact signature
matching a previously observed family is labelled **recurring failure — new variant**.
Family counts and previously observed interface names appear alongside exact counts
and original evidence. Interface names do not establish physical device identity.
IWD object-path numbers may vary within the recognized family; error codes remain
separate. Unknown message patterns are never grouped by replacing device names globally.
With incomplete history, recurrence can be established but variant novelty is labelled
**variant history incomplete**. Empty messages are excluded from comparison signatures
and counted explicitly.

A signature can be newly observed only with at least one baseline boot and no
reported collection limitations in the target or selected baseline. Partial data
can still prove recurrence, but cannot establish absence. If fewer boots are
available than requested, labels apply only to the selected baseline and the
command reports incomplete requested coverage. No older boots means insufficient
history, not a new failure.

Comparison uses all retained error-or-higher records for each selected boot.
Observed spans are shown because boots can have different durations; counts are
not rates or equal-duration comparisons. Log retention gaps may still exist.
Only signatures found in the target are shown; resolved historical errors and
package-change correlation are outside this milestone.

Exit codes: `0` when all requested boots were collected without reported limitations,
`1` for missing/incomplete coverage or collection failure, and `2` for invalid arguments.

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
