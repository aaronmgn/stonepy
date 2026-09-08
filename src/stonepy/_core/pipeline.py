"""Synchronous and asynchronous request pipeline: auth, rate-limit, retry, errors, parsing."""

from __future__ import annotations

import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isfinite
from typing import Any, Never, Protocol, TypeVar, cast, get_origin, runtime_checkable

import httpx
from pydantic import BaseModel, Field, RootModel
from pydantic import ValidationError as PydanticValidationError

from stonepy._core import codec
from stonepy._core.clock import AsyncClock, Clock, system_utc_now
from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.errors import (
    AuthenticationError,
    OrderRejectedError,
    OrderStatusUnknownError,
    RateLimitError,
    ResponseParseError,
    StoneXAPIError,
    StoneXError,
    TransportError,
)
from stonepy._core.logging import SECRET_KEYS
from stonepy._core.models import ResponseModel, UnspecifiedResponse, _remap_response_keys
from stonepy._core.ratelimit import (
    SlidingWindowLimiter,
    backoff_delay,
)
from stonepy._core.retry import RetryPolicy
from stonepy._core.session import AsyncSessionManager, SessionManager, SessionRefreshResult
from stonepy._core.status import (
    BusinessStatus,
    LegacyStatusDecoder,
    StatusDecision,
    StatusDecoder,
    StatusDomain,
    _decode_default_status,
    _UnknownInstructionStatus,
    default_status_decoder,
    normalize_status_decoder,
)
from stonepy._core.transport import Request, build_request

# CIAPI basics guide: when throttling activates (HTTP 429), "the client UI application must
# wait 1 second before sending further API requests".
_MIN_THROTTLE_DELAY_SECONDS = 1.0
logger = logging.getLogger("stonepy.pipeline")

ResponseT = TypeVar("ResponseT", bound=BaseModel)

