# Contributing

Thanks for your interest in improving `stonepy`! This guide covers local setup, the checks CI
enforces, and the conventions for the generated client code.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). To report a bug
or request a feature, open a [GitHub issue](https://github.com/aaronmgn/stonepy/issues); for
security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Development Setup

`stonepy` uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
uv venv
uv sync --extra dev
```

## Running Checks

CI runs the following on Python 3.11-3.13. Run them locally before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/consistency_lint.py
uv run pytest --cov=src/stonepy/_core --cov=src/stonepy/_generator --cov=src/stonepy/resources --cov-fail-under=90
```

[pre-commit](https://pre-commit.com/) hooks are also configured - run `uv run pre-commit install`
to enable them.

## Documentation

The documentation site is built with [MkDocs](https://www.mkdocs.org/) and Material for MkDocs.
Preview it locally with live reload:

```bash
uv sync --extra docs
uv run mkdocs serve
```

Build it exactly as CI does, with warnings treated as errors:

```bash
uv run mkdocs build --strict
```

The model reference pages under "API reference > Models" are generated from `stonepy.models` by
`docs/gen_ref_pages.py` at build time - do not add them by hand.

## Commit and Pull Request Conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit subjects
  (e.g. `fix(order): correct rejection semantics`).
- Keep pull requests focused. `main` is protected and requires a passing CI run before merge.

## Generated Files

Models, endpoint bindings, contract tests, `client.py`, resource `__init__.py` files, and
`_sync` resource files are generated from the StoneX catalog. **Do not edit them by hand** -
regenerate them instead:

```bash
STONEPY_CATALOG=/path/to/stonex_api_docs/Docs uv run python -m stonepy._generator all
```

The catalog lives in a separate repository; `CATALOG_VERSION` records the pinned revision.

## Adding Resource Methods

Scaffold a new resource method:

```bash
uv run python -m stonepy._generator scaffold session ChangePassword
```

The command refuses to overwrite existing files; use `--force` only when you intend to replace
the current resource and its generated test stub. Then fill in the generated test response
payload and request values, remove the skip marker, regenerate the client, and run the focused
test:

```bash
STONEPY_CATALOG=/path/to/stonex_api_docs/Docs uv run python -m stonepy._generator all
uv run pytest tests/resources/session/test_change_password.py
```

See [AGENTS.md](AGENTS.md) for the detailed resource-authoring contract.
