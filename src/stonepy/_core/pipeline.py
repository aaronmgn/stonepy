"""Synchronous and asynchronous request pipeline: auth, rate-limit, retry, errors, parsing."""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isfinite
from typing import Any, Protocol, TypeVar, cast, get_origin, runtime_checkable

import httpx
from pydantic import BaseModel, Field, RootModel
from pydantic import ValidationError as PydanticValidationError

from stonepy._core import codec
from stonepy._core.clock import AsyncClock, Clock
from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.errors import (
    AuthenticationError,
    OrderRejectedError,
    RateLimitError,
    ResponseParseError,
    StoneXAPIError,
    TransportError,
)
from stonepy._core.models import ResponseModel
from stonepy._core.ratelimit import (
    BucketedSlidingWindowLimiter,
    SlidingWindowLimiter,
    backoff_delay,
)
from stonepy._core.retry import RetryPolicy
from stonepy._core.session import AsyncSessionManager, SessionManager, SessionRefreshResult
from stonepy._core.status import (
    BusinessStatus,
    StatusDecision,
    StatusDecoder,
    default_status_decoder,
)
from stonepy._core.transport import Request, build_request

ResponseT = TypeVar("ResponseT", bound=BaseModel)

_SECRET_HEADER_KEYS = {
    "api-key",
    "app-key",
    "app_key",
    "appkey",
    "authorization",
    "cookie",
    "password",
    "proxy-authorization",
    "session",
    "set-cookie",
    "x-api-key",
}


def _random_jitter() -> float:
    return random.random()


__all__ = [
    "ApiErrorResponseDTO",
    "BusinessStatus",
    "CallContext",
    "StatusDecoder",
    "check_business_status",
    "map_error",
    "parse_response",
]


@runtime_checkable
class _Transport(Protocol):
    """Structural type for a synchronous transport the pipeline can drive."""

    def send(self, req: Request) -> httpx.Response:
        """Send *req* and return the HTTP response."""
        ...


@runtime_checkable
class _AsyncTransport(Protocol):
    """Structural type for an asynchronous transport the pipeline can drive."""

    async def asend(self, req: Request) -> httpx.Response:
        """Send *req* and return the HTTP response."""
        ...


class ApiErrorResponseDTO(ResponseModel):
    """The StoneX error envelope parsed from a non-2xx response body."""

    error_code: int | None = Field(default=None, alias="ErrorCode")
    """The StoneX ``ErrorCode``, if the body carried one."""
    error_message: str | None = Field(default=None, alias="ErrorMessage")
    """The human-readable error message, if present."""
    http_status: int | None = Field(default=None, alias="HttpStatus")
    """The HTTP status echoed in the body, if present."""


@dataclass(frozen=True)
class _ErrorInfo:
    http_status: int
    error_code: int | None
    error_message: str | None
    raw_body: bytes | None


