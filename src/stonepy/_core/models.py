"""Base Pydantic models for requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from stonepy._core.codec import StoneXDateTime

__all__ = [
    "PassthroughResponseModel",
    "RequestModel",
    "ResponseModel",
    "StoneXDateTime",
    "StoneXModel",
]


class StoneXModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RequestModel(StoneXModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ResponseModel(StoneXModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PassthroughResponseModel(StoneXModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")
