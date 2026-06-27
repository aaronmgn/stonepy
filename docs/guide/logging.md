# Logging and Secret Redaction

stonepy is deliberately quiet. It does not log your HTTP requests, responses,
headers, or payloads. The only place the library writes to the standard
`logging` module is plugin discovery, and credentials are stripped from object
reprs before they can ever reach a log line, a traceback, or your console.

This guide covers two distinct mechanisms:

1. The stdlib `logging` usage (one logger, warnings only).
2. Secret redaction at the `repr()` level, which protects `ClientConfig` and
   the internal `Request` object regardless of how you log them.

## What stonepy logs

stonepy uses Python's standard `logging` module in exactly one module:
`stonepy._core.plugins`. It creates a single named logger:

```python
logger = logging.getLogger("stonepy.plugins")
```

That logger emits `WARNING` records only, and only during out-of-tree plugin
discovery (which is off unless you set `enable_plugins=True` on your
`ClientConfig`). The two messages are:

```python
logger.warning("plugin %s failed to load: %s; continuing", ep.name, exc)
logger.warning("plugin %s did not load a BaseResource subclass; continuing", ep.name)
```

!!! note
    There is no request/response logging built into stonepy. The client does
    not log URLs, auth headers, order payloads, or rate-limit activity. If you
    need wire-level tracing you must enable it on the underlying HTTP stack (see
    the caution at the end of this guide).

## Enabling logging

Because stonepy logs through the stdlib, you control it with the normal logging
configuration. The logger name `stonepy.plugins` lives under the `stonepy`
hierarchy, so configuring `stonepy` captures it:

```python
import logging

# Simplest: configure the root logger and let propagation carry stonepy records.
logging.basicConfig(level=logging.WARNING)

# Or target the stonepy hierarchy specifically.
stonepy_logger = logging.getLogger("stonepy")
stonepy_logger.setLevel(logging.WARNING)
```

A failed plugin load then produces output similar to:

```text
WARNING:stonepy.plugins:plugin acme_orders failed to load: No module named 'acme'; continuing
```

!!! tip
    Set the level on `"stonepy"` (the parent) rather than `"stonepy.plugins"` if
    you want a single switch that will also pick up any future stonepy loggers.

## How secrets are redacted

Redaction in stonepy happens when an object is converted to its string
representation, not inside a logging handler. This means a credential is hidden
whether it appears in a deliberate `log.info(config)`, an f-string, a `print()`,
or an exception that captures the object. The helpers live in
`stonepy._core.logging`.

The core primitive replaces any non-empty value with a fixed mask (it does not
truncate or partially reveal the value):

```python
def redact(value: str) -> str:
    if not value:
        return value
    return "***"
```

### The default secret key set

`safe_repr()` decides which keys to mask using this set, defined in
`stonepy/_core/logging.py`:

```python
_DEFAULT_SECRET_KEYS = {"app_key", "appkey", "authorization", "password", "proxy", "session"}
```

Matching is case-insensitive: every candidate key is lowercased before it is
compared against this set, so `Password`, `AppKey`, `Session`, and `Authorization`
all match. Any matching value is rendered as `'***'`.

### The secret query-string key set

URL query parameters are redacted separately, in
`stonepy/_core/transport.py`, using an identical set of names:

```python
_SECRET_QUERY_KEYS = {"app_key", "appkey", "authorization", "password", "proxy", "session"}
```

When the internal `Request` object is repr'd, `_redact_url_query()` parses the
URL's query string and masks any parameter whose (lowercased) name is in that
set, leaving the rest intact.

## ClientConfig repr redaction

`ClientConfig` is a dataclass, and its `__repr__` delegates straight to
`safe_repr`:

```python
def __repr__(self) -> str:
    return safe_repr(self)
```

For a dataclass instance, `safe_repr` rebuilds the repr field by field, masking
any field whose name is in the default secret key set. Given:

```python
from stonepy import ClientConfig

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    app_key="SECRET-KEY",
    username="alice",
    password="hunter2",
    proxy="http://corp-proxy:9999",
)
print(repr(config))
```

you get (truncated for readability) - note `app_key`, `password`, and `proxy`
are masked while non-secret fields such as `username` and `base_url` are shown
verbatim:

```text
ClientConfig(base_url='https://ciapi.cityindex.com/TradingAPI', app_key='***', username='alice', password='***', ..., proxy='***', user_agent='stonepy/0.1.3', ...)
```

!!! note
    `username` is not in the secret set, so it is printed in full. Only
    `app_key`, `password`, and `proxy` among the credential-bearing
    `ClientConfig` fields are masked.

## Request repr redaction

The internal `Request` dataclass (used to build every HTTP call) defines a
custom `__repr__` that redacts on three fronts: the URL query string, the
headers mapping, and the params mapping. The body content is never shown - only
its length:

```python
def __repr__(self) -> str:
    content = "None" if self.content is None else f"<redacted {len(self.content)} bytes>"
    return (
        f"{type(self).__qualname__}(method={self.method!r}, "
        f"url={_redact_url_query(self.url)!r}, "
        f"headers={safe_repr(self.headers)}, params={safe_repr(self.params)}, "
        f"content={content})"
    )
```

For mappings, `safe_repr` returns a dict whose secret-keyed values are replaced
with `'***'`. A representative repr looks like:

```text
Request(method='GET', url='https://ciapi.cityindex.com/TradingAPI/order/123?Session=***&UserName=alice&Password=***', headers={'Authorization': '***', 'Session': '***', 'UserName': 'alice'}, params={'Session': '***', 'MarketId': '99'}, content=<redacted 7 bytes>)```

Here `Session`, `Password`, and `Authorization` are masked in both the URL and
the headers/params, while `UserName` and `MarketId` pass through, and the request
body is reduced to a byte count.

## Custom secret keys

`safe_repr` accepts an optional `secret_keys` argument that is merged (after
lowercasing) into the defaults:

```python
def safe_repr(obj: object, secret_keys: set[str] | None = None) -> str:
    ...
```

So calling `safe_repr(some_mapping, secret_keys={"token"})` masks `token` in
addition to the six default keys.

!!! warning
    This extra-keys capability is an internal helper in `stonepy._core.logging`;
    it is not exported from the public `stonepy` API. The two redaction sites
    that ship with stonepy - `ClientConfig.__repr__` (which calls
    `safe_repr(self)`) and `Request.__repr__` (which calls `safe_repr(...)` on
    headers and params) - do not pass any custom keys, so in normal use only the
    six default keys are redacted. There is no `ClientConfig` setting to register
    additional secret key names.

## Caution: the HTTP layer is not redacted

stonepy's redaction only applies to its own `ClientConfig` and `Request`
reprs. The underlying transport is `httpx`, which has its own loggers
(for example `httpx` and `httpcore`). If you enable `DEBUG`-level logging on the
root logger or on those loggers, httpx may emit request URLs and connection
details that stonepy does not redact - and those URLs can contain `Session`,
`AppKey`, and similar query parameters in clear text.

!!! warning
    Avoid enabling `logging.basicConfig(level=logging.DEBUG)` (or DEBUG on the
    `httpx`/`httpcore` loggers) in production, or raise their level explicitly to
    keep credentials out of your logs:

    ```python
    import logging

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    ```