@dataclass
class CallContext:
    """Shared, per-client state that drives every request through the pipeline.

    Bundles the configuration, transport, session manager, rate limiter, retry policy, and
    clock that [`invoke`][stonepy._core.pipeline.CallContext.invoke] and
    [`ainvoke`][stonepy._core.pipeline.CallContext.ainvoke] use to execute an
    [`EndpointSpec`][stonepy._core.endpoint.EndpointSpec]: acquiring rate-limit slots,
    attaching auth headers, sending the request, refreshing the session on auth errors,
    retrying idempotent failures within the budget, and parsing or mapping the response.
    """

    config: ClientConfig
    transport: _Transport | _AsyncTransport
    session: SessionManager | AsyncSessionManager
    limiter: SlidingWindowLimiter | BucketedSlidingWindowLimiter
    retry: RetryPolicy
    clock: Clock
    logon: Callable[[], SessionRefreshResult]
    alogon: Callable[[], Awaitable[SessionRefreshResult]] | None = None
    jitter: Callable[[], float] = _random_jitter

    def invoke(
        self,
        spec: EndpointSpec[ResponseT],
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        body: Mapping[str, object] | BaseModel | None = None,
    ) -> ResponseT:
        """Execute *spec* synchronously and return the parsed response model.

        Acquires a rate-limit slot, attaches session auth headers (refreshing proactively or
        after a 401/expired-token error), sends the request, and retries idempotent transport
        and rate-limit failures within the configured retry budget.

        Args:
            spec: The endpoint to call.
            path_params: Values substituted into ``{placeholder}`` path segments.
            query: Query-string parameters.
            body: The request body, as a model or a mapping.

        Returns:
            The validated response model declared by ``spec.response_model``.

        Raises:
            AuthenticationError: On unrecoverable authentication failures.
            RateLimitError: When rate-limit retries are exhausted.
            OrderRejectedError: When an order response carries a rejection status.
            TransportError: When a network failure persists past the retry budget.
            ResponseParseError: When the response body cannot be decoded or validated.
            StoneXAPIError: For other non-2xx responses.
        """
        path_params_dict = dict(path_params or {})
        query_dict = dict(query or {})
        body_dict = _body_to_dict(body)
        attempt = 0
        auth_refresh_used = False
        started_at = self.clock.now()
        transport = self._sync_transport()

        while True:
            if spec.auth_policy is AuthPolicy.NONE:
                seen_generation = 0
                auth_headers: dict[str, str] = {}
            else:
                seen_generation = self.session.generation
                if self.session.needs_proactive_refresh():
                    self.session.refresh(seen_generation, self.logon)

                seen_generation = self.session.generation
                auth_headers = self.session.auth_headers(spec.auth_policy)

            req = build_request(
                self.config.base_url,
                spec,
                path_params=path_params_dict,
                query=query_dict,
                body_dict=body_dict,
                auth_headers=auth_headers,
                user_agent=self.config.user_agent,
            )
            self._acquire(spec)

            try:
                resp = transport.send(req)
            except httpx.TransportError as exc:
                delay = self._backoff_delay(attempt, None)
                if self._can_retry_transport_error(spec, attempt, started_at, delay):
                    self.clock.sleep(delay)
                    attempt += 1
                    continue
                raise TransportError(
                    str(exc),
                    method=spec.method,
                    path=spec.path,
                    attempt=attempt,
                ) from exc

            if 200 <= resp.status_code < 300:
                return self._parse_success(spec, resp)

            error_info = _parse_error_info(resp)
            if _should_refresh_auth(spec, resp, error_info):
                if not auth_refresh_used and self._within_retry_budget(started_at, 0.0):
                    self.session.refresh(seen_generation, self.logon)
                    auth_refresh_used = True
                    if self._within_retry_budget(started_at, 0.0):
                        continue
                raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

            if _is_rate_limited(resp, error_info):
                retry_after = _parse_retry_after(resp)
                delay = self._backoff_delay(attempt, retry_after)
                if self._can_retry_rate_limit(spec, attempt, started_at, delay):
                    self.clock.sleep(delay)
                    attempt += 1
                    continue
                raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

            if self.retry.should_retry(
                spec=spec,
                response_received=True,
                status=resp.status_code,
                attempt=attempt,
            ):
                delay = self._backoff_delay(attempt, _parse_retry_after(resp))
                if self._within_retry_budget(started_at, delay):
                    self.clock.sleep(delay)
                    attempt += 1
                    continue

            raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

    async def ainvoke(
        self,
        spec: EndpointSpec[ResponseT],
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        body: Mapping[str, object] | BaseModel | None = None,
    ) -> ResponseT:
        """Execute *spec* asynchronously and return the parsed response model.

        The awaitable twin of [`invoke`][stonepy._core.pipeline.CallContext.invoke], with the
        same arguments, return value, retry semantics, and exceptions. Falls back to the
        synchronous path when the transport exposes no ``asend`` coroutine.
        """
        if not callable(getattr(self.transport, "asend", None)):
            return self.invoke(spec, path_params=path_params, query=query, body=body)

        path_params_dict = dict(path_params or {})
        query_dict = dict(query or {})
        body_dict = _body_to_dict(body)
        attempt = 0
        auth_refresh_used = False
        started_at = self.clock.now()
        transport = self._async_transport()

        while True:
            if spec.auth_policy is AuthPolicy.NONE:
                seen_generation = 0
                auth_headers: dict[str, str] = {}
            else:
                seen_generation = await self._ageneration()
                if await self._aneeds_proactive_refresh():
                    await self._arefresh(seen_generation)

                seen_generation = await self._ageneration()
                auth_headers = await self._aauth_headers(spec.auth_policy)

            req = build_request(
                self.config.base_url,
                spec,
                path_params=path_params_dict,
                query=query_dict,
                body_dict=body_dict,
                auth_headers=auth_headers,
                user_agent=self.config.user_agent,
            )
            await self._aacquire(spec)

            try:
                resp = await transport.asend(req)
            except httpx.TransportError as exc:
                delay = self._backoff_delay(attempt, None)
                if self._can_retry_transport_error(spec, attempt, started_at, delay):
                    await self._asleep(delay)
                    attempt += 1
                    continue
                raise TransportError(
                    str(exc),
                    method=spec.method,
                    path=spec.path,
                    attempt=attempt,
                ) from exc

            if 200 <= resp.status_code < 300:
                return self._parse_success(spec, resp)

            error_info = _parse_error_info(resp)
            if _should_refresh_auth(spec, resp, error_info):
                if not auth_refresh_used and self._within_retry_budget(started_at, 0.0):
                    await self._arefresh(seen_generation)
                    auth_refresh_used = True
                    if self._within_retry_budget(started_at, 0.0):
                        continue
                raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

            if _is_rate_limited(resp, error_info):
                retry_after = _parse_retry_after(resp)
                delay = self._backoff_delay(attempt, retry_after)
                if self._can_retry_rate_limit(spec, attempt, started_at, delay):
                    await self._asleep(delay)
                    attempt += 1
                    continue
                raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

            if self.retry.should_retry(
                spec=spec,
                response_received=True,
                status=resp.status_code,
                attempt=attempt,
            ):
                delay = self._backoff_delay(attempt, _parse_retry_after(resp))
                if self._within_retry_budget(started_at, delay):
                    await self._asleep(delay)
                    attempt += 1
                    continue

            raise _map_error(spec, resp, _redact_headers(resp.headers), error_info)

    def _can_retry_transport_error(
        self, spec: EndpointSpec[Any], attempt: int, started_at: float, delay: float
    ) -> bool:
        return self.retry.should_retry(
            spec=spec,
            response_received=False,
            status=None,
            attempt=attempt,
        ) and self._within_retry_budget(started_at, delay)

    def _can_retry_rate_limit(
        self, spec: EndpointSpec[Any], attempt: int, started_at: float, delay: float
    ) -> bool:
        return self.retry.should_retry_rate_limit(spec=spec, attempt=attempt) and (
            self._within_retry_budget(started_at, delay)
        )

    def _within_retry_budget(self, started_at: float, delay: float) -> bool:
        return (self.clock.now() + delay - started_at) <= self.config.retry_budget_seconds

    def _backoff_delay(self, attempt: int, retry_after: float | None) -> float:
        jitter = 1.0 if retry_after is not None else self.jitter()
        return backoff_delay(attempt, retry_after, jitter=jitter)

    def _sync_transport(self) -> _Transport:
        if isinstance(self.transport, _Transport):
            return self.transport
        raise TypeError("CallContext.invoke requires a transport with send()")

    def _async_transport(self) -> _AsyncTransport:
        if isinstance(self.transport, _AsyncTransport):
            return self.transport
        raise TypeError("CallContext.ainvoke requires a transport with asend()")

    def _acquire(self, spec: EndpointSpec[Any]) -> None:
        if isinstance(self.limiter, BucketedSlidingWindowLimiter):
            self.limiter.acquire(spec.rate_limit_bucket)
            return
        self.limiter.acquire()

    async def _aacquire(self, spec: EndpointSpec[Any]) -> None:
        if isinstance(self.limiter, BucketedSlidingWindowLimiter):
            await self.limiter.aacquire(spec.rate_limit_bucket)
            return
        await self.limiter.aacquire()

    async def _aneeds_proactive_refresh(self) -> bool:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.aneeds_proactive_refresh()
        return self.session.needs_proactive_refresh()

    async def _ageneration(self) -> int:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.ageneration()
        return self.session.generation

    async def _aauth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.aauth_headers(policy)
        return self.session.auth_headers(policy)

    async def _arefresh(self, seen_generation: int) -> None:
        if isinstance(self.session, AsyncSessionManager):
            await self.session.arefresh(seen_generation, self._alogon)
            return
        self.session.refresh(seen_generation, self.logon)

    async def _alogon(self) -> SessionRefreshResult:
        if self.alogon is not None:
            return await self.alogon()
        return self.logon()

    def _parse_success(self, spec: EndpointSpec[ResponseT], resp: httpx.Response) -> ResponseT:
        model = parse_response(spec, resp)
        if (
            not isinstance(model, RootModel)
            and self.config.status_decoder is not None
            and _should_check_business_status(spec, self.config.status_decoder)
        ):
            check_business_status(
                model,
                self.config.status_decoder,
                method=spec.method,
                path=spec.path,
                http_status=resp.status_code,
            )
        return model

    async def _asleep(self, delay: float) -> None:
        if isinstance(self.clock, AsyncClock):
            await self.clock.asleep(delay)
            return
        self.clock.sleep(delay)


