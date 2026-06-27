# stonepy

A typed Python client for the StoneX / City Index **CIAPI v2** trading API, with both
synchronous and asynchronous clients generated from the upstream API catalog.

[![PyPI version](https://img.shields.io/pypi/v/stonepy.svg)](https://pypi.org/project/stonepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/stonepy.svg)](https://pypi.org/project/stonepy/)
[![CI](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml/badge.svg)](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml)

## Why stonepy

- **Fully typed.** Every request and response is a [Pydantic](https://docs.pydantic.dev/) model,
  so your editor autocompletes fields and `mypy` checks your calls.
- **Sync and async.** Identical APIs on `StoneXClient` and `AsyncStoneXClient`.
- **Complete coverage.** All 72 documented CIAPI endpoints are bound, using the v2 variant of
  every endpoint that has one.
- **Batteries included.** Automatic session refresh, retry handling, rate-limit handling, and a
  clear exception hierarchy.

## Install

```bash
pip install stonepy
```

Requires Python >= 3.11.

## At a glance

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

Continue with the [Quickstart](quickstart.md), or jump to the [API reference](api/client.md).

## Disclaimer

`stonepy` is **unofficial** and is not affiliated with, endorsed by, or supported by StoneX,
City Index, or GAIN Capital. Trading carries financial risk; validate all behaviour against the
[official API documentation](https://docs.labs.gaincapital.com/) before using it with a live
account.
