# Installation

`stonepy` is a typed Python client for the StoneX / City Index (CIAPI) v2 trading API. It is published on PyPI as [`stonepy`](https://pypi.org/project/stonepy/) and supports Python 3.11 and newer.

## Requirements

- **Python `>=3.11`** - declared as `requires-python = ">=3.11"` in `pyproject.toml`. Tested against CPython 3.11, 3.12, and 3.13.
- A working internet connection at runtime to reach the CIAPI endpoints.

## Install

Choose whichever installer matches your workflow.

=== "pip"

    ```bash
    pip install stonepy
    ```

=== "uv"

    Add it to a project (records the dependency in `pyproject.toml`):

    ```bash
    uv add stonepy
    ```

    Or install it into the active environment without touching project metadata:

    ```bash
    uv pip install stonepy
    ```

=== "pipx"

    Useful if you want `stonepy` installed in an isolated environment, for example to use it from scripts or notebooks:

    ```bash
    pipx install stonepy
    ```

!!! tip "Verify the install"
    ```bash
    python -c "import stonepy; print(stonepy.__version__)"
    ```
    This prints the installed version (for example `0.2.1`).

## Runtime dependencies

A normal install pulls in three small, well-established libraries:

| Package | Constraint | Why it is needed |
| --- | --- | --- |
| [`httpx`](https://www.python-httpx.org/) | `>=0.27,<1.0` | HTTP transport for both the sync and async clients |
| [`pydantic`](https://docs.pydantic.dev/) | `>=2.7,<3.0` | Typed request/response models (DTOs) and validation |
| [`simplejson`](https://simplejson.readthedocs.io/) | `>=3.19,<4.0` | JSON encoding/decoding |

That is the entire footprint - no native build steps and no heavyweight transitive trees beyond what these three require.

!!! note "No extras for normal use"
    There are **no** optional extras to install for typical usage. `pip install stonepy` (or the `uv` / `pipx` equivalents above) gives you everything needed to authenticate and trade. The extras below are only for people working *on* the library.

## Contributor extras

Two optional dependency groups exist for contributors. End users do not need these.

=== "dev"

    Test, lint, type-check, and release tooling:

    ```bash
    pip install "stonepy[dev]"
    ```

    Includes `pytest`, `pytest-cov`, `respx`, `mypy`, `ruff`, `unasync`, `pre-commit`, `types-simplejson`, and `twine`.

=== "docs"

    Documentation build tooling:

    ```bash
    pip install "stonepy[docs]"
    ```

    Includes `mkdocs-material`, `mkdocstrings[python]`, `mike`, and `ruff`.

With `uv`, install groups against a checkout instead:

```bash
uv pip install -e ".[dev]"
uv pip install -e ".[docs]"
```

## Type checking (PEP 561)

`stonepy` is fully typed and ships a `py.typed` marker, so it is [PEP 561](https://peps.python.org/pep-0561/) compliant. The package is also flagged `Typing :: Typed` on PyPI. Type checkers pick up the bundled annotations automatically - no separate stub package is required.

This means tools like `mypy` and `pyright` work out of the box:

```bash
mypy your_script.py
# or
pyright your_script.py
```

Editor features such as autocomplete and inline type hints (in VS Code, PyCharm, and other LSP-aware editors) work the same way, with no extra configuration.

## Stability

!!! warning "Pre-1.0 / alpha"
    `stonepy` is currently pre-1.0 (PyPI Development Status: **3 - Alpha**). The public API may change between releases. Pin a version (for example `stonepy==0.2.1`) if you need reproducible builds, and review the changelog before upgrading.
