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

CI runs the following on Python 3.11-3.14. Run them locally before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/consistency_lint.py
uv run pytest --cov
uv build
uv run twine check dist/*
```

The required Python 3.12 typing job also runs `uv run pyright tests src/stonepy/models`,
`uv run python -m mypy.stubtest stonepy.models`, and the pyright consumer cases selected by
`uv run pytest -m pyright tests/test_consumer_typing.py`. The interpreter matrix excludes those
pyright cases to avoid repeating checker subprocesses. Model stub/field parity runs in the
ordinary test suite; stubtest alone cannot verify Pydantic field types or aliases.

Coverage measures `src/stonepy/_core`, `_generator`, `resources` (without `_sync` and
`__init__.py`), `_endpoints`, and `stonepy.client`; `stonepy.models` is generated and excluded.

[pre-commit](https://pre-commit.com/) hooks are also configured - run `uv run pre-commit install`
to enable them. The hooks are a fast subset of CI (ruff, format, mypy); CI also runs the tests,
consistency lint, packaging, and strict docs.

## Live tests

The live suite requires explicit opt-in and an approved account. Configure the following with
your demo credentials and the positive id of the **first** client account returned by
`client.user_account.get_client_and_trading_account()`:

```bash
export STONEX_LIVE=1
export STONEX_USERNAME="your-demo-username"
export STONEX_PASSWORD="your-demo-password"
export STONEX_APP_KEY="your-app-key"
export STONEX_BASE_URL="https://ciapi.cityindex.com/TradingAPI"
export STONEX_LIVE_CLIENT_ACCOUNT_ID="12345"  # replace with the approved first client-account id
uv run pytest tests/live -m live
```

`STONEX_BASE_URL` must use HTTPS with one of these exact host/port combinations:

- `ciapi.cityindex.com` on the default HTTPS port or explicit port `443`.
- `ciapipreprod.cityindextest9.co.uk` on the default HTTPS port, explicit port `443`, or `8443`.

Without `STONEX_LIVE=1`, live tests are skipped. After opt-in, missing credentials or a missing
account id fail collection loudly; a disallowed target or an account mismatch fails at setup.
The session-wide account assertion runs before any live test, including write round-trips.

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

The generator ships in the wheel but needs the dev tools (`ruff`, `unasync`)
and the repository `pyproject.toml`; run it from a source checkout or editable install.

Models and their companion `.pyi` stubs, endpoint bindings, contract tests, `client.py`,
resource `__init__.py` files, and `_sync` resource files are generated from the StoneX catalog.
**Do not edit them by hand** - regenerate them instead:

```bash
export STONEPY_CATALOG=/path/to/stonex_api_docs/Docs/catalog
uv run python -m stonepy._generator all
```

The catalog lives in a separate repository; `CATALOG_VERSION` records the pinned revision. The
generator has no machine-specific catalog fallback. Set `STONEPY_CATALOG` as above, or pass
`--catalog-root /path/to/stonex_api_docs/Docs/catalog` on each catalog-consuming command; the CLI
flag takes precedence over the environment variable.

The catalog-free `generated-client` CI job regenerates only client/resource aggregation; it
does not regenerate or check model stubs. Full model/stub regeneration drift is checked by the
manual `drift.yml` workflow, which needs the private catalog. Ordinary CI checks stub ownership,
runtime parity, and static validity, but cannot establish freshness against that catalog.

## Adding Resource Methods

Scaffold a new resource method:

```bash
STONEPY_CATALOG=/path/to/stonex_api_docs/Docs/catalog \
  uv run python -m stonepy._generator scaffold session ChangePassword
```

The command refuses to overwrite existing files; use `--force` only when you intend to replace
the current resource and its generated test stub. Then fill in the generated test response
payload and request values, remove the skip marker, regenerate the client, and run the focused
test:

```bash
STONEPY_CATALOG=/path/to/stonex_api_docs/Docs/catalog uv run python -m stonepy._generator all
uv run pytest tests/resources/session/test_change_password.py
```

See [AGENTS.md](AGENTS.md) for the detailed resource-authoring contract.
