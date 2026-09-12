# Changelog

Completed changes are recorded here. Future work lives in the
[roadmap](docs/roadmap.md). Unreleased entries have not been published as a release.

## [Unreleased]

### Added

- Explicit Wi-Fi failure families for missing `iw`, IWD interface-type errors,
  and IWD interface-index failures, with family counts and interface-name evidence.
- Eight family regression tests covering variants, partial history, and grouping
  boundaries (70 tests total).

- `whatbroke compare` with target-boot selection and configurable previous-boot
  count (default 5), grouped signatures, per-boot counts, and original evidence.
- Conservative NetworkManager timestamp/pointer normalization preserving device
  names, paths, source identities, and error codes.
- Newly observed, recurring, and insufficient-history classifications, with
  requested/selected coverage, observed spans, and access limitations.
- Fourteen comparison regression tests (62 tests total).

- `whatbroke errors` with current-boot, index, or boot-ID selection and `--limit`.
- Structured error-or-higher system journal records with precise UTC timestamps,
  messages, priorities, boot IDs, optional source fields, cursors, and original JSON.
- Boot-history validation before error collection, distinguishing zero matching
  errors from missing or restricted logs; malformed-record reporting.
- Synthetic journal error fixture and 15 regression tests (48 tests total).

- `whatbroke boots` with configurable `--limit`, visible boot counts, boot IDs,
  journal indices, and observed UTC history ranges.
- System journal boot collector with missing-history, missing-command, timeout,
  malformed-output, and access-restriction reporting; no automatic elevation.
- Shared source statuses and structured boot-history models.
- Synthetic boot-list fixture and 15 tests for parsing, collection failures,
  access hints, CLI behavior, and reporting (33 tests total).

- Pacman collector for installs, upgrades, downgrades, reinstalls, and removals,
  preserving versions, timestamps, and source-line evidence.
- `whatbroke packages` with `--log-file` and `--limit`, configuration discovery
  through `pacman-conf`, and an explicit default-path fallback notice.
- Observed history ranges, including separate bounds for legacy local timestamps.
- Source availability and malformed-record reporting, with sudo guidance only for
  permission-denied reads and nonzero exit codes for incomplete collection.
- Synthetic Pacman fixtures and 18 portable tests covering parsing, history,
  access failures, configuration discovery, and CLI behavior.

- Python package scaffold with a `src` layout and `whatbroke` CLI entry point.
- Help, development-status, and version output.
- Namespaces for models, collectors, distro adapters, analysis, and reporting,
  including an initial Arch Linux namespace.
- Architecture, milestone roadmap, contribution guidance, and fixture conventions.
- Ignore rules for Python environments, caches, and build artifacts.

### Changed

- New exact signatures in known recurring families now report “recurring failure —
  new variant” rather than implying an entirely new failure. Incomplete history
  does not establish variant novelty. Exact signatures and evidence remain intact.

- Comparison reuses one boot-history snapshot and queries exact boot IDs.
- Empty error messages display an explicit label and are excluded from comparison
  signatures with a disclosed count.

- Expanded the original one-line README with project purpose, current status,
  setup instructions, structure, and an illustrative future report.