_SECRET_HEADER_KEYS = SECRET_KEYS


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
    limiter: SlidingWindowLimiter
    retry: RetryPolicy
    clock: Clock
    logon: Callable[[], SessionRefreshResult]
    alogon: Callable[[], Awaitable[SessionRefreshResult]] | None = None
    jitter: Callable[[], float] = _random_jitter
    utc_now: Callable[[], datetime] = system_utc_now
    _decoder_cache: tuple[object, StatusDecoder | None] | None = field(
        default=None, init=False, repr=False
    )

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
            OrderStatusUnknownError: When a write acknowledgement carries an indeterminate status.
            TransportError: When a network failure persists past the retry budget.
            ResponseParseError: When the response body cannot be decoded or validated.
            StoneXAPIError: For other non-2xx responses.
        """
        path_params_dict = dict(path_params or {})
        query_dict = dict(query or {})
        if (
            spec.request_model is not None
            and isinstance(body, BaseModel)
            and not isinstance(body, spec.request_model)
        ):
            cast(type[BaseModel], spec.request_model).model_validate(body)
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
                    try:
                        self.session.refresh(seen_generation, self.logon)
                    except StoneXError:
                        logger.warning(
                            "proactive session refresh failed; continuing with existing token"
                        )

                seen_generation, auth_headers = self.session.snapshot(spec.auth_policy)

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
                raise _map_error(
                    spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
                )

            if _is_rate_limited(resp):
                retry_after = _parse_retry_after(resp, utc_now=self.utc_now)
                delay = self._throttle_delay(attempt, retry_after)
                if self._can_retry_rate_limit(spec, attempt, started_at, delay):
                    self.clock.sleep(delay)
                    attempt += 1
                    continue
                raise _map_error(
                    spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
                )

            if self.retry.should_retry(
                spec=spec,
                response_received=True,
                status=resp.status_code,
                attempt=attempt,
            ):
                delay = self._backoff_delay(attempt, _parse_retry_after(resp, utc_now=self.utc_now))
                if self._within_retry_budget(started_at, delay):
                    self.clock.sleep(delay)
                    attempt += 1
                    continue

            raise _map_error(
                spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
            )

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
        same arguments, return value, retry semantics, and exceptions. Requires an async
        transport and an ``AsyncClock``; synchronous-only components raise ``TypeError``.
        """
        if not isinstance(self.clock, AsyncClock):
            raise TypeError("async paths require an AsyncClock")

        path_params_dict = dict(path_params or {})
        query_dict = dict(query or {})
        if (
            spec.request_model is not None
            and isinstance(body, BaseModel)
            and not isinstance(body, spec.request_model)
        ):
            cast(type[BaseModel], spec.request_model).model_validate(body)
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
                    try:
                        await self._arefresh(seen_generation)
                    except StoneXError:
                        logger.warning(
                            "proactive session refresh failed; continuing with existing token"
                        )

                seen_generation, auth_headers = await self._asnapshot(spec.auth_policy)

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
                raise _map_error(
                    spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
                )

            if _is_rate_limited(resp):
                retry_after = _parse_retry_after(resp, utc_now=self.utc_now)
                delay = self._throttle_delay(attempt, retry_after)
                if self._can_retry_rate_limit(spec, attempt, started_at, delay):
                    await self._asleep(delay)
                    attempt += 1
                    continue
                raise _map_error(
                    spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
                )

            if self.retry.should_retry(
                spec=spec,
                response_received=True,
                status=resp.status_code,
                attempt=attempt,
            ):
                delay = self._backoff_delay(attempt, _parse_retry_after(resp, utc_now=self.utc_now))
                if self._within_retry_budget(started_at, delay):
                    await self._asleep(delay)
                    attempt += 1
                    continue

            raise _map_error(
                spec, resp, _redact_headers(resp.headers), error_info, utc_now=self.utc_now
            )

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

    def _throttle_delay(self, attempt: int, retry_after: float | None) -> float:
        """Delay before retrying a throttled (429) call.

        Every delay is floored at the one second the CIAPI basics guide requires after
        throttling, including zero, expired, or sub-second ``Retry-After`` values.
        """
        delay = self._backoff_delay(attempt, retry_after)
        return max(delay, _MIN_THROTTLE_DELAY_SECONDS)

    def _sync_transport(self) -> _Transport:
        if isinstance(self.transport, _Transport):
            return self.transport
        raise TypeError("CallContext.invoke requires a transport with send()")

    def _async_transport(self) -> _AsyncTransport:
        if isinstance(self.transport, _AsyncTransport):
            return self.transport
        raise TypeError("CallContext.ainvoke requires a transport with asend()")

    def _acquire(self, spec: EndpointSpec[Any]) -> None:
        self.limiter.acquire()

    async def _aacquire(self, spec: EndpointSpec[Any]) -> None:
        await self.limiter.aacquire()

    async def _aneeds_proactive_refresh(self) -> bool:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.aneeds_proactive_refresh()
        return self.session.needs_proactive_refresh()

    async def _ageneration(self) -> int:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.ageneration()
        return self.session.generation

    async def _asnapshot(self, policy: AuthPolicy) -> tuple[int, dict[str, str]]:
        if isinstance(self.session, AsyncSessionManager):
            return await self.session.asnapshot(policy)
        return self.session.snapshot(policy)

    async def _arefresh(self, seen_generation: int) -> None:
        if isinstance(self.session, AsyncSessionManager):
            await self.session.arefresh(seen_generation, self._alogon)
            return
        self.session.refresh(seen_generation, self.logon)

    def commit(
        self, token: str, username: str, do_logon: Callable[[], SessionRefreshResult]
    ) -> None:
        """Commit a manual synchronous logon to the session manager."""
        if not isinstance(self.session, SessionManager):
            raise TypeError("commit requires a SessionManager")
        self.session.commit(token, username, do_logon)

    async def acommit(
        self, token: str, username: str, do_logon: Callable[[], Awaitable[SessionRefreshResult]]
    ) -> None:
        """Commit a manual asynchronous logon to the session manager."""
        if not isinstance(self.session, AsyncSessionManager):
            raise TypeError("acommit requires an AsyncSessionManager")
        await self.session.acommit(token, username, do_logon)

    async def _alogon(self) -> SessionRefreshResult:
        if self.alogon is None:
            raise TypeError("ainvoke requires an async logon callable on the context")
        return await self.alogon()

    def _status_decoder(self) -> StatusDecoder | None:
        decoder = self.config.status_decoder
        if self._decoder_cache is None or decoder is not self._decoder_cache[0]:
            self._decoder_cache = (decoder, normalize_status_decoder(decoder))
        return self._decoder_cache[1]

    def _parse_success(self, spec: EndpointSpec[ResponseT], resp: httpx.Response) -> ResponseT:
        status_decoder = self._status_decoder()
        model = parse_response(spec, resp, status_decoder=status_decoder)
        if (
            not isinstance(model, RootModel)
            and status_decoder is not None
            and spec.status_domain not in {StatusDomain.NONE, StatusDomain.EXECUTION_TEXT}
        ):
            check_business_status(
                model,
                status_decoder,
                status_domain=spec.status_domain,
                method=spec.method,
                path=spec.path,
                http_status=resp.status_code,
            )
        return model

    async def _asleep(self, delay: float) -> None:
        if not isinstance(self.clock, AsyncClock):
            raise TypeError("async paths require an AsyncClock")
        await self.clock.asleep(delay)


