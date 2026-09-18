# Architecture

What Broke? reads logs on demand, compares error signatures across boots, and
lists package changes preceding newly observed failures. Everything runs locally
using Python's standard library and existing system commands.

## Code layout

| Location | Current responsibility |
| --- | --- |
| `cli.py` | Parse commands, invoke collection, and combine reports and exit codes. |
| `models/` | Store package events, boot records, journal errors, and source status. |
| `collectors/` | Read one Pacman log and query system journal boots and errors. |
| `distros/arch/pacman.py` | Resolve the Pacman log path through `pacman-conf`, with a disclosed fallback. |
| `analysis/compare.py` | Normalize signatures, compare counts, and orchestrate boot collection. |
| `analysis/families.py` | Group recognized Wi-Fi message patterns without changing exact signatures. |
| `analysis/correlate.py` | Select temporal package candidates from structured results. |
| `reporting/` | Format evidence, counts, history limits, and diagnostics. |

There is no automatic distro detection or adapter registry yet. Package and
journal events have separate models; there is no universal event schema.

## Collection

**Packages:** preserve timestamps, actions, versions, source lines, and raw text.
Read one plain-text file. Compare timestamps with known offsets chronologically;
keep legacy local-time bounds separate. Report malformed records and read errors.
Archive discovery and transaction-completion validation are not implemented.

**Boots:** request the system journal's boot list as JSON. Preserve indices, IDs,
and first/last entry timestamps at microsecond precision. These describe observed
records, not exact uptime.

**Errors:** resolve the target to a boot ID, then query system-journal priorities
0–3. For `current`, read the kernel's current boot ID. Retain accepted JSON records,
messages, source identifiers, and cursors in memory. Disclose malformed or
unsupported records, including binary messages.

Journal calls use a C locale, no pager, and a 30-second timeout per call.
Privilege hints and read-permission errors mark access as restricted. Other
diagnostics or failures can make results incomplete. No automatic elevation occurs.

## Comparison

Discover history once and collect the target plus earlier visible boots by journal
index. Query each boot by its exact ID so changing relative indices cannot select
a different boot midway through a comparison.

A signature contains unit, identifier, transport, and normalized message.
Normalization trims surrounding whitespace and replaces recognized NetworkManager
timestamps and pointers. Original messages remain available as evidence.

Positive baseline matches establish recurrence. Calling a signature newly observed
requires at least one baseline boot and available status for every selected
collection. Missing requested boots produce a coverage shortfall. Empty target
messages are counted and excluded from signatures.

Source-specific rules group missing-`iw`, IWD interface-type, interface-index,
connection-aborted, and two `.Set` error formats. Recognized `wlanN` names and IWD
object-path numbers can vary; error types and codes remain distinct. Family context can identify a new variant of a
recurring failure without changing exact-signature counts. Family counts must not
be added to exact counts.

## Package correlation

For each newly observed signature, select changes strictly between the nearest
earlier absence baseline's last record and the earliest matching target error.
Sort candidates by timestamp and preserve versions and source-line evidence.

The CLI reads the package log once, only when eligible findings exist. Recurring
failures and new family variants do not trigger correlation. Package errors remain
visible alongside journal results; correlation limitations produce exit code 1.

Disclose incomplete logs, unknown timezones, unverified history bounds, equal
boundary timestamps, and inconsistent time ordering. No fallback onset, causal
ranking, or activation time is inferred.

## Extension boundaries

`reporting/summary.py` groups findings by source and family (or exact signature
when no family matches). Target counts sum exact counts once; baseline family
counts are never added to target totals. Recurring family evidence takes precedence
over variant novelty. Partial-history notices remain visible.

The CLI completes correlation before rendering one overall status. Default output
deduplicates candidate events by source path and line number and shared limitations
by text. `--verbose` uses the detailed renderers for per-failure windows, exact
variants, and evidence. Rendering mode does not alter collection or exit codes.

Keep new package formats in collectors and distro configuration in `distros/`.
Reuse journal collection for compatible systemd distributions. Keep rendering
separate from collection and matching decisions.

Future work includes onset tracing, broader tested normalization, component
ranking, and additional distro adapters. See the [roadmap](roadmap.md).

## Evidence limits

History can contain gaps or change between queries. Comparisons use full available
boot records with unequal spans; counts are not rates. Source availability does
not prove every log is readable. A preceding package change is an investigation
lead, and changes outside the selected window may still matter.
