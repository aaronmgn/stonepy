# Configuration Reference

`ClientConfig` holds every tunable setting for both `StoneXClient` and `AsyncStoneXClient`. It is a plain dataclass: construct it with keyword arguments, or build it from environment variables with `ClientConfig.from_env()`.

Only `base_url` is required; every other field has a default. The tables below document each field exactly as defined in `stonepy._core.config`.

```python
from stonepy import ClientConfig, StoneXClient

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingApi")

with StoneXClient(config) as client:
    ...
```

## Required field

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `base_url` | `str` | _(required)_ | CIAPI root URL. No default; must be supplied positionally or by keyword. |

## Connection & timeouts

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `connect_timeout` | `float` | `10.0` | Seconds to wait for a connection to be established. |
| `read_timeout` | `float` | `30.0` | Seconds to wait for a response to be read. |
| `write_timeout` | `float` | `30.0` | Seconds to wait while sending the request body. |
| `pool_timeout` | `float` | `5.0` | Seconds to wait for a free connection from the pool. |
| `max_connections` | `int` | `20` | Maximum number of connections in the HTTP connection pool. |

## Authentication & sessions

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `app_key` | `str` | `""` | Application key used for log-on and session refresh. |
| `username` | `str` | `""` | StoneX / City Index username used for automatic session refresh. |
| `password` | `str` | `""` | Account password used for automatic session refresh. |
| `app_version` | `str` | `"stonepy"` | Application version string reported during log-on. |
| `proactive_refresh_seconds` | `float` | `1080.0` | Age (in seconds) after which the session is proactively refreshed before it expires. |

!!! tip
    Set `app_key`, `username`, and `password` together to enable automatic session refresh. Leaving them empty disables proactive refresh, in which case you manage the session yourself.

## Resilience

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `max_retries` | `int` | `3` | Maximum number of retry attempts for retryable requests. |
| `retry_budget_seconds` | `float` | `30.0` | Total time budget (in seconds) for all retries of a single request. |
| `rate_limit_max` | `int` | `500` | Maximum number of requests allowed within the rate-limit window. |
| `rate_limit_window_seconds` | `float` | `5.0` | Length (in seconds) of the rolling rate-limit window. |

## Transport & security

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `verify_tls` | `bool` | `True` | Whether to verify TLS certificates. |
| `proxy` | `str \| None` | `None` | Optional proxy URL routed through for all requests. |
| `user_agent` | `str` | `"stonepy/<version>"` | User-Agent header. Defaults to `stonepy/` plus the installed package version (falling back to `0.1.2` if the version cannot be resolved). |

!!! warning
    Setting `verify_tls=False` disables certificate verification and exposes the connection to interception. Only use it against trusted, isolated test endpoints.

## Extensibility

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `status_decoder` | `StatusDecoder \| None` | `default_status_decoder` | Callable that maps API status codes to outcomes. Pass `None` to disable status decoding. |
| `enable_plugins` | `bool` | `False` | Whether plugin hooks are enabled. |
| `allow_overrides` | `tuple[str, ...]` | `()` | Tuple of field names that plugins are permitted to override. |

## From the environment

`ClientConfig.from_env()` builds a config from `STONEX_*` environment variables, with optional keyword overrides:

| Variable | Maps to | Default if unset |
| --- | --- | --- |
| `STONEX_BASE_URL` | `base_url` | `""` |
| `STONEX_APP_KEY` | `app_key` | `""` |
| `STONEX_USERNAME` | `username` | `""` |
| `STONEX_PASSWORD` | `password` | `""` |

Behavior:

- Keyword overrides take precedence over environment variables. For example, `ClientConfig.from_env(app_key="abc")` uses `"abc"` regardless of `STONEX_APP_KEY`.
- It raises `ValueError` if `base_url` resolves to an empty (or whitespace-only) value after applying the `STONEX_BASE_URL` variable and any override.
- It raises `TypeError` if you pass an override whose name is not a `ClientConfig` field.
- Only the four variables above are read from the environment. Every other field uses its dataclass default unless supplied as a keyword override.

```python
import os

from stonepy import ClientConfig

os.environ["STONEX_BASE_URL"] = "https://ciapi.cityindex.com/TradingApi"
os.environ["STONEX_APP_KEY"] = "your-app-key"
os.environ["STONEX_USERNAME"] = "your-username"
os.environ["STONEX_PASSWORD"] = "your-password"

config = ClientConfig.from_env()
```

Override individual fields, including ones with no environment variable:

```python
from stonepy import ClientConfig

config = ClientConfig.from_env(
    base_url="https://ciapi.cityindex.com/TradingApi",
    read_timeout=60.0,
    max_retries=5,
)
```

!!! note
    `from_env()` does not require the `STONEX_*` variables to be set as long as the corresponding values are provided as keyword overrides; only `base_url` is mandatory and is validated as non-empty.
