# Extensibility

stonepy can be extended in three independent ways, all driven by `ClientConfig`:

- **Out-of-tree resource plugins** - ship your own resource group in a separate package, register it with a packaging entry point, and reach it through `client.plugin("name")`.
- **`allow_overrides`** - permit a plugin to shadow a built-in resource name.
- **A custom `status_decoder`** - change how the response pipeline decides whether a business `Status` field means "rejected".

Everything below is grounded in the actual loader (`src/stonepy/_core/plugins.py`), the base class (`src/stonepy/_core/resource.py`), the status types (`src/stonepy/_core/status.py`), the client wiring (`src/stonepy/client.py`), and `ClientConfig` (`src/stonepy/_core/config.py`).

## 1. Writing a plugin resource

A plugin resource is any subclass of `BaseResource`. The base class is intentionally tiny:

```python
# src/stonepy/_core/resource.py
ABI_VERSION: int = 1


class BaseResource:
    def __init__(self, ctx: CallContext) -> None:
        self._ctx = ctx
```

The constructor takes a single `CallContext` and stores it as `self._ctx`. That context is the only thing your resource needs: it exposes `self._ctx.invoke(spec, ...)` (sync) and `self._ctx.ainvoke(spec, ...)` (async), which run the full pipeline (auth refresh, rate limiting, retries, error mapping, response parsing, and the business-status check).

!!! note
    `BaseResource` is imported from the internal module `stonepy._core.resource` - that exact import path is the ABI surface plugins depend on. The built-in generated resources import it the same way (for example `src/stonepy/resources/cfd/__init__.py` does `from stonepy._core.resource import BaseResource`). It is not re-exported from the top-level `stonepy` package, so import it from `stonepy._core.resource` directly.

### A minimal plugin resource

The methods on your resource are ordinary Python methods. To call the StoneX API you build an `EndpointSpec` (from `stonepy._core.endpoint`) and pass it to `self._ctx.invoke(...)`, exactly as the generated endpoint modules do. Here is a read-only resource that lists CFD markets through a hand-written spec:

```python
# my_stonepy_plugin/resource.py
from __future__ import annotations

from stonepy._core.endpoint import AuthPolicy, EndpointSpec, Param
from stonepy._core.resource import BaseResource
from stonepy.models import ListCfdMarketsResponseDTO

_LIST_MARKETS = EndpointSpec(
    name="ListCfdMarkets",
    method="GET",
    path="/cfd/markets",
    idempotent=True,
    auth_policy=AuthPolicy.SESSION,
    rate_limit_bucket="cfd",
    response_model=ListCfdMarketsResponseDTO,
    params=(
        Param(name="ClientAccountId", location="query", python_name="client_account_id"),
        Param(name="maxResults", location="query", python_name="max_results"),
    ),
)


class CfdExtrasResource(BaseResource):
    # Optional version-compat contract; see section on requires_stonepy below.
    requires_stonepy = ">=0.1.0"

    def list_markets(self, client_account_id: int, *, max_results: int = 20) -> ListCfdMarketsResponseDTO:
        return self._ctx.invoke(
            _LIST_MARKETS,
            query={"ClientAccountId": client_account_id, "maxResults": max_results},
        )
```

!!! note
    The `query` keys you pass to `invoke` are the wire names (the `Param.name` values), not the Python names. This mirrors the generated endpoint modules under `src/stonepy/_endpoints/`.

### Registering it via a packaging entry point

The loader discovers plugins from the entry-point group **`stonepy.resources`**. This is the exact group name read in `discover_plugin_resources`:

```python
# src/stonepy/_core/plugins.py
discovered = (
    entry_points
    if entry_points is not None
    else metadata_entry_points(group="stonepy.resources")
)
```

Declare the entry point in your plugin package's `pyproject.toml`. The entry-point **name** becomes the key you pass to `client.plugin(...)`, and the value must point at a `BaseResource` subclass:

```toml
# my_stonepy_plugin/pyproject.toml
[project.entry-points."stonepy.resources"]
cfd_extras = "my_stonepy_plugin.resource:CfdExtrasResource"
```

After installing that package into the same environment as stonepy, the resource is discoverable under the name `cfd_extras`.

### Enabling and accessing the plugin

Plugin discovery is **off by default**. Turn it on with `ClientConfig(enable_plugins=True)`. The client loads and instantiates every discovered plugin at construction time and stores them in an internal dict; `client.plugin(name)` returns the instance:

```python
from stonepy import ClientConfig, StoneXClient

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    app_key="your-app-key",
    username="your-username",
    password="your-password",
    enable_plugins=True,
)

with StoneXClient(config) as client:
    extras = client.plugin("cfd_extras")  # the CfdExtrasResource instance
    markets = extras.list_markets(client_account_id=12345, max_results=10)
```

The same works for `AsyncStoneXClient`; both clients build their `_plugins` dict identically in `__init__` and both expose `def plugin(self, name: str) -> BaseResource`.

!!! note
    `client.plugin(name)` does a plain dict lookup and raises `KeyError` if the name was never loaded (plugins disabled, package not installed, entry point not declared, or the plugin was skipped during loading). There is no fallback.

!!! warning
    When `enable_plugins=False` (the default), `discover_plugin_resources` returns `{}` immediately and no entry points are read at all. Plugins only load when you opt in.

### How loading and validation work (fail-loud vs fail-soft)

`load_plugin_resources` enforces a precise set of rules. Understanding which conditions raise and which are silently skipped matters for debugging:

- **Name collides with a built-in** - if an entry-point name is one of the 19 built-in resource names and is **not** listed in `allow_overrides`, loading raises `ValueError("plugin resource '<name>' collides with a built-in; add it to allow_overrides to override")`. This is fail-loud, raised during client construction.
- **Duplicate plugin name** - if two entry points declare the same name, loading raises `ValueError("plugin resource '<name>' was declared more than once")`. Fail-loud.
- **`ep.load()` raises** - if importing/loading the entry point throws, the loader logs a warning (`logger = logging.getLogger("stonepy.plugins")`) and **continues**, skipping that plugin. Fail-soft.
- **Loaded object is not a `BaseResource` subclass** - if `ep.load()` does not return a class that is a subclass of `BaseResource`, the loader logs a warning and **continues**, skipping it. Fail-soft.
- **`requires_stonepy` mismatch or invalid** - raises `ValueError` (see below). Fail-loud.

The built-in names that count as collisions are exactly the `known` set passed in from `client.py`:

```text
cfd, client_preference, clientapplication, clientpreference, fixedmargin, margin, market,
message, news, order, order_including_closed, pm, preference, price_alert, session, spread,
tradingadvisor, user_account, watchlist
```

!!! tip
    Because a failed `ep.load()` is only logged (not raised), enable the `stonepy.plugins` logger while developing a plugin so you can see why a resource silently failed to appear:

    ```python
    import logging
    logging.getLogger("stonepy.plugins").setLevel(logging.WARNING)
    logging.basicConfig()
    ```

### Version-compatibility contract: `requires_stonepy`

`stonepy._core.resource` defines `ABI_VERSION = 1`, but the loader does **not** check that integer. The compatibility contract that the loader actually enforces is an **optional** class attribute named `requires_stonepy` on your resource class, validated by `_check_requires_stonepy`:

- If the attribute is absent (`None`), no check is performed.
- If present but not a `str`, loading raises `ValueError("plugin resource '<name>' has invalid requires_stonepy")`.
- If present and the current stonepy version does not satisfy it, loading raises `ValueError("plugin resource '<name>' requires stonepy <req>, but current version is <ver>")`.

The requirement string is a comma-separated list of simple constraints. Each part must match operator + version, where the operator is one of `>=`, `<=`, `>`, `<`, `==`, and the version is one to three dotted numeric components (for example `">=0.1.0"`, `">=0.1,<0.2"`). A part that does not match this shape raises `ValueError("invalid requires_stonepy requirement: <req>")`.

Version comparison uses only the first three dotted components; any non-numeric component is treated as `0` and missing components are padded with `0`. The current version comes from `importlib.metadata.version("stonepy")`, falling back to `"0.1.0"` if the package metadata is not found.

## 2. `allow_overrides` semantics

`ClientConfig.allow_overrides` is a `tuple[str, ...]` (default `()`). It is the allow-list of names that a plugin is permitted to share with a built-in resource. It only affects the collision check described above:

- A plugin name that matches a built-in name is rejected with `ValueError` **unless** that name is in `allow_overrides`.
- Adding the name to `allow_overrides` lets the plugin load under that name into the `_plugins` dict.

```python
from stonepy import ClientConfig

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    enable_plugins=True,
    allow_overrides=("order",),  # permit a plugin named "order"
)
```

!!! warning
    `allow_overrides` does **not** replace the built-in resource property. The built-in `client.order` property still returns the generated `OrderResource`; the overriding plugin is only reachable through `client.plugin("order")`. The two coexist - `allow_overrides` simply suppresses the collision error so the plugin can be loaded alongside the built-in.

## 3. Supplying a custom `status_decoder`

After a successful HTTP response is parsed, the pipeline can raise `OrderRejectedError` based on
the status domain declared by the endpoint spec. `ClientConfig.status_decoder` can replace the
top-level numeric decision, and has this backward-compatible type:

```python
# src/stonepy/_core/status.py
StatusDecision: TypeAlias = BusinessStatus | bool | str | None
StatusDecoder: TypeAlias = Callable[[int, int | None], StatusDecision]
```

A decoder receives `(status, status_reason)` (the `status_reason` may be `None`) and returns a
`StatusDecision`. It is called for the top-level status on both `INSTRUCTION` and `ORDER` specs;
the signature does not include the domain. The pipeline interprets its return value as follows:

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
instruction-code safeguard. The custom callable therefore needs a policy that is valid for both
numeric vocabularies, even though some numbers have different meanings between them.

### Where the check runs

Business-status checking runs only for endpoint specs with an explicit non-`NONE` `StatusDomain`.
A custom decoder does not broaden checking to read endpoints that merely echo stored status.

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

`status_decoder` is `StatusDecoder | None`. Setting it to `None` disables all business-status
checks, including execution-text and nested-order checks, so no `OrderRejectedError` or
`OrderStatusUnknownError` is raised from a 2xx response:

```python
from stonepy import ClientConfig

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    status_decoder=None,  # never raise a business-status exception on 2xx
)
```

!!! warning
    Setting `status_decoder=None` means a 2xx response whose body reports a rejection or an indeterminate acknowledgement will be returned as a normal result. Inspect the status fields yourself before acting, especially in any flow that places or cancels live orders.

!!! note
    `ClientConfig.from_env()` treats `status_decoder` specially: it is only overridden when you pass it explicitly as a keyword. Omitting it keeps `default_status_decoder`; passing `status_decoder=None` is honored as an explicit disable.