def _guard_raw_acknowledgement(
    payload: object,
    *,
    status_domain: StatusDomain,
    method: str,
    path: str,
    http_status: int,
    response_model: type[BaseModel] | None = None,
) -> None:
    """Reject missing or malformed raw statuses before permissive DTO validation."""
    if status_domain is StatusDomain.NONE:
        return

    def guard(value: object, *, numeric: bool = True) -> None:
        usable = False
        if numeric:
            if isinstance(value, (int, str)) and not isinstance(value, bool):
                try:
                    int(value)
                except ValueError:
                    pass
                else:
                    usable = True
        else:
            usable = isinstance(value, str) and bool(value.strip())
        if not usable:
            _raise_unknown_status(
                status=_coerce_status_value(value),
                status_reason=None,
                response=payload,
                method=method,
                path=path,
                http_status=http_status,
            )

    if not isinstance(payload, Mapping):
        guard(None)
        return
    numeric = status_domain is not StatusDomain.EXECUTION_TEXT
    names = _numeric_status_field_names(status_domain)[0] if numeric else ("Status", "status")
    if response_model is not None:
        # A field from another acknowledgement schema must not stand in for this DTO's status.
        declared = set(response_model.model_fields)
        declared.update(
            field.alias for field in response_model.model_fields.values() if field.alias
        )
        names = tuple(name for name in names if name in declared)
    guard(_mapping_object_value(payload, names), numeric=numeric)
    if status_domain is StatusDomain.INSTRUCTION:
        order_names = ("OrderStatusId", "order_status_id")
        if any(
            isinstance(k, str) and k.lower() in {"orderstatusid", "order_status_id"}
            for k in payload
        ):
            guard(_mapping_object_value(payload, order_names))
        orders = _mapping_object_value(payload, ("Orders", "orders"))
        if isinstance(orders, list):
            names = _numeric_status_field_names(StatusDomain.ORDER)[0]
            for order in orders:
                if isinstance(order, Mapping) and any(
                    isinstance(k, str) and k.lower() in {name.lower() for name in names}
                    for k in order
                ):
                    guard(_mapping_object_value(_remap_response_keys(order), names))


def _validation_error_summary(error: PydanticValidationError) -> str:
    """Return locations and error types only (never input values or messages)."""
    errors = error.errors(include_input=False, include_context=False, include_url=False)
    return f"{error.error_count()} validation error(s): " + "; ".join(
        f"{'.'.join(map(str, e['loc']))}: {e['type']}" for e in errors
    )


