# Roadmap

Completed work is checked below. Unchecked items are plans, not release commitments.
See the [changelog](../CHANGELOG.md) for progress.

## Available now

- [x] Local Python CLI with package, boot, error, and comparison commands.
- [x] Pacman actions, versions, timestamps, and source evidence.
- [x] System journal boot history and per-boot error-or-higher records.
- [x] Visible history ranges, access limitations, and malformed-record reporting.
- [x] Configurable boot comparison with exact signatures and per-boot counts.
- [x] NetworkManager timestamp/pointer normalization and narrowly scoped Wi-Fi family rules.
- [x] Temporal package candidates for newly observed failures.
- [x] Synthetic tests for collection, comparison, correlation, and missing data.
- [x] Concise comparison summaries with grouped totals and `--verbose` evidence.

## Next

- [ ] Trace a selected signature or known family to its earliest observed boot.
- [ ] Report unknown onset when history starts with the failure or has gaps.
- [ ] Correlate package changes around a supported historical onset.
- [ ] Provide commands to inspect source evidence directly.
- [ ] Add a complete CLI regression scenario from synthetic logs through correlation.

## Later

- [ ] Support startup-only or equal-duration comparisons.
- [ ] Add tested normalization rules and recognize failures logged below error priority.
- [ ] Add component-aware filtering and candidate ranking.
- [ ] Account for package activation when evidence is available.
- [ ] Read rotated package logs and add distro adapters.
- [ ] Consider machine-readable output and historical incident discovery.

## Out of scope for now

Cloud processing, AI diagnosis, background monitoring, kernel modules, and eBPF.