def parse_response(spec: EndpointSpec[ResponseT], resp: httpx.Response) -> ResponseT:
    """Decode and validate a success response into ``spec.response_model``.

    Raises:
        ResponseParseError: If the body is not valid JSON (``phase="decode"``) or does not
            satisfy the response model (``phase="validate"``).
    """
    model_type = spec.response_model
    is_list_root = (
        isinstance(model_type, type)
        and issubclass(model_type, RootModel)
        and get_origin(model_type.model_fields["root"].annotation) is list
    )
    raw_body = resp.content or (b"[]" if is_list_root else b"{}")
    try:
        payload = codec.loads(raw_body)
    except ValueError as exc:
        raise ResponseParseError(
            phase="decode",
            http_status=resp.status_code,
            method=spec.method,
            path=spec.path,
            raw_body=raw_body,
            message=str(exc),
        ) from exc
    try:
        return model_type.model_validate(payload)
    except PydanticValidationError as exc:
        raise ResponseParseError(
            phase="validate",
            http_status=resp.status_code,
            method=spec.method,
            path=spec.path,
            raw_body=raw_body,
            message=str(exc),
        ) from exc


def check_business_status(
    model: BaseModel | Mapping[str, object],
    status_decoder: StatusDecoder,
    *,
    method: str | None = None,
    path: str | None = None,
    http_status: int | None = None,
) -> None:
    """Raise [`OrderRejectedError`][stonepy.OrderRejectedError] if a model carries a rejection.

    Reads the ``Status`` (and optional ``StatusReason``) fields and runs them through
    *status_decoder*. Returns without error when the model has no status field or the status
    is not a rejection.
    """
    status_value = _field_value(model, ("Status", "status"))
    if status_value is None:
        return

    status = int(status_value)
    status_reason_value = _field_value(
        model,
        ("StatusReason", "status_reason", "StatusReasonId", "statusReason"),
    )
    status_reason = None if status_reason_value is None else int(status_reason_value)
    rejected, reason = _decode_rejection(status_decoder(status, status_reason))
    if not rejected:
        return

    raise OrderRejectedError(
        status=status,
        status_reason=status_reason,
        reason=reason,
        response=model,
        method=method,
        path=path,
        http_status=http_status,
    )