def parse_response(
    spec: EndpointSpec[ResponseT],
    resp: httpx.Response,
    *,
    status_decoder: StatusDecoder | LegacyStatusDecoder | None = None,
) -> ResponseT:
    """Decode and validate a success response into ``spec.response_model``.

    When *status_decoder* is supplied for an acknowledgement spec, raw statuses are checked
    before model validation. Missing or malformed statuses are indeterminate even when the
    response model would otherwise coerce or discard them. Unspecified response contracts
    normalize empty bodies and JSON null to an empty object, preserving unexpected fields.

    Raises:
        OrderRejectedError: If an execution-text acknowledgement reports ``Failure``.
        OrderStatusUnknownError: If an acknowledgement has no usable status or unknown text status.
        ResponseParseError: If the body is not valid JSON (``phase="decode"``) or does not
            satisfy the response model (``phase="validate"``).
    """
    status_decoder = normalize_status_decoder(status_decoder)
    model_type = spec.response_model
    is_list_root = (
        isinstance(model_type, type)
        and issubclass(model_type, RootModel)
        and get_origin(model_type.model_fields["root"].annotation) is list
    )
    raw_body = resp.content
    parse_error: ResponseParseError | None = None
    try:
        if raw_body:
            payload = codec.loads(raw_body)
        elif spec.status_domain is StatusDomain.NONE:
            payload = [] if is_list_root else {}
        else:
            payload = None
    except ValueError as exc:
        parse_error = ResponseParseError(
            phase="decode",
            http_status=resp.status_code,
            method=spec.method,
            path=spec.path,
            raw_body=raw_body,
            message=f"invalid JSON response ({type(exc).__name__})",
        )
    if parse_error is not None:
        raise parse_error from None
    if issubclass(model_type, UnspecifiedResponse) and payload is None:
        payload = {}
    if status_decoder is not None and spec.status_domain is not StatusDomain.NONE:
        if issubclass(model_type, ResponseModel):
            payload = _remap_response_keys(payload, model_type)
        _guard_raw_acknowledgement(
            payload,
            status_domain=spec.status_domain,
            method=spec.method,
            path=spec.path,
            http_status=resp.status_code,
            response_model=model_type,
        )
    if (
        status_decoder is not None
        and spec.status_domain is StatusDomain.EXECUTION_TEXT
        and isinstance(payload, Mapping)
    ):
        check_business_status(
            cast(Mapping[str, object], payload),
            status_decoder,
            status_domain=spec.status_domain,
            method=spec.method,
            path=spec.path,
            http_status=resp.status_code,
        )
    try:
        model = model_type.model_validate(payload)
    except PydanticValidationError as exc:
        parse_error = ResponseParseError(
            phase="validate",
            http_status=resp.status_code,
            method=spec.method,
            path=spec.path,
            raw_body=raw_body,
            message=_validation_error_summary(exc),
        )
    if parse_error is not None:
        raise parse_error from None
    if status_decoder is not None and spec.status_domain is not StatusDomain.NONE:
        _guard_raw_acknowledgement(
            model.model_dump(by_alias=True, exclude_unset=True),
            status_domain=spec.status_domain,
            method=spec.method,
            path=spec.path,
            http_status=resp.status_code,
            response_model=model_type,
        )
    return model


def check_business_status(
    model: BaseModel | Mapping[str, object],
    status_decoder: StatusDecoder | LegacyStatusDecoder,
    *,
    status_domain: StatusDomain = StatusDomain.ORDER,
    method: str | None = None,
    path: str | None = None,
    http_status: int | None = None,
) -> None:
    """Check one response using its declared business-status domain.

    A custom *status_decoder* replaces only the top-level numeric decision for ``INSTRUCTION``
    and ``ORDER`` domains. SaveOrder's ``EXECUTION_TEXT`` vocabulary and an instruction
    response's nested ``Orders[]`` remain built-in checks. Fixed-margin acknowledgements expose
    that order result as ``OrderStatusId`` rather than ``Orders[]`` and receive the same built-in
    order-domain check. Quote statuses are intentionally out of scope.

    Raises:
        OrderRejectedError: If a status is a documented rejection.
        OrderStatusUnknownError: If a closed acknowledgement domain cannot be interpreted.
    """
    decoder = normalize_status_decoder(status_decoder)
    if decoder is None or status_domain is StatusDomain.NONE:
        return
    if status_domain is StatusDomain.EXECUTION_TEXT:
        _check_execution_text_status(model, method=method, path=path, http_status=http_status)
        return

    _check_numeric_status(
        model,
        decoder,
        status_domain=status_domain,
        response=model,
        method=method,
        path=path,
        http_status=http_status,
    )
    if status_domain is StatusDomain.INSTRUCTION:
        _check_instruction_order_statuses(model, method=method, path=path, http_status=http_status)


