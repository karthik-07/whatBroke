# Roadmap

Milestones describe intended scope, not release commitments. Completed changes
are recorded in [CHANGELOG.md](../CHANGELOG.md).

## 0 — Foundation

- [x] Establish a Python package and informational CLI.
- [x] Separate collectors, distro integration, models, analysis, and reporting.
- [x] Document scope, architecture, and contribution workflow.

## 1 — Arch data collection

- [x] Define package events, source statuses, and observed log-history ranges.
- [x] Define boot-history records, observed ranges, and source availability.
- [x] Parse Pacman package actions with old and new versions.
- [x] Read available system journal boot history.
- [x] Read structured error-or-higher records within a selected boot.
- [x] Collect error-level kernel and service messages, preserving driver text.
- [ ] Identify failures logged at lower priorities and extract component identities.
- [x] Test malformed Pacman records, missing files, and unreadable sources.
- [x] Test boot-history collection, missing history, and access restrictions.
- [x] Test journal error-record collection and empty-versus-unavailable results.

## 2 — Boot comparison

- [x] Add conservative source-aware normalization for NetworkManager timestamps/pointers.
- [x] Distinguish new variants of three known Wi-Fi failure families from new failures.
- [ ] Expand normalization using additional tested source formats.
- [x] Compare a selected boot against configurable earlier boots.
- [x] Report newly observed signatures, counts, and history coverage.
- [x] Include observed full-boot ranges and representative evidence.
- [ ] Add equal-duration or startup-only comparison windows.

## 3 — MVP report

- [ ] Identify package changes between the last observed healthy boot and first
  observed failing boot, with a bounded fallback when no healthy baseline exists.
- [ ] Show candidate changes alongside failures.
- [ ] Provide commands to inspect source evidence.
- [ ] Validate the complete workflow against reproducible regression scenarios.

## Later

- [ ] Add component-aware correlation for kernel, firmware, drivers, and services.
- [ ] Account for package activation evidence where available.
- [ ] Add distro adapters and additional package-history collectors.
- [ ] Consider machine-readable output for scripts.

Cloud processing, AI diagnosis, background monitoring, kernel modules, and eBPF
are outside the current scope.
