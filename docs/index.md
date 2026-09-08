# stonepy

A typed Python client for the StoneX / City Index **CIAPI v2** trading API, with both
synchronous and asynchronous clients generated from the upstream API catalog.

[![PyPI version](https://img.shields.io/pypi/v/stonepy.svg)](https://pypi.org/project/stonepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/stonepy.svg)](https://pypi.org/project/stonepy/)
[![CI](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml/badge.svg)](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml)

## Why stonepy

- **Typed models.** Request and response DTO bodies are
  [Pydantic](https://docs.pydantic.dev/) models; some methods take primitive parameters or return
  bare scalars or lists. Generated model stubs let mypy and pyright check snake_case or wire-alias
  constructor keywords, subject to the
  [constructor typing limitations](installation.md#type-checking-pep-561).
- **Sync and async.** Identical APIs on `StoneXClient` and `AsyncStoneXClient`.
- **Complete coverage.** All 128 endpoints of the frozen catalog revision (`CATALOG_VERSION`)
  are bound, using the v2 variant of every endpoint that has one.
- **Batteries included.** Automatic session refresh, retry handling, rate-limit handling, and a
  clear exception hierarchy.

## Install

```bash
pip install stonepy
```

Requires Python >= 3.11 and pydantic >= 2.7 (< 3.0), with pydantic >= 2.12 on Python 3.14
and newer.

## At a glance

=== "Sync"

    ```python
    from stonepy import ClientConfig, StoneXClient
    from stonepy.models import ApiLogOnRequestDTO

    config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

    with StoneXClient(config) as client:
        session = client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="username",
                Password="password",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
        print(session.status_code)
    ```

=== "Async"

    ```python
    from stonepy import AsyncStoneXClient, ClientConfig
    from stonepy.models import ApiLogOnRequestDTO

    config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

    async with AsyncStoneXClient(config) as client:
        session = await client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="username",
                Password="password",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
        print(session.status_code)
    ```

Continue with the [Quickstart](quickstart.md), or jump to the [API reference](api/client.md).

When upgrading, await async-session mutators in extension code and ensure request-field
assignments pass validation. In-place edits to nested containers remain unguarded; see
[assignment validation](api/models.md#assignment-validation). If migrating from an older release,
also use strict `Request<Name>` DTO variants for shared request data, replace entry-point plugins
with explicitly constructed resources, and update deprecated resource names.
See the [model migration notes](api/models.md#request-side-variants-of-shared-dtos),
[extensibility guide](guide/extensibility.md), and [changelog](changelog.md) for details.

## Disclaimer

`stonepy` is **unofficial** and is not affiliated with, endorsed by, or supported by StoneX,
City Index, or GAIN Capital. Trading carries financial risk; validate all behaviour against the
[official API documentation](https://docs.labs.gaincapital.com/) before using it with a live
account.