def _check_numeric_status(
    model: BaseModel | Mapping[str, object],
    status_decoder: StatusDecoder,
    *,
    status_domain: StatusDomain,
    response: object,
    method: str | None,
    path: str | None,
    http_status: int | None,
) -> None:
    status_names, reason_names = _numeric_status_field_names(status_domain)
    status_value = _field_value(model, status_names)
    if status_value is None:
        return
    try:
        status = int(status_value)
    except (TypeError, ValueError):
        _raise_unknown_status(
            status=status_value,
            status_reason=None,
            response=response,
            method=method,
            path=path,
            http_status=http_status,
        )

    status_reason_value = _field_value(model, reason_names)
    try:
        status_reason = None if status_reason_value is None else int(status_reason_value)
    except (TypeError, ValueError):
        _raise_unknown_status(
            status=status,
            status_reason=None,
            response=response,
            method=method,
            path=path,
            http_status=http_status,
        )

    decision: StatusDecision
    if status_decoder is default_status_decoder:
        try:
            decision = _decode_default_status(status_domain, status, status_reason)
        except _UnknownInstructionStatus:
            _raise_unknown_status(
                status=status,
                status_reason=status_reason,
                response=response,
                method=method,
                path=path,
                http_status=http_status,
            )
    else:
        decision = status_decoder(status, status_reason, domain=status_domain)
    rejected, reason = _decode_rejection(decision)
    if rejected:
        raise OrderRejectedError(
            status=status,
            status_reason=status_reason,
            reason=reason,
            response=response,
            method=method,
            path=path,
            http_status=http_status,
        )


