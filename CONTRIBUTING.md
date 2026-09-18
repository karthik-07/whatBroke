# Contributing

I'm building What Broke? as a personal learning project, so I'm keeping development
solo for now and won't be accepting pull requests. Bug reports and feedback are
welcome. Thanks for taking a look!

For bug reports, include the command you ran, what you expected, and what happened.
Remove personal details and secrets from any log excerpts you share.

To explore the code locally, start with the [README](README.md),
[architecture](docs/architecture.md), and [roadmap](docs/roadmap.md).

## Local checks

These checks run from source without installing dependencies:

```sh
PYTHONPATH=src python3 -m whatbroke --help
PYTHONPATH=src python3 -m whatbroke --version
PYTHONPATH=src python3 -m whatbroke packages --log-file tests/fixtures/pacman/transactions.log
python3 -m compileall -q src
```

Run the fixture-based tests with standard-library `unittest`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Maintainer notes

- Keep distro-specific formats and paths out of the analysis engine.
- Test parser and comparison behavior using small, sanitized fixtures.
- Cover missing history and malformed records as well as successful cases.
- Never commit personal system logs or credentials.
- Update documentation when behavior changes.
- Record completed changes under `Unreleased` in `CHANGELOG.md`, using `Added`,
  `Changed`, `Fixed`, or `Removed` as appropriate. Keep plans in the roadmap.

When publishing a release, move Unreleased entries into a versioned section with
the actual release date.
