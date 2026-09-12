# Roadmap

Milestones describe intended scope, not release commitments. Completed changes
are recorded in [CHANGELOG.md](../CHANGELOG.md).

## 0 — Foundation

- [x] Establish a Python package and informational CLI.
- [x] Separate collectors, distro integration, models, analysis, and reporting.
- [x] Document scope, architecture, and contribution workflow.

## 1 — Arch data collection

- [ ] Define normalized events and boot-history coverage models.
- [ ] Parse Pacman transactions with old and new package versions.
- [ ] Read boot history and structured systemd journal records.
- [ ] Collect kernel, driver, and service failures.
- [ ] Test malformed records, missing history, and unreadable sources.

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
