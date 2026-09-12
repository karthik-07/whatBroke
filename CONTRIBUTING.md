# Contributing

Start with the [README](README.md), [architecture](docs/architecture.md), and
[roadmap](docs/roadmap.md). Follow the README for editable installation.

## Local checks

These checks run from source without installing dependencies:

```sh
PYTHONPATH=src python3 -m whatbroke --help
PYTHONPATH=src python3 -m whatbroke --version
PYTHONPATH=src python3 -m whatbroke
python3 -m compileall -q src
```

There is no automated behavior test suite yet. As functionality is implemented,
add fixture-based tests with standard-library `unittest`, runnable with:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Change guidelines

- Keep distro-specific formats and paths out of the analysis engine.
- Test parser and comparison behavior using small, sanitized fixtures.
- Cover missing history and malformed records as well as successful cases.
- Never commit personal system logs or credentials.
- Update documentation when behavior changes.
- Record completed changes under `Unreleased` in `CHANGELOG.md`, using `Added`,
  `Changed`, `Fixed`, or `Removed` as appropriate. Keep plans in the roadmap.

When publishing a release, move Unreleased entries into a versioned section with
the actual release date.
