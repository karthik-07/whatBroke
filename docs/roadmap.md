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
- [ ] Read structured failure records within each boot.
- [ ] Collect kernel, driver, and service failures.
- [x] Test malformed Pacman records, missing files, and unreadable sources.
- [x] Test boot-history collection, missing history, and access restrictions.
- [ ] Test journal failure-record collection.

## 2 — Boot comparison

- [ ] Normalize variable fields without merging unrelated failures.
- [ ] Compare a selected boot against configurable earlier boots.
- [ ] Report newly observed signatures, counts, and history coverage.
- [ ] Include explicit comparison windows and representative evidence.

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