def _numeric_status_field_names(
    status_domain: StatusDomain,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if status_domain is StatusDomain.INSTRUCTION:
        return (
            ("Status", "status", "InstructionStatusId", "instruction_status_id"),
            (
                "StatusReason",
                "status_reason",
                "InstructionStatusReasonId",
                "instruction_status_reason_id",
            ),
        )
    if status_domain is StatusDomain.ORDER:
        return (
            ("Status", "status", "OrderStatusId", "order_status_id"),
            (
                "StatusReason",
                "status_reason",
                "OrderStatusReasonId",
                "order_status_reason_id",
            ),
        )
    raise ValueError(f"numeric status fields cannot use {status_domain.value!r}")


def _check_instruction_order_statuses(
    model: BaseModel | Mapping[str, object],
    *,
    method: str | None,
    path: str | None,
    http_status: int | None,
) -> None:
    # FixedMarginOrderResponseDTO exposes the resulting order status beside its instruction
    # status (Docs/reference/data-types/FixedMarginOrderResponseDTO.md), rather than in Orders[].
    if _field_value(model, ("OrderStatusId", "order_status_id")) is not None:
        _check_numeric_status(
            model,
            default_status_decoder,
            status_domain=StatusDomain.ORDER,
            response=model,
            method=method,
            path=path,
            http_status=http_status,
        )

    orders = _field_object_value(model, ("Orders", "orders"))
    if not isinstance(orders, list):
        return
    for order in orders:
        if not isinstance(order, (BaseModel, Mapping)):
            continue
        _check_numeric_status(
            cast(BaseModel | Mapping[str, object], order),
            default_status_decoder,
            status_domain=StatusDomain.ORDER,
            response=model,
            method=method,
            path=path,
            http_status=http_status,
        )


def _check_execution_text_status(
    model: BaseModel | Mapping[str, object],
    *,
    method: str | None,
    path: str | None,
    http_status: int | None,
) -> None:
    """Accept Success, reject Failure, and fail closed on every other supplied value."""
    status_value = _field_value(model, ("Status", "status"))
    if status_value is None:
        return
    if not isinstance(status_value, str):
        _raise_unknown_status(
            status=status_value,
            status_reason=None,
            response=model,
            method=method,
            path=path,
            http_status=http_status,
        )

    normalized = status_value.strip().lower()
    if normalized == "success":
        return
    if normalized == "failure":
        reason_value = _field_value(model, ("Reason", "reason", "StatusReason", "status_reason"))
        reason = str(reason_value) if reason_value is not None else status_value
        raise OrderRejectedError(
            status=status_value,
            status_reason=None,
            reason=reason,
            response=model,
            method=method,
            path=path,
            http_status=http_status,
        )
    _raise_unknown_status(
        status=status_value,
        status_reason=None,
        response=model,
        method=method,
        path=path,
        http_status=http_status,
    )


def _raise_unknown_status(
    *,
    status: int | str | None,
    status_reason: int | None,
    response: object,
    method: str | None,
    path: str | None,
    http_status: int | None,
) -> Never:
    raise OrderStatusUnknownError(
        status=status,
        status_reason=status_reason,
        response=response,
        method=method,
        path=path,
        http_status=http_status,
    )


def map_error(
    spec: EndpointSpec[Any],
    resp: httpx.Response,
    *,
    utc_now: Callable[[], datetime] = system_utc_now,
) -> StoneXAPIError:
    """Map a non-2xx response to the most specific ``StoneXAPIError`` subclass.

    Returns an [`AuthenticationError`][stonepy.AuthenticationError] for auth failures, a
    [`RateLimitError`][stonepy.RateLimitError] for HTTP 429, or a plain
    [`StoneXAPIError`][stonepy.StoneXAPIError] otherwise. Secret headers are redacted.
    """
    return _map_error(
        spec, resp, _redact_headers(resp.headers), _parse_error_info(resp), utc_now=utc_now
    )


def _should_refresh_auth(
    spec: EndpointSpec[Any], resp: httpx.Response, error_info: _ErrorInfo
) -> bool:
    if spec.auth_policy is AuthPolicy.NONE:
        return False
    if error_info.error_code == 4010:
        return False
    return resp.status_code == 401 or error_info.error_code == 4011


def _map_error(
    spec: EndpointSpec[Any],
    resp: httpx.Response,
    headers: Mapping[str, str],
    error_info: _ErrorInfo,
    *,
    utc_now: Callable[[], datetime] = system_utc_now,
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
    if _is_rate_limited(resp):
        return RateLimitError(
            http_status=error_info.http_status,
            error_code=error_info.error_code,
            error_message=error_info.error_message,
            method=spec.method,
            path=spec.path,
            raw_body=error_info.raw_body,
            headers=headers,
            retry_after=_parse_retry_after(resp, utc_now=utc_now),
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
        fallback = (
            f"{resp.reason_phrase or 'HTTP error'}; response body length={len(raw_body)} bytes"
        )
        return _ErrorInfo(resp.status_code, None, fallback, raw_body)

    message = dto.error_message if dto.error_message is not None else resp.reason_phrase
    return _ErrorInfo(resp.status_code, dto.error_code, message, raw_body)


def _parse_retry_after(
    resp: httpx.Response, *, utc_now: Callable[[], datetime] = system_utc_now
) -> float | None:
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
    return max(0.0, (retry_at.astimezone(UTC) - utc_now()).total_seconds())


def _is_rate_limited(resp: httpx.Response) -> bool:
    return resp.status_code == 429


def _field_value(
    model: BaseModel | Mapping[str, object], names: tuple[str, ...]
) -> int | str | None:
    return _coerce_status_value(_field_object_value(model, names))


def _field_object_value(model: BaseModel | Mapping[str, object], names: tuple[str, ...]) -> object:
    if isinstance(model, BaseModel):
        value = _mapping_object_value(model.model_dump(by_alias=True), names)
        if value is not None:
            return value
        return _mapping_object_value(model.model_dump(), names)

    return _mapping_object_value(model, names)


def _mapping_object_value(mapping: Mapping[Any, Any], names: tuple[str, ...]) -> object:
    for name in names:
        if name in mapping:
            return mapping[name]

    lower_names = {name.lower() for name in names}
    for key, value in mapping.items():
        if isinstance(key, str) and key.lower() in lower_names:
            return value
    return None


def _coerce_status_value(value: object) -> int | str | None:
    """Return a status/reason value only when it is an int or str code, else None.

    Status codes arrive as a JSON number or string; any value that is neither an ``int`` nor a
    ``str`` is treated as absent rather than coerced.
    """
    if isinstance(value, (int, str)) and not isinstance(value, bool):
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
