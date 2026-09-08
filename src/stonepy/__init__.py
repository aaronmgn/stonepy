"""stonepy: a typed Python client for the StoneX (City Index / CIAPI) v2 trading API.

Exposes the synchronous [`StoneXClient`][stonepy.StoneXClient] and asynchronous
[`AsyncStoneXClient`][stonepy.AsyncStoneXClient], the [`ClientConfig`][stonepy.ClientConfig]
used to construct them, and the public exception hierarchy rooted at
[`StoneXError`][stonepy.StoneXError]. Generated request and response models live in
``stonepy.models``; [`UnspecifiedResponse`][stonepy.UnspecifiedResponse] represents results
whose catalog contracts document no response body.
"""

from stonepy._core.config import ClientConfig, ClientConfigOverrides
from stonepy._core.errors import (
    AuthenticationError,
    ConfigurationError,
    OrderRejectedError,
    OrderStatusUnknownError,
    RateLimitError,
    ResponseParseError,
    StoneXAPIError,
    StoneXError,
    TransportError,
)
from stonepy._core.models import UnspecifiedResponse
from stonepy._version import __version__
from stonepy.client import AsyncStoneXClient, StoneXClient

__all__ = [
    "AsyncStoneXClient",
    "AuthenticationError",
    "ClientConfig",
    "ClientConfigOverrides",
    "ConfigurationError",
    "OrderRejectedError",
    "OrderStatusUnknownError",
    "RateLimitError",
    "ResponseParseError",
    "StoneXAPIError",
    "StoneXClient",
    "StoneXError",
    "TransportError",
    "UnspecifiedResponse",
    "__version__",
]
