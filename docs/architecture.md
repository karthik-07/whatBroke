# Architecture

The Pacman collector, package event/result models, Arch log-path resolver, and
package report are implemented. Journal collection and analysis remain planned.

| Module | Responsibility |
| --- | --- |
| `cli` | Parse arguments and coordinate the pipeline. |
| `models` | Define shared events, boot-history coverage, and results. |
| `collectors` | Read and parse existing journal and package-history records. |
| `distros` | Detect support and select collectors and distro defaults. |
| `analysis` | Normalize failures, compare boots, and find preceding changes. |
| `reporting` | Render findings, evidence, and history limitations. |

Collectors should return shared models. Analysis should consume those models
without depending on distro-specific paths, formats, or output rendering.
Reporting should not collect logs or decide which changes are relevant.

## Data flow

1. Select a distro adapter and discover available data sources.
2. Collect boot metadata, journal failures, and package transactions.
3. Normalize records while preserving source evidence.
4. Group failures by signature and compare available boot histories.
5. Find changes preceding the first observed failure.
6. Report counts, evidence, coverage, and candidate changes.

The planned event contract includes time and timezone, source, event kind,
message, optional boot ID and component, and source-specific details such as
package versions. Package transactions do not necessarily belong to a known boot.

## Supporting other distributions

Start with `distros/arch/` and a Pacman history collector. Future distributions
can add sibling adapters and package-history readers without changing the
comparison engine. Share the systemd journal collector across compatible distros.

Adapters should declare their capabilities. Missing journal retention, unreadable
logs, and unsupported sources must be reported as limitations, not interpreted as
an absence of failures. Non-systemd collectors are outside the initial MVP.

## Analysis constraints

- Preserve original evidence alongside normalized failure signatures.
- Distinguish missing logs from observed boots without the failure.
- Make boot duration and comparison windows visible when reporting counts.
- Describe first appearance as first *observed* appearance.
- Distinguish package installation from activation when evidence permits.
- Present temporal correlation as a lead for investigation, not proof of causation.

## Runtime

Prefer the Python standard library. Run on demand and read existing logs without
persistent services or system modifications. Collectors should report permission
failures explicitly and never escalate automatically.

## Implemented package collection contract

`models/packages.py` defines package events with timestamps, actions, versions,
source paths, line numbers, and raw evidence. Collection results hold events,
source status, observed history bounds, read/ignored/malformed counts, warnings,
and any read error. A read failure preserves events already collected.

Bounds include valid timestamps from non-package records. Offset-aware timestamps
are compared chronologically; legacy local timestamps have separate bounds so
unknown historical timezones are never guessed. A readable empty file is available
but has no observed coverage. Malformed records produce a partial result.

`distros/arch/pacman.py` uses `pacman-conf LogFile` to respect configuration Includes
and defaults. If discovery fails, the default path is tried with a notice. An
explicit CLI path bypasses discovery. See the official
[pacman-conf manual](https://man.archlinux.org/man/pacman-conf.8.en) and
[pacman configuration manual](https://man.archlinux.org/man/pacman.conf.5.en).

The collector reads one plain-text log; rotated archives, transaction-completion
validation, and package activation tracking remain outside this milestone.
