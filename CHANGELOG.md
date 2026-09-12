# Changelog

Completed changes are recorded here. Future work lives in the
[roadmap](docs/roadmap.md). Unreleased entries have not been published as a release.

## [Unreleased]

### Added

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

- Expanded the original one-line README with project purpose, current status,
  setup instructions, structure, and an illustrative future report.
