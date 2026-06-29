"""Base Pydantic models for requests and responses."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, RootModel, model_validator

from stonepy._core.codec import StoneXDateTime

__all__ = [
    "ListResponse",
    "PassthroughResponseModel",
    "RequestModel",
    "ResponseModel",
    "ScalarResponse",
    "StoneXDateTime",
    "StoneXModel",
]

ItemT = TypeVar("ItemT", bound=BaseModel)
ScalarT = TypeVar("ScalarT")


class StoneXModel(BaseModel):
    """Base model for every generated StoneX DTO.

    Enables ``populate_by_name`` so fields can be set with their snake_case Python names or
    their upstream PascalCase aliases, and ``use_attribute_docstrings`` so each generated
    field's docstring also becomes its JSON-schema description. ``model_config`` is merged
    across subclasses, so both behaviors apply to every request and response model.
    """

    model_config = ConfigDict(populate_by_name=True, use_attribute_docstrings=True)


class RequestModel(StoneXModel):
    """Base model for request bodies. Rejects unknown fields (``extra="forbid"``).

    Forbidding extras surfaces typos and stale fields as validation errors before a request
    is sent, rather than silently dropping them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ResponseModel(StoneXModel):
    """Base model for response bodies. Ignores unknown fields (``extra="ignore"``).

    Ignoring extras lets the client tolerate new or undocumented fields the API adds without
    raising, so responses keep parsing across upstream changes.

    Response keys are matched to field aliases case-insensitively: CIAPI's v2 endpoints return
    camelCase JSON (for example ``clientAccountWatchlists``) while the generated models alias
    fields with the catalog's PascalCase (``ClientAccountWatchlists``). Without this, an
    exact-case match would miss every camelCase key and ``extra="ignore"`` would silently drop
    the data, leaving the parsed model empty. The remap runs at every nesting level because each
    nested model is itself a ``ResponseModel``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _match_keys_case_insensitively(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        canonical: dict[str, str] = {}
        for name, field in cls.model_fields.items():
            target = field.alias or name
            canonical.setdefault(name.lower(), target)
            if field.alias:
                canonical.setdefault(field.alias.lower(), target)
        remapped: dict[str, Any] = {}
        for key, value in data.items():
            target = canonical.get(key.lower(), key) if isinstance(key, str) else key
            remapped.setdefault(target, value)
        return remapped


class ListResponse(RootModel[list[ItemT]], Generic[ItemT]):
    """Response wrapper for endpoints whose success body is a bare top-level JSON array.

    CIAPI's order-query endpoints (for example ``order.get_orders``) return a top-level JSON array
    rather than an object, which an ordinary ``ResponseModel`` cannot validate. Their
    ``response_model`` is set to ``ListResponse[Item]``; the pipeline validates each element as
    ``Item`` and the generated wrapper returns ``root`` (a ``list[Item]``), so callers receive a
    plain list. Each element is still a ``ResponseModel``, so case-insensitive key matching applies.
    """


class ScalarResponse(RootModel[ScalarT], Generic[ScalarT]):
    """Response wrapper for endpoints whose success body is a bare top-level JSON scalar.

    A few CIAPI endpoints (for example ``user_account.get_charting_enabled``) return a bare scalar
    such as ``true`` rather than an object. Their ``response_model`` is set to ``ScalarResponse[T]``
    and the generated wrapper returns ``root`` (a ``T``), so callers receive the plain value.
    """


class PassthroughResponseModel(StoneXModel):
    """Response model that retains unknown fields (``extra="allow"``).

    Used for endpoints whose response type is not described in the catalog: every field is
    preserved on the model instance so callers can still read the raw payload.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")
