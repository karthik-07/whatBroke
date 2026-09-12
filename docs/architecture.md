# Architecture

The Pacman collector, package event/result models, Arch log-path resolver, and
package report are implemented. System journal boot-history collection is also
implemented, along with per-boot error-record collection. Conservative signature comparison is implemented; package correlation remains planned.

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

## Implemented boot-history collection

`collectors/journal.py` invokes `journalctl --system --list-boots --no-pager --utc
--output=json` with a stable C locale and a 30-second timeout. It preserves stderr
rather than suppressing privilege hints. The parser validates JSON table records,
retains exact microsecond timestamps, and skips invalid/duplicate rows explicitly.
`models/boots.py` stores journal indices, IDs, and observed entry bounds.

Permission diagnostics produce restricted-access status even on a successful exit.
Other diagnostics mark the result partial; nonzero command exits remain errors.
Missing readable boots do not imply a healthy system. Availability describes this
query only, not guaranteed access to all files. No enumeration of individual
missing journal files or other namespaces is performed.

The default system journal query includes its accessible retained journal files.
Its indices refer to listed history; no row is asserted to be the currently running
boot. See the [journalctl manual](https://man.archlinux.org/man/journalctl.1.en).

## Implemented per-boot errors

`collectors/errors.py` resolves the selected boot against discovered history. For
`current`, it reads `/proc/sys/kernel/random/boot_id`; it never substitutes the most
recent recorded boot. It then queries that exact ID through `journalctl --system`
with priorities `0..3`, JSON output, `--all`, no pager, and a 30-second timeout.

`models/errors.py` retains structured events and source evidence. Error counts do
not imply distinct failure signatures yet. Empty successful queries are meaningful
only alongside readable boot history; discovery warnings and access restrictions
remain part of the result. Historical coverage is a snapshot and logs can change
between discovery and collection.

Unsupported field representations, including binary messages and repeated scalar
fields, are counted as skipped records. No component inference, signature
normalization, or cross-boot comparison is performed in this milestone. Journal
field meanings follow the [systemd field reference](https://man.archlinux.org/man/systemd.journal-fields.7.en).

## Implemented comparison

`analysis/compare.py` provides pure signature/grouping and comparison functions,
plus collection orchestration. The orchestration discovers boot history once,
resolves the target, and collects the nearest earlier visible boots by journal
index using exact IDs. Wall-clock timestamps do not determine boot order.

A signature contains unit, identifier, transport, and normalized message. Only
known NetworkManager timestamp/object-pointer patterns are substituted; original
events remain untouched. Empty target messages are counted but not classified.
A positive baseline match establishes recurrence even with partial data. Absence
requires a nonempty baseline and available status for every selected collection;
otherwise classification is insufficient history. Requested coverage shortfalls
remain visible and produce a nonzero exit status.

All retained records per boot are used. Reports expose unequal observed spans;
equal-duration analysis, broader normalization, and package correlation remain
future work. Reusing a discovery snapshot does not guarantee logs cannot rotate
while subsequent queries run.

## Failure-family context

`analysis/families.py` recognizes three complete, source-specific Wi-Fi message
patterns. Family keys retain the exact signature's source identity and preserve
error codes. Only interface names and recognized IWD object-path numbers vary
within these families. Exact signatures, counts, and original events are unchanged.
Family counts are additional context, not counts to add to exact-signature totals.

A positive baseline family match changes an otherwise unseen exact signature to
recurring failure/new variant when coverage is available. With incomplete target
or baseline collection, it reports recurring failure/variant history incomplete.
Observed interface names are labels from logs, not physical hardware identities.
