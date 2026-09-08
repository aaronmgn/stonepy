# Extensibility

## Subclass `BaseResource` and pass a `CallContext`

Import the supported extension types from `stonepy.extensions`: `BaseResource`, `CallContext`,
`EndpointSpec`, `Param`, `AuthPolicy`, and `StatusDomain`. Construct your resource explicitly with
`MyResource(client.call_context)` or a `CallContext` you assemble yourself. Both clients expose
`call_context`; resources access the same context through `self.call_context`.

```python
from pydantic import BaseModel

from stonepy import ClientConfig, StoneXClient
from stonepy.extensions import AuthPolicy, BaseResource, EndpointSpec, StatusDomain


class HealthResponse(BaseModel):
    healthy: bool


_HEALTH = EndpointSpec(
    name="Health",
    method="GET",
    path="/health",
    idempotent=True,
    auth_policy=AuthPolicy.NONE,
    rate_limit_bucket="health",
    response_model=HealthResponse,
    status_domain=StatusDomain.NONE,
)


class MyResource(BaseResource):
    """Resource for an application-specific health endpoint."""

    def health(self) -> HealthResponse:
        """Read the application's health endpoint."""
        return self.call_context.invoke(_HEALTH)


with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
    resource = MyResource(client.call_context)
    # For an API that implements /health:
    response = resource.health()
```

For an async resource, define `async def health` and use
`return await self.call_context.ainvoke(_HEALTH)`. Prefer reusing
`AsyncStoneXClient.call_context`, which already supplies the async components and logon callback.
If you assemble the context yourself, async invocation requires a transport with `asend()` and
an `AsyncClock`-capable clock with `asleep()`. For a context using `AsyncSessionManager`, also
provide an `alogon` callable that returns an awaitable: when refresh needs that callback,
`alogon=None` raises `TypeError` instead of falling back to synchronous `logon`.
Synchronous-only clocks or transports also raise `TypeError`; `ainvoke()` no longer falls back
to synchronous invocation.

Session mutations on an `AsyncSessionManager` must also be awaited. Reach it through
`manager = client.call_context.session`, then use `await manager.aset_token(token, username)`,
`await manager.aclear(expected_token=...)`, or
`await manager.arefresh(seen_generation, do_logon)` with an awaitable logon callback.
The synchronous `set_token()`, `clear()`, and `refresh()` methods raise `TypeError` without
changing state or running a logon callback. Synchronous read accessors remain available.
Use `ainvoke()` with an async session manager: a hand-built context passed to `invoke()` raises
`TypeError` if it tries to refresh that manager. Synchronous contexts should use `SessionManager`.

The callback takes no arguments and resolves to either a token string (retaining the current
username) or a `(token, username)` pair: `Callable[[], Awaitable[str | tuple[str, str]]]`.
`arefresh()` returns `None`; it updates the manager or reuses a peer's newer generation.
Capture `seen_generation` before deciding to refresh so concurrent callers can share that result.
`client.call_context.session` is typed as `SessionManager | AsyncSessionManager`, even on an
async client. Neither `AsyncSessionManager` nor the `SessionRefreshResult` alias is re-exported
by `stonepy` or `stonepy.extensions`; the example explicitly depends on the internal
`stonepy._core.session` module to narrow the union:

```python
from collections.abc import Awaitable, Callable

from stonepy import AsyncStoneXClient
from stonepy._core.session import AsyncSessionManager


async def refresh_session(
    client: AsyncStoneXClient,
    fetch_session: Callable[[], Awaitable[tuple[str, str]]],
) -> None:
    manager = client.call_context.session
    assert isinstance(manager, AsyncSessionManager)
    seen_generation = await manager.ageneration()

    async def do_logon() -> str | tuple[str, str]:
        return await fetch_session()

    await manager.arefresh(seen_generation, do_logon)  # Returns None.
```

Supply `fetch_session` as your async credential-acquisition function. It runs while the manager's
lock is held, so it must obtain credentials independently of this manager; calling this client's
`session.log_on()` or another manager mutator inside the callback would reacquire that lock.
To avoid an internal import, define a runtime-checkable `Protocol` with the `ageneration()` and
`arefresh()` signatures above and narrow with `isinstance(manager, YourProtocol)` instead.

When seeding a manual token that needs its own callback for a 401 refresh/replay, use
`await manager.acommit(token, username, alogon)` to install both together; `aset_token()` leaves
any existing manual callback unchanged and does not install one on a fresh manager.
An installed manual callback takes precedence over the callback passed to `arefresh()`.

The `call_context` properties are read-only references to mutable, shared call state. Reusing a
client's context shares its authentication, rate limiter, retry policy, and transport. Complete
resource calls before closing that client; constructing a resource does not transfer transport
ownership. The `stonepy.extensions` module docstring also shows explicit `CallContext` construction.

Entry-point plugin discovery and registration support have been removed. To migrate, remove
the `stonepy.resources` entry-point registration,
`enable_plugins`, `allow_overrides`, `requires_stonepy`, and `ABI_VERSION`, and replace
`client.plugin("name")` with `MyResource(client.call_context)`.

For business-status customization, see [custom status decoders](configuration.md#supplying-a-custom-status_decoder).
