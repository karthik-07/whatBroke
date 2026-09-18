# What Broke?

**What changed before your Linux system started breaking?**

Compare errors across Linux boots and see which package changes preceded a newly
observed failure. Right now it is only tested against **Arch Linux**.

**Early development:** package history, boot history, error comparison, and
temporal package correlation work today. Automatic onset tracing and
component-aware relevance ranking are still planned. 

Runs locally, on demand, with no cloud, AI, daemon, kernel module, or eBPF.
Your logs and system packages are never modified.

## Get started

You need Python 3.11+ and, for boot analysis, `journalctl` with JSON support for
`--list-boots`. There are no third-party Python runtime dependencies; installation
may download build dependencies.

From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
whatbroke compare
```

Use `whatbroke --help` or a command's help, such as `whatbroke compare --help`,
for options.

## Commands

```sh
whatbroke packages                      # Recent package changes
whatbroke packages --limit 50
whatbroke boots                         # Available boot history
whatbroke boots --limit 50
whatbroke errors                        # Current boot's errors
whatbroke errors --boot -1 --limit 50
whatbroke compare                       # Current boot vs 5 earlier boots
whatbroke compare --previous 15
whatbroke compare --boot -1 --previous 5
whatbroke compare --previous 5 --verbose # Exact variants, counts, and evidence
```

`packages`, `boots`, and `errors` display up to 20 records by default.
`--limit` changes the display count, not how much available history is read.

For `errors` and `compare`, choose a boot with `--boot current`, a journal index,
or a boot ID from `whatbroke boots`. Index `0` is the latest recorded boot,
`-1` the one before it; positive offsets start at `1` for the oldest visible boot.
The current running boot may differ from the latest recorded boot.

### Use a saved package log

Your configured Pacman log is used automatically, with a disclosed fallback to
`/var/log/pacman.log`. To choose a file explicitly:

```sh
whatbroke packages --log-file /var/log/pacman.log
whatbroke compare --log-file /var/log/pacman.log
```

Replace `/var/log/pacman.log` with your saved copy's path when needed.

You can try a synthetic fixture without Arch or an installation:

```sh
PYTHONPATH=src python3 -m whatbroke packages --log-file tests/fixtures/pacman/transactions.log
```

## Read the results

Package reports show installs, upgrades, downgrades, reinstalls, and removals,
including versions and observed log dates.

Boot and error reports show available history, boot IDs, timestamps, and access
limitations. Error collection includes system-journal priorities 0–3
(emergency through error).

Comparison shows one overall status, then groups related messages once and
summarizes recurring failures. Counts are target occurrences, not unique causes.
Use `--verbose` for exact signatures, per-boot counts, boot details, and original
evidence. Both modes collect the same data and return the same exit code.

| Result | Meaning |
| --- | --- |
| Newly observed | No matching signature in the selected baseline, with no reported collection limitations. |
| Recurring | A matching signature appeared in an earlier comparison boot. |
| Recurring failure — new variant | A new exact signature belongs to a known recurring failure family. |
| Insufficient history | Available evidence cannot establish whether the signature is new. |

With incomplete history, a recurring family's variant may instead be labelled
“variant history incomplete.”

Normalization handles known NetworkManager timestamp and pointer formats.
Narrow Wi-Fi rules group missing-`iw`, IWD interface-type, interface-index,
connection-aborted, and two `.Set` error formats. Recognized `wlanN` names and
numeric IWD object paths can vary within a family. Different error types and
codes remain separate; this is not comprehensive Wi-Fi detection.

### Investigate preceding changes

For newly observed failures, comparison lists package changes strictly between:

1. The last observed record of the nearest earlier comparison boot without the signature.
2. The earliest matching error in the selected boot.

The default report lists each candidate package change and shared limitation once.
Use `--verbose` for each failure's window, package versions, and source lines.
These changes are investigation candidates, not proven causes or relevance rankings.

Recurring failures and new variants do not trigger package correlation.
The tool does not yet trace them backward to their first appearance.

## Understand the limits

- **History:** you can inspect only readable, retained records. Reports show the
  available range. Increasing `--limit` cannot recover older logs, and missing
  records do not establish that an earlier boot was healthy.
- **Permissions:** restricted journal access or a denied package-log read prompts
  sudo guidance. Privileges are never requested automatically. Readable records
  do not guarantee access to every journal file.
- **Coverage:** boot timestamps describe retained entries, not exact uptime.
  Comparisons use full available boot records with potentially different durations;
  counts are not rates.
- **Sources:** journal queries include accessible rotated system journals in the
  default namespace. Warnings, separate user journals, and other namespaces are
  excluded. Package collection reads one plain-text log, without archive discovery.
- **Parsing:** skipped malformed or unsupported records are disclosed. Empty error
  messages are excluded from comparison. Legacy package timestamps without a
  timezone are shown separately and excluded from correlation.
- **Timing:** package installation does not establish activation time. Changes
  outside the correlation window may still matter. Equal boundary timestamps,
  inconsistent clocks, and unverified package-history coverage are disclosed.
- **Scope:** comparison investigates errors present in the selected boot. It does
  not search all history for past incidents or recover deleted records.

Exit codes: `0` for available results, `1` for incomplete coverage or
collection/correlation errors, and `2` for invalid arguments. Package-log fallback
and legacy-timezone notices alone do not change the package command's exit code.
An empty readable package log or zero matching errors can return `0`; neither
proves system health. Requesting more comparison boots than are available returns `1`.
Comparison can also return `1` when journal results are available but package-log
coverage is unverified; check the separate correlation status and limitations.

## Contributions

I'm building What Broke? as a personal learning project, so I'm keeping development
solo for now and won't be accepting pull requests. Bug reports and feedback are
welcome. Thanks for taking a look!

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests use synthetic records and mocked failures; you do not need root or systemd.

```text
src/whatbroke/
├── cli.py          # Commands
├── models/         # Events and results
├── collectors/     # Log readers
├── distros/arch/   # Pacman configuration
├── analysis/       # Signatures, comparison, correlation
└── reporting/      # Terminal output
tests/fixtures/     # Synthetic log scenarios
docs/               # Architecture and roadmap
```

See [architecture](docs/architecture.md) for module boundaries,
[roadmap](docs/roadmap.md) for planned work,
[changelog](CHANGELOG.md) for progress, and
[contribution policy](CONTRIBUTING.md) for feedback and development notes.
