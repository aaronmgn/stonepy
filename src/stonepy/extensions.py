"""Supported types for explicitly constructed out-of-tree resources.

Subclass ``BaseResource`` and use ``self.call_context.invoke(spec)`` or, with an asynchronous
context, ``await self.call_context.ainvoke(spec)``. A client's read-only ``call_context`` property
provides its shared state. It can also supply the components of an explicit ``CallContext``::

    from stonepy import ClientConfig, StoneXClient
    from stonepy.extensions import BaseResource, CallContext

    class MyResource(BaseResource):
        '''An application-specific resource group.'''

    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
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

Usually ``MyResource(client.call_context)`` is sufficient. Resources share the caller's
transport lifetime and must finish their calls before the client closes.
"""

from stonepy._core.endpoint import AuthPolicy, EndpointSpec, Param
from stonepy._core.pipeline import CallContext
from stonepy._core.resource import BaseResource
from stonepy._core.status import StatusDomain

__all__ = ["AuthPolicy", "BaseResource", "CallContext", "EndpointSpec", "Param", "StatusDomain"]
