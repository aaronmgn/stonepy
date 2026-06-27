"""Endpoint metadata emitted by the generator and consumed by the pipeline."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class AuthPolicy(enum.Enum):
    NONE = "none"
    SESSION = "session"


@dataclass(frozen=True)
class Param:
    name: str
    location: Literal["path", "query", "body"]
    python_name: str


@dataclass(frozen=True)
class EndpointSpec(Generic[ResponseT]):
    name: str
    method: str
    path: str
    idempotent: bool
    auth_policy: AuthPolicy
    rate_limit_bucket: str
    response_model: type[ResponseT]
    request_model: type | None = None
    params: tuple[Param, ...] = field(default_factory=tuple)
