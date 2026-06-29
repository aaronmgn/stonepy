"""Endpoint metadata emitted by the generator and consumed by the pipeline."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class AuthPolicy(enum.Enum):
    """Whether an endpoint requires a session token.

    Attributes:
        NONE: The endpoint is called unauthenticated (for example, logon).
        SESSION: The endpoint requires a valid session token, refreshed as needed.
    """

    NONE = "none"
    SESSION = "session"


@dataclass(frozen=True)
class Param:
    """A single request parameter binding for an endpoint.

    Attributes:
        name: The wire parameter name expected by the API (its alias).
        location: Where the value is sent - in the URL path, query string, or body.
        python_name: The snake_case name of the wrapper argument that supplies the value.
    """

    name: str
    location: Literal["path", "query", "body"]
    python_name: str


@dataclass(frozen=True)
class EndpointSpec(Generic[ResponseT]):
    """Immutable description of one API endpoint, consumed by the request pipeline.

    Generated as a module-level constant per endpoint and passed to
    [`CallContext.invoke`][stonepy._core.pipeline.CallContext.invoke].

    Attributes:
        name: The catalog endpoint name identifying this endpoint (for example,
            ``"ChangePassword"``).
        method: The HTTP method (for example ``"GET"`` or ``"POST"``).
        path: The URL path template, which may contain ``{placeholder}`` segments.
        idempotent: Whether the call is safe to retry automatically.
        auth_policy: Whether the call requires a session token.
        rate_limit_bucket: The limiter bucket this endpoint shares with its siblings.
        response_model: The Pydantic model the response body is validated against.
        request_model: The Pydantic model for the request body, if any.
        params: The ordered path, query, and body parameter bindings.
        host_rooted: Whether ``path`` is resolved against the server host root rather than the
            configured base URL. CIAPI serves its v2 session and account endpoints from
            ``/v2`` at the host root, not under the ``/TradingAPI`` base.
    """

    name: str
    method: str
    path: str
    idempotent: bool
    auth_policy: AuthPolicy
    rate_limit_bucket: str
    response_model: type[ResponseT]
    request_model: type | None = None
    params: tuple[Param, ...] = field(default_factory=tuple)
    host_rooted: bool = False
