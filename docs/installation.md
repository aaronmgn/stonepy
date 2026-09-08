# Installation

`stonepy` is a typed Python client for the StoneX / City Index (CIAPI) v2 trading API. It is published on PyPI as [`stonepy`](https://pypi.org/project/stonepy/) and supports Python 3.11 and newer.

## Requirements

- **Python `>=3.11`** - declared as `requires-python = ">=3.11"` in `pyproject.toml`. Tested against CPython 3.11, 3.12, 3.13, and 3.14.
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

!!! tip "Verify the install"
    ```bash
    python -c "import stonepy; print(stonepy.__version__)"
    ```
    This prints the package version from its single source in `stonepy/_version.py`.

## Runtime dependencies

A normal install pulls in three small, well-established libraries:

| Package | Constraint | Why it is needed |
| --- | --- | --- |
| [`httpx`](https://www.python-httpx.org/) | `>=0.27,<1.0` | HTTP transport for both the sync and async clients |
| [`pydantic`](https://docs.pydantic.dev/) | `>=2.7,<3.0` on Python < 3.14; `>=2.12,<3.0` on Python >= 3.14 | Typed request/response models (DTOs) and validation |
| [`simplejson`](https://simplejson.readthedocs.io/) | `>=3.19,<5.0` | JSON encoding/decoding |

That is the entire footprint - there are no native build steps on platforms with a compatible
prebuilt `pydantic-core` wheel; source installations may require a Rust toolchain. There are no
heavyweight transitive trees beyond what these three require.

!!! note "No extras for normal use"
    There are **no** optional extras to install for typical usage. `pip install stonepy` (or the `uv` equivalent above) gives you everything needed to authenticate and trade. The extras below are only for people working *on* the library.

## Contributor extras

Two optional dependency groups exist for contributors. End users do not need these.

=== "dev"

    Test, lint, type-check, and release tooling:

    ```bash
    pip install "stonepy[dev]"
    ```

    Includes `pytest`, `pytest-cov`, `respx`, `mypy`, `pyright`, `ruff`, `unasync`, `pre-commit`, `types-simplejson`, and `twine`.

=== "docs"

    Documentation build tooling:

    ```bash
    pip install "stonepy[docs]"
    ```

    Includes `mkdocs-material`, `mkdocstrings[python]`, `mike`, `mkdocs-gen-files`,
    `mkdocs-literate-nav`, and `ruff`.

With `uv`, install groups against a checkout instead:

```bash
uv pip install -e ".[dev]"
uv pip install -e ".[docs]"
```

The generator ships in the wheel but needs the dev tools (`ruff`, `unasync`)
and the repository `pyproject.toml`; run it from a source checkout or editable install.

## Type checking (PEP 561)

`stonepy` ships annotations, generated companion model stubs, and a `py.typed` marker for [PEP 561](https://peps.python.org/pep-0561/) type discovery. The package is also flagged `Typing :: Typed` on PyPI. Type checkers pick up the bundled annotations automatically - no separate stub package is required.

You can check consumer code with `mypy` or `pyright`:

```bash
mypy your_script.py
# or
pyright your_script.py
```

Editor features such as autocomplete and inline type hints (in VS Code, PyCharm, and other LSP-aware editors) work the same way, with no extra configuration.

Generated model constructors accept either catalog aliases such as `UserName` or Python names
such as `user_name` under both mypy and pyright. Use one naming convention throughout a call:
mixing alias and snake_case keywords is still a static error, although it is valid at runtime.
Aliases that cannot be Python keyword arguments, such as `"Price Tolerance"`, use the Python
field name in either constructor signature. Both checkers enforce field types and required
arguments. The required Python 3.12 typing job runs `pyright src tests`, model stubtest, and
selected consumer typing cases. Strict mypy runs in the Python 3.11-3.14 test matrix. Separate
stub/field parity tests check runtime fields and aliases; freshness against the private catalog
is checked by the manual drift workflow.

`ClientConfig.from_env()` exposes typed keyword overrides through `ClientConfigOverrides`.
Annotate dynamic override dictionaries with this exported TypedDict so checkers can validate
their keys and values.

## Stability

!!! warning "Pre-1.0 / alpha"
    `stonepy` is currently pre-1.0 (PyPI Development Status: **3 - Alpha**). The public API may change between releases. Pin a version (for example `stonepy==0.6.0`) if you need reproducible builds, and review the changelog before upgrading.