def map_error(spec: EndpointSpec[Any], resp: httpx.Response) -> StoneXAPIError:
    """Map a non-2xx response to the most specific ``StoneXAPIError`` subclass.

    Returns an [`AuthenticationError`][stonepy.AuthenticationError] for auth failures, a
    [`RateLimitError`][stonepy.RateLimitError] for HTTP 429, or a plain
    [`StoneXAPIError`][stonepy.StoneXAPIError] otherwise. Secret headers are redacted.
    """
    return _map_error(spec, resp, _redact_headers(resp.headers), _parse_error_info(resp))


def _should_refresh_auth(
    spec: EndpointSpec[Any], resp: httpx.Response, error_info: _ErrorInfo
) -> bool:
    if spec.auth_policy is AuthPolicy.NONE:
        return False
    if error_info.error_code == 4010:
        return False
    return resp.status_code == 401 or error_info.error_code == 4011


def _should_check_business_status(spec: EndpointSpec[Any], status_decoder: StatusDecoder) -> bool:
    if status_decoder is default_status_decoder:
        return spec.rate_limit_bucket == "order"
    return True


def _map_error(
    spec: EndpointSpec[Any],
    resp: httpx.Response,
    headers: Mapping[str, str],
    error_info: _ErrorInfo,
) -> StoneXAPIError:
    if error_info.error_code in {4010, 4011} or resp.status_code == 401:
        return AuthenticationError(
            http_status=error_info.http_status,
            error_code=error_info.error_code,
            error_message=error_info.error_message,
            method=spec.method,
            path=spec.path,
            raw_body=error_info.raw_body,
            headers=headers,
        )
    if _is_rate_limited(resp, error_info):
        return RateLimitError(
            http_status=error_info.http_status,
            error_code=error_info.error_code,
            error_message=error_info.error_message,
            method=spec.method,
            path=spec.path,
            raw_body=error_info.raw_body,
            headers=headers,
            retry_after=_parse_retry_after(resp),
        )
    return StoneXAPIError(
        http_status=error_info.http_status,
        error_code=error_info.error_code,
        error_message=error_info.error_message,
        method=spec.method,
        path=spec.path,
        raw_body=error_info.raw_body,
        headers=headers,
    )


