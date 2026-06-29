"""stonepy: a typed Python client for the StoneX (City Index / CIAPI) v2 trading API.

Exposes the synchronous [`StoneXClient`][stonepy.StoneXClient] and asynchronous
[`AsyncStoneXClient`][stonepy.AsyncStoneXClient], the [`ClientConfig`][stonepy.ClientConfig]
used to construct them, and the public exception hierarchy rooted at
[`StoneXError`][stonepy.StoneXError]. Request and response models live in ``stonepy.models``.
"""

from stonepy._core.config import ClientConfig
from stonepy._core.errors import (
    AuthenticationError,
    OrderRejectedError,
    RateLimitError,
    ResponseParseError,
    StoneXAPIError,
    StoneXError,
    TransportError,
)
from stonepy.client import AsyncStoneXClient, StoneXClient

__version__ = "0.2.1"

__all__ = [
    "AsyncStoneXClient",
    "AuthenticationError",
    "ClientConfig",
    "OrderRejectedError",
    "RateLimitError",
    "ResponseParseError",
    "StoneXAPIError",
    "StoneXClient",
    "StoneXError",
    "TransportError",
    "__version__",
]
