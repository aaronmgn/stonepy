import asyncio
import importlib.metadata
import inspect

import pytest
import respx
from pydantic import BaseModel

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy.extensions import (
    AuthPolicy,
    BaseResource,
    CallContext,
    EndpointSpec,
    Param,
    StatusDomain,
)


def test_public_exports() -> None:
    import stonepy

    expected_exports = {
        "StoneXClient",
        "AsyncStoneXClient",
        "ClientConfig",
        "ClientConfigOverrides",
        "ConfigurationError",
        "StoneXError",
        "StoneXAPIError",
        "AuthenticationError",
        "RateLimitError",
        "OrderRejectedError",
        "OrderStatusUnknownError",
        "ResponseParseError",
        "TransportError",
        "__version__",
    }

    for name in expected_exports:
        assert hasattr(stonepy, name), name

    assert set(stonepy.__all__) == expected_exports

    assert inspect.isclass(stonepy.StoneXClient)
    assert inspect.isclass(stonepy.AsyncStoneXClient)
    assert inspect.isclass(stonepy.ClientConfig)

    assert issubclass(stonepy.StoneXAPIError, stonepy.StoneXError)
    assert issubclass(stonepy.AuthenticationError, stonepy.StoneXError)
    assert issubclass(stonepy.RateLimitError, stonepy.StoneXError)
    assert issubclass(stonepy.OrderRejectedError, stonepy.StoneXError)
    assert issubclass(stonepy.OrderStatusUnknownError, stonepy.StoneXError)
    assert not issubclass(stonepy.OrderStatusUnknownError, stonepy.OrderRejectedError)
    assert issubclass(stonepy.ResponseParseError, stonepy.StoneXError)
    assert issubclass(stonepy.TransportError, stonepy.StoneXError)


def test_public_errors_module_reexports_exception_hierarchy() -> None:
    from stonepy import errors

    assert errors.StoneXError.__name__ == "StoneXError"
    assert errors.TransportError.__name__ == "TransportError"
    assert "ResponseParseError" in errors.__all__
    assert "OrderStatusUnknownError" in errors.__all__


def test_extensions_exports_supported_types() -> None:
    from stonepy import extensions
    from stonepy._core.endpoint import AuthPolicy as InternalAuthPolicy
    from stonepy._core.endpoint import EndpointSpec as InternalEndpointSpec
    from stonepy._core.endpoint import Param as InternalParam
    from stonepy._core.pipeline import CallContext as InternalCallContext
    from stonepy._core.resource import BaseResource as InternalBaseResource
    from stonepy._core.status import StatusDomain as InternalStatusDomain

    expected = {
        "BaseResource": InternalBaseResource,
        "CallContext": InternalCallContext,
        "EndpointSpec": InternalEndpointSpec,
        "Param": InternalParam,
        "AuthPolicy": InternalAuthPolicy,
        "StatusDomain": InternalStatusDomain,
    }
    assert set(extensions.__all__) == set(expected)
    for name, internal in expected.items():
        assert getattr(extensions, name) is internal


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@respx.mock
def test_resource_can_be_constructed_from_public_extensions(async_client: bool) -> None:
    class HealthResponse(BaseModel):
        healthy: bool

    spec = EndpointSpec(
        name="Health",
        method="GET",
        path="/health",
        idempotent=True,
        auth_policy=AuthPolicy.NONE,
        rate_limit_bucket="health",
        response_model=HealthResponse,
        params=(Param("detail", "query", "detail"),),
        status_domain=StatusDomain.NONE,
    )

    class MyResource(BaseResource):
        def health(self) -> HealthResponse:
            return self.call_context.invoke(spec, query={"detail": "short"})

        async def ahealth(self) -> HealthResponse:
            return await self.call_context.ainvoke(spec, query={"detail": "short"})

    def construct(client: StoneXClient | AsyncStoneXClient) -> MyResource:
        shared = client.call_context
        ctx = CallContext(
            config=shared.config,
            transport=shared.transport,
            session=shared.session,
            limiter=shared.limiter,
            retry=shared.retry,
            clock=shared.clock,
            logon=shared.logon,
            alogon=shared.alogon,
        )
        resource = MyResource(ctx)
        assert resource.call_context is ctx
        assert MyResource(shared).call_context is shared
        with pytest.raises(AttributeError):
            resource.call_context = ctx  # type: ignore[misc]
        with pytest.raises(AttributeError):
            client.call_context = ctx  # type: ignore[misc]
        assert client.call_context is shared
        return resource

    route = respx.get("https://api.example/health", params={"detail": "short"}).respond(
        200, json={"healthy": True}
    )
    config = ClientConfig(base_url="https://api.example")
    if async_client:

        async def run() -> HealthResponse:
            async with AsyncStoneXClient(config) as client:
                return await construct(client).ahealth()

        response = asyncio.run(run())
    else:
        with StoneXClient(config) as client:
            response = construct(client).health()
    assert response.healthy is True
    assert route.call_count == 1


def test_removed_plugin_configuration_is_rejected() -> None:
    with pytest.raises(TypeError, match="enable_plugins"):
        ClientConfig(base_url="https://api.example", enable_plugins=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="allow_overrides"):
        ClientConfig(base_url="https://api.example", allow_overrides=())  # type: ignore[call-arg]


def test_clients_do_not_discover_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_discovery(**kwargs: object) -> None:
        pytest.fail("Client construction must not discover entry points")

    monkeypatch.setattr(importlib.metadata, "entry_points", unexpected_discovery)
    config = ClientConfig(base_url="https://api.example")
    with StoneXClient(config) as client:
        assert not hasattr(client, "plugin")
        assert not hasattr(client, "_plugins")

    async def run() -> None:
        async with AsyncStoneXClient(config) as client:
            assert not hasattr(client, "plugin")
            assert not hasattr(client, "_plugins")

    asyncio.run(run())
