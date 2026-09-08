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
| `proactive_refresh_seconds` | `float` | `1080.0` | Token age (in seconds) at which the session is proactively refreshed; no server expiry timestamp is consulted. |

!!! tip
    Set `app_key`, `username`, and `password` together to enable automatic session refresh
    without an explicit `log_on()`. A successful manual `log_on()` also installs a refresh
    callable, so proactive and reactive refresh work for manual sessions.

## Resilience

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `max_retries` | `int` | `3` | Maximum number of retry attempts for retryable requests. |
| `retry_budget_seconds` | `float` | `30.0` | Pre-sleep admission budget: a retry is skipped when its upcoming sleep would exceed this elapsed-time threshold; in-flight attempts and proactive limiter waits can run past it. |
| `rate_limit_max` | `int` | `500` | Maximum aggregate requests across all endpoints within the rate-limit window. |
| `rate_limit_window_seconds` | `float` | `5.0` | Length (in seconds) of the rolling rate-limit window. |

## Transport & security

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `verify_tls` | `bool` | `True` | Whether to verify TLS certificates. |
| `proxy` | `str \| None` | `None` | Optional proxy URL routed through for all requests. |
| `user_agent` | `str` | `"stonepy/<version>"` | User-Agent header. Defaults to `stonepy/` plus the package version from `stonepy/_version.py`. |

!!! warning
    Setting `verify_tls=False` disables certificate verification and exposes the connection to interception. Only use it against trusted, isolated test endpoints.

## Extensibility

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `status_decoder` | `StatusDecoder \| LegacyStatusDecoder \| None` | `default_status_decoder` | Replaces top-level numeric instruction/order decoding; accepts a `domain` keyword, with legacy two-argument callables supported. Text execution and nested-order checks stay built in; pass `None` to disable all business-status checks. |

## From the environment

`ClientConfig.from_env()` builds a config from `STONEX_*` environment variables, with optional keyword overrides.

Keyword names and values are statically checked using the public `ClientConfigOverrides`
TypedDict. Use it to annotate an override dictionary passed as `**overrides`; runtime validation
also rejects unknown names.

| Variable | Maps to | Default if unset |
| --- | --- | --- |
| `STONEX_BASE_URL` | `base_url` | `""` |
| `STONEX_APP_KEY` | `app_key` | `""` |
| `STONEX_USERNAME` | `username` | `""` |
| `STONEX_PASSWORD` | `password` | `""` |

Behavior:

- Non-`None` keyword overrides take precedence over environment variables. `None` is ignored
  except for `status_decoder`, where an explicit `None` disables business-status checks. For
  example, `ClientConfig.from_env(app_key="abc")` uses `"abc"` regardless of `STONEX_APP_KEY`.
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
    `from_env()` does not require the `STONEX_*` variables to be set when the corresponding
    values are provided as keyword overrides. Only `base_url` is mandatory; all constructor
    validation rules below apply.

## Validation

`ClientConfig` validates on construction, including through `from_env()`. Invalid types raise
builtin `TypeError`; invalid values raise builtin `ValueError`.

- `base_url` must be a non-blank string without surrounding whitespace, with an `http` or `https`
  scheme, a hostname, a valid port, and no embedded username or password.
- Timeouts, `rate_limit_window_seconds`, and `proactive_refresh_seconds` must be finite positive
  integers or floats.
- `max_connections` and `rate_limit_max` must be positive integers; `max_retries` must be a
  non-negative integer.
- `retry_budget_seconds` must be a finite non-negative number. Booleans are rejected for all
  numeric fields.

## Supplying a custom `status_decoder`

After a successful HTTP response is parsed, the pipeline can raise `OrderRejectedError` based on
the status domain declared by the endpoint spec. `ClientConfig.status_decoder` can replace the
top-level numeric decision. Both callable signatures are supported:

```python
from stonepy._core.status import StatusDecision
from stonepy.extensions import StatusDomain


def decoder(status: int, status_reason: int | None, *, domain: StatusDomain) -> StatusDecision: ...
def legacy_decoder(status: int, status_reason: int | None) -> StatusDecision: ...
```

A decoder receives the endpoint's `INSTRUCTION` or `ORDER` domain through the `domain` keyword
when its signature accepts it. Legacy two-argument callables retain their calling convention.
The signature is inspected once per callable identity; replacing `config.status_decoder` after
client construction takes effect on the next response. Runtime exceptions from a decoder propagate
without retrying the callable. `StatusDecision` is `BusinessStatus | bool | str | None`.

The pipeline interprets its return value as follows:

- `BusinessStatus(is_rejection=..., reason=...)` - used directly.
- `bool` - `True` means rejected with no reason; `False` means accepted.
- `str` - treated as rejected, with the string used as the rejection reason.
- `None` - treated as accepted.

When `ClientConfig` keeps the default callable, the pipeline selects its built-in logic by domain:

- Instruction acknowledgements reject `RedCard` (2) and `Error` (4). An undocumented numeric
  instruction status raises `OrderStatusUnknownError`.
- Order/simulation acknowledgements reject `Rejected` (5) and `RedCard` (10); unknown numeric
  lifecycle values are informational.

Supplying any other callable fully replaces that top-level numeric logic, including the unknown
instruction-code safeguard. Use `domain` to distinguish the two numeric vocabularies, where some
numbers have different meanings. Legacy callables must apply a policy valid for both vocabularies.

### Where the check runs

Business-status checking runs only for endpoint specs with an explicit non-`NONE` `StatusDomain`.
A custom decoder does not broaden checking to read endpoints that merely echo stored status.
Before model validation, acknowledgement responses must carry a usable status. Missing, null,
boolean, or malformed numeric statuses raise `OrderStatusUnknownError`; execution-text statuses
must be non-empty strings. Supplied nested order statuses are checked too.

The custom decoder replaces only the top-level numeric decision. SaveOrder's closed text
`Success`/`Failure` check and instruction responses' nested `Orders[]` checks remain built in;
fixed-margin responses likewise retain their `OrderStatusId` check. Nested quote statuses are out
of scope.

### Writing one

```python
from stonepy import ClientConfig
from stonepy.models import OrderStatus
from stonepy._core.status import BusinessStatus, StatusDecision


def strict_decoder(status: int, status_reason: int | None) -> StatusDecision:
    # Example custom policy: require an OrderStatus-style Accepted code. This same numeric rule
    # also receives instruction statuses, so use it only when that cross-domain policy is wanted.
    if status == int(OrderStatus.Accepted):
        return BusinessStatus(False)
    return BusinessStatus(True, reason=f"status={status} reason={status_reason}")


config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    status_decoder=strict_decoder,
)
```

### Disabling business-status checks

`status_decoder` is `StatusDecoder | LegacyStatusDecoder | None`. Setting it to `None` disables all business-status
checks, including raw acknowledgement, execution-text, and nested-order checks, so no `OrderRejectedError` or
`OrderStatusUnknownError` is raised from a 2xx response (model validation can still fail):

```python
from stonepy import ClientConfig

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    status_decoder=None,  # never raise a business-status exception on 2xx
)
```

An empty acknowledgement body still raises `ResponseParseError` during model validation even
with `status_decoder=None`. Disabling business-status checks does not disable JSON decoding or
response-model validation.

!!! warning
    Setting `status_decoder=None` means a 2xx response whose body reports a rejection or an
    indeterminate acknowledgement can be returned as a normal result if model validation succeeds.
    Inspect the status fields yourself before acting, especially in any flow that places or cancels
    live orders.

!!! note
    `ClientConfig.from_env()` treats `status_decoder` specially: it is only overridden when you pass it explicitly as a keyword. Omitting it keeps `default_status_decoder`; passing `status_decoder=None` is honored as an explicit disable.