def _body_to_dict(body: Mapping[str, object] | BaseModel | None) -> dict[str, object] | None:
    if body is None:
        return None
    if isinstance(body, BaseModel):
        return cast(
            dict[str, object],
            body.model_dump(by_alias=True, exclude_unset=True, mode="python"),
        )
    return dict(body)


def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: "***" if key.lower() in _SECRET_HEADER_KEYS else value
        for key, value in headers.items()
    }


def _parse_error_info(resp: httpx.Response) -> _ErrorInfo:
    raw_body = resp.content or None
    if raw_body is None:
        return _ErrorInfo(resp.status_code, None, resp.reason_phrase, None)

    try:
        dto = ApiErrorResponseDTO.model_validate(codec.loads(raw_body))
    except (TypeError, ValueError):
        fallback = resp.text or resp.reason_phrase
        return _ErrorInfo(resp.status_code, None, fallback, raw_body)

    message = dto.error_message if dto.error_message is not None else resp.reason_phrase
    return _ErrorInfo(resp.status_code, dto.error_code, message, raw_body)


def _parse_retry_after(resp: httpx.Response) -> float | None:
    raw_value = resp.headers.get("Retry-After")
    if raw_value is None:
        return None
    value = raw_value.strip()
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(0.0, seconds) if isfinite(seconds) else None

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max(0.0, (retry_at.astimezone(UTC) - datetime.now(UTC)).total_seconds())


def _is_rate_limited(resp: httpx.Response, error_info: _ErrorInfo) -> bool:
    return resp.status_code == 429


def _field_value(
    model: BaseModel | Mapping[str, object], names: tuple[str, ...]
) -> int | str | None:
    if isinstance(model, BaseModel):
        value = _mapping_field_value(model.model_dump(by_alias=True), names)
        if value is not None:
            return value
        return _mapping_field_value(model.model_dump(), names)

    return _mapping_field_value(model, names)


def _mapping_field_value(mapping: Mapping[Any, Any], names: tuple[str, ...]) -> int | str | None:
    for name in names:
        if name in mapping:
            return _coerce_status_value(mapping[name])

    lower_names = {name.lower() for name in names}
    for key, value in mapping.items():
        if isinstance(key, str) and key.lower() in lower_names:
            return _coerce_status_value(value)
    return None


def _coerce_status_value(value: object) -> int | str | None:
    """Return a status/reason value only when it is an int or str code, else None.

    Status codes arrive as a JSON number or string; any value that is neither an ``int`` nor a
    ``str`` is treated as absent rather than coerced.
    """
    if isinstance(value, (int, str)):
        return value
    return None


def _decode_rejection(decision: StatusDecision) -> tuple[bool, str | None]:
    if isinstance(decision, BusinessStatus):
        return decision.is_rejection, decision.reason
    if isinstance(decision, bool):
        return decision, None
    if decision is None:
        return False, None
    return True, decision
