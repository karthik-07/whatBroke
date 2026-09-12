# Architecture

This is the intended architecture. Only the package scaffold and informational
CLI exist today; the other namespaces are placeholders.

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
