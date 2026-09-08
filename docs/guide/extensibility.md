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

The `call_context` properties are read-only references to mutable, shared call state. Reusing a
client's context shares its authentication, rate limiter, retry policy, and transport. Complete
resource calls before closing that client; constructing a resource does not transfer transport
ownership. The `stonepy.extensions` module docstring also shows explicit `CallContext` construction.

Entry-point plugin discovery and registration support have been removed. To migrate, remove
the `stonepy.resources` entry-point registration,
`enable_plugins`, `allow_overrides`, `requires_stonepy`, and `ABI_VERSION`, and replace
`client.plugin("name")` with `MyResource(client.call_context)`.

For business-status customization, see [custom status decoders](configuration.md#supplying-a-custom-status_decoder).
