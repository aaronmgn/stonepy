from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime
from typing import cast

import httpx
import pytest
from pydantic import Field

from stonepy import __version__
from stonepy._core import codec
from stonepy._core.clock import FakeClock
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
from stonepy._core.models import RequestModel, ResponseModel
from stonepy._core.pipeline import (
    BusinessStatus,
    CallContext,
    check_business_status,
    map_error,
    parse_response,
)
from stonepy._core.ratelimit import BucketedSlidingWindowLimiter, SlidingWindowLimiter
from stonepy._core.retry import RetryPolicy
from stonepy._core.session import AsyncSessionManager, SessionManager
from stonepy._core.status import default_status_decoder
from stonepy._core.transport import Request


class _Resp(ResponseModel):
    order_id: int = Field(alias="OrderId")


class _AmountResp(ResponseModel):
    amount: Decimal = Field(alias="Amount")


class _StatusResp(ResponseModel):
    status: int = Field(alias="Status")
    status_reason: int | None = Field(default=None, alias="StatusReason")


class _Body(RequestModel):
    required: int = Field(alias="Required")
    optional_value: int | None = Field(default=None, alias="OptionalValue")


class FakeTransport:
    def __init__(self, responses: list[httpx.Response | BaseException]) -> None:
        self._responses = responses
        self.sent: list[Request] = []

    def send(self, req: Request) -> httpx.Response:
        self.sent.append(req)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self) -> None:  # pragma: no cover
        pass


class AsyncFakeTransport:
    def __init__(self, responses: list[httpx.Response | BaseException]) -> None:
        self._responses = responses
        self.sent: list[Request] = []

    async def asend(self, req: Request) -> httpx.Response:
        self.sent.append(req)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _RacingSession:
    def __init__(self) -> None:
        self._generation = 1
        self._token = "OLD"
        self.refresh_seen_generations: list[int] = []

    @property
    def generation(self) -> int:
        return self._generation

    def needs_proactive_refresh(self) -> bool:
        self._generation = 2
        self._token = "OTHER"
        return True

    def refresh(self, seen_generation: int, do_logon: Callable[[], str]) -> None:
        self.refresh_seen_generations.append(seen_generation)
        if self._generation > seen_generation:
            return
        self._token = do_logon()
        self._generation += 1

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        if policy is AuthPolicy.NONE:
            return {}
        return {"Session": self._token, "UserName": "alice"}


class _ExplodingSession:
    @property
    def generation(self) -> int:
        raise AssertionError("AuthPolicy.NONE must not read session generation")

    def needs_proactive_refresh(self) -> bool:
        raise AssertionError("AuthPolicy.NONE must not check proactive refresh")

    def refresh(self, seen_generation: int, do_logon: Callable[[], str]) -> None:
        raise AssertionError("AuthPolicy.NONE must not refresh")

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        raise AssertionError("AuthPolicy.NONE must not read auth headers")


class _NestedLogonSession:
    def __init__(self) -> None:
        self._in_logon = False
        self.logon_calls = 0

    @property
    def generation(self) -> int:
        if self._in_logon:
            raise AssertionError("nested AuthPolicy.NONE invoke touched session generation")
        return 1

    def needs_proactive_refresh(self) -> bool:
        if self._in_logon:
            raise AssertionError("nested AuthPolicy.NONE invoke checked proactive refresh")
        return True

    def refresh(self, seen_generation: int, do_logon: Callable[[], str]) -> None:
        if self._in_logon:
            raise AssertionError("nested AuthPolicy.NONE invoke refreshed session")
        self.logon_calls += 1
        self._in_logon = True
        try:
            do_logon()
        finally:
            self._in_logon = False

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        if self._in_logon:
            raise AssertionError("nested AuthPolicy.NONE invoke read auth headers")
        if policy is AuthPolicy.NONE:
            return {}
        return {"Session": "NEW", "UserName": "alice"}


@dataclass(frozen=True)
class _ContextParts:
    ctx: CallContext
    clock: FakeClock


def _one_jitter() -> float:
    return 1.0


def _ctx(
    transport: FakeTransport,
    logon_tokens: list[str],
    *,
    retry: RetryPolicy | None = None,
    config: ClientConfig | None = None,
    jitter: Callable[[], float] = _one_jitter,
    status_decoder: Callable[[int, int | None], BusinessStatus | bool | str | None] | None = None,
) -> _ContextParts:
    clk = FakeClock()
    cfg = config or ClientConfig(base_url="https://api.example")
    if status_decoder is not None:
        cfg.status_decoder = status_decoder
    sm = SessionManager(clock=clk, proactive_refresh_seconds=1080)
    sm.set_token("OLD", "alice")
    tokens = iter(logon_tokens)
    return _ContextParts(
        ctx=CallContext(
            config=cfg,
            transport=transport,
            session=sm,
            clock=clk,
            limiter=BucketedSlidingWindowLimiter(
                cfg.rate_limit_max,
                cfg.rate_limit_window_seconds,
                clk,
            ),
            retry=retry or RetryPolicy(3),
            logon=lambda: next(tokens),
            jitter=jitter,
        ),
        clock=clk,
    )


async def _actx(
    transport: AsyncFakeTransport,
    logon_tokens: list[str],
    *,
    retry: RetryPolicy | None = None,
    config: ClientConfig | None = None,
    jitter: Callable[[], float] = _one_jitter,
) -> _ContextParts:
    clk = FakeClock()
    cfg = config or ClientConfig(base_url="https://api.example")
    sm = AsyncSessionManager(clock=clk, proactive_refresh_seconds=1080)
    await sm.aset_token("OLD", "alice")
    tokens = iter(logon_tokens)

    async def alogon() -> str:
        return next(tokens)

    return _ContextParts(
        ctx=CallContext(
            config=cfg,
            transport=cast(FakeTransport, transport),
            session=cast(SessionManager, sm),
            clock=clk,
            limiter=BucketedSlidingWindowLimiter(
                cfg.rate_limit_max,
                cfg.rate_limit_window_seconds,
                clk,
            ),
            retry=retry or RetryPolicy(3),
            logon=lambda: "SYNC-SHOULD-NOT-RUN",
            alogon=alogon,
            jitter=jitter,
        ),
        clock=clk,
    )


def _spec(*, method: str = "GET", idempotent: bool = True) -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name="GetOrder",
        method=method,
        path="/order/{OrderId}",
        idempotent=idempotent,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        response_model=_Resp,
    )


def _bucket_spec(bucket: str) -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name=f"Bucket{bucket}",
        method="GET",
        path=f"/bucket/{bucket}",
        idempotent=True,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket=bucket,
        response_model=_Resp,
    )


def _amount_spec() -> EndpointSpec[_AmountResp]:
    return EndpointSpec(
        name="Amount",
        method="GET",
        path="/amount",
        idempotent=True,
        auth_policy=AuthPolicy.NONE,
        rate_limit_bucket="default",
        response_model=_AmountResp,
    )


def _body_spec() -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name="PostBody",
        method="POST",
        path="/body",
        idempotent=False,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        response_model=_Resp,
        request_model=_Body,
    )


def _status_spec(*, bucket: str = "order") -> EndpointSpec[_StatusResp]:
    return EndpointSpec(
        name="Status",
        method="POST",
        path="/status",
        idempotent=False,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket=bucket,
        response_model=_StatusResp,
    )


def test_happy_path_parses_response() -> None:
    t = FakeTransport([httpx.Response(200, json={"OrderId": 7})])
    out = _ctx(t, []).ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7


def test_ainvoke_delegates_to_pipeline() -> None:
    t = FakeTransport([httpx.Response(200, json={"OrderId": 7})])
    out = asyncio.run(_ctx(t, []).ctx.ainvoke(_spec(), path_params={"OrderId": 7}))
    assert out.order_id == 7


def test_ainvoke_uses_async_transport_when_available() -> None:
    t = AsyncFakeTransport([httpx.Response(200, content=b'{"Amount":1.30}')])
    clk = FakeClock()
    ctx = CallContext(
        config=ClientConfig(base_url="https://api.example"),
        transport=cast(FakeTransport, t),
        session=cast(SessionManager, _ExplodingSession()),
        clock=clk,
        limiter=SlidingWindowLimiter(500, 5.0, clk),
        retry=RetryPolicy(3),
        logon=lambda: "NEW",
        jitter=_one_jitter,
    )

    out = asyncio.run(ctx.ainvoke(_amount_spec()))

    assert out.amount == Decimal("1.30")
    assert t.sent[0].headers == {"User-Agent": f"stonepy/{__version__}"}


def test_sync_invoke_rejects_async_only_transport() -> None:
    t = AsyncFakeTransport([httpx.Response(200, content=b'{"Amount":1.30}')])
    clk = FakeClock()
    ctx = CallContext(
        config=ClientConfig(base_url="https://api.example"),
        transport=cast(FakeTransport, t),
        session=cast(SessionManager, _ExplodingSession()),
        clock=clk,
        limiter=SlidingWindowLimiter(500, 5.0, clk),
        retry=RetryPolicy(3),
        logon=lambda: "NEW",
        jitter=_one_jitter,
    )

    with pytest.raises(TypeError, match=r"send\(\)"):
        ctx.invoke(_amount_spec())


def test_ainvoke_uses_async_session_refresh_callback() -> None:
    async def run() -> None:
        from stonepy._core.session import AsyncSessionManager

        t = AsyncFakeTransport(
            [
                httpx.Response(
                    401,
                    json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 401},
                ),
                httpx.Response(200, json={"OrderId": 7}),
            ]
        )
        clk = FakeClock()
        session = AsyncSessionManager(clk, proactive_refresh_seconds=1080)
        await session.aset_token("OLD", "alice")
        calls: list[int] = []

        async def alogon() -> str:
            calls.append(1)
            await asyncio.sleep(0)
            return "NEW"

        ctx = CallContext(
            config=ClientConfig(base_url="https://api.example"),
            transport=cast(FakeTransport, t),
            session=cast(SessionManager, session),
            clock=clk,
            limiter=SlidingWindowLimiter(500, 5.0, clk),
            retry=RetryPolicy(3),
            logon=lambda: "SYNC-SHOULD-NOT-RUN",
            alogon=alogon,
            jitter=_one_jitter,
        )

        out = await ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert out.order_id == 7
        assert calls == [1]
        assert t.sent[1].headers["Session"] == "NEW"

    asyncio.run(run())


def test_request_model_body_omits_unset_optional_fields() -> None:
    t = FakeTransport([httpx.Response(200, json={"OrderId": 7})])
    out = _ctx(t, []).ctx.invoke(_body_spec(), body=_Body.model_validate({"Required": 3}))

    assert out.order_id == 7
    assert codec.loads(t.sent[0].content or b"{}") == {"Required": 3}


def test_parse_response_uses_codec_decimal_loading_and_model_validation() -> None:
    out = parse_response(_amount_spec(), httpx.Response(200, content=b'{"Amount":1.30}'))
    assert out.amount == Decimal("1.30")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, content=b"not-json"), "decode"),
        (httpx.Response(200, json={"OrderId": "not-an-int"}), "validate"),
    ],
)
def test_parse_response_wraps_success_body_parse_failures(
    response: httpx.Response,
    message: str,
) -> None:
    with pytest.raises(ResponseParseError) as excinfo:
        parse_response(_spec(), response)

    exc = excinfo.value
    assert type(exc).__name__ == "ResponseParseError"
    assert message in str(exc).lower()
    assert exc.http_status == 200
    assert exc.method == "GET"
    assert exc.path == "/order/{OrderId}"
    assert exc.raw_body == response.content


def test_auth_none_invoke_does_not_touch_session() -> None:
    t = FakeTransport([httpx.Response(200, content=b'{"Amount":1.30}')])
    clk = FakeClock()
    ctx = CallContext(
        config=ClientConfig(base_url="https://api.example"),
        transport=t,
        session=cast(SessionManager, _ExplodingSession()),
        clock=clk,
        limiter=SlidingWindowLimiter(500, 5.0, clk),
        retry=RetryPolicy(3),
        logon=lambda: "NEW",
        jitter=_one_jitter,
    )

    out = ctx.invoke(_amount_spec())

    assert out.amount == Decimal("1.30")
    assert t.sent[0].headers == {"User-Agent": f"stonepy/{__version__}"}


def test_nested_logon_auth_none_invoke_does_not_reenter_session() -> None:
    t = FakeTransport(
        [
            httpx.Response(200, content=b'{"Amount":1.30}'),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    clk = FakeClock()
    session = _NestedLogonSession()
    ctx: CallContext

    def do_logon() -> str:
        out = ctx.invoke(_amount_spec())
        assert out.amount == Decimal("1.30")
        return "NEW"

    ctx = CallContext(
        config=ClientConfig(base_url="https://api.example"),
        transport=t,
        session=cast(SessionManager, session),
        clock=clk,
        limiter=SlidingWindowLimiter(500, 5.0, clk),
        retry=RetryPolicy(3),
        logon=do_logon,
        jitter=_one_jitter,
    )

    out = ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert out.order_id == 7
    assert session.logon_calls == 1
    assert t.sent[0].headers == {"User-Agent": f"stonepy/{__version__}"}
    assert t.sent[1].headers["Session"] == "NEW"


def test_401_triggers_refresh_then_replays_with_new_token() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 401},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    out = _ctx(t, ["NEW"]).ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert t.sent[1].headers["Session"] == "NEW"


def test_plain_401_without_error_code_refreshes_then_replays_with_new_token() -> None:
    t = FakeTransport(
        [
            httpx.Response(401, content=b""),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    out = _ctx(t, ["NEW"]).ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert len(t.sent) == 2
    assert t.sent[1].headers["Session"] == "NEW"


def test_4011_error_code_on_non_401_refreshes_then_replays_with_new_token() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                400,
                json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 400},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    out = _ctx(t, ["NEW"]).ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert len(t.sent) == 2
    assert t.sent[1].headers["Session"] == "NEW"


def test_401_refresh_replay_only_happens_once() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 401},
            ),
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "exp2", "HttpStatus": 401},
            ),
        ]
    )
    with pytest.raises(AuthenticationError) as exc_info:
        _ctx(t, ["NEW"]).ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.error_code == 4011
    assert len(t.sent) == 2
    assert t.sent[1].headers["Session"] == "NEW"


def test_401_refresh_does_not_replay_when_refresh_exhausts_retry_budget() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 401},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    parts = _ctx(
        t,
        [],
        config=ClientConfig(base_url="https://api.example", retry_budget_seconds=0.5),
    )

    def slow_logon() -> str:
        parts.clock.advance(1.0)
        return "NEW"

    parts.ctx.logon = slow_logon

    with pytest.raises(AuthenticationError) as exc_info:
        parts.ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.error_code == 4011
    assert len(t.sent) == 1
    assert parts.clock.now() == 1.0


def test_async_401_refresh_does_not_replay_when_refresh_exhausts_retry_budget() -> None:
    async def run() -> None:
        t = AsyncFakeTransport(
            [
                httpx.Response(
                    401,
                    json={"ErrorCode": 4011, "ErrorMessage": "exp", "HttpStatus": 401},
                ),
                httpx.Response(200, json={"OrderId": 7}),
            ]
        )
        parts = await _actx(
            t,
            [],
            config=ClientConfig(base_url="https://api.example", retry_budget_seconds=0.5),
        )

        async def slow_alogon() -> str:
            parts.clock.advance(1.0)
            return "NEW"

        parts.ctx.alogon = slow_alogon

        with pytest.raises(AuthenticationError) as exc_info:
            await parts.ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert exc_info.value.error_code == 4011
        assert len(t.sent) == 1
        assert parts.clock.now() == 1.0

    asyncio.run(run())


def test_4010_bad_credentials_raises_without_loop() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                401,
                json={"ErrorCode": 4010, "ErrorMessage": "bad", "HttpStatus": 401},
            )
        ]
    )
    with pytest.raises(AuthenticationError) as exc_info:
        _ctx(t, ["NEW"]).ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.error_code == 4010
    assert len(t.sent) == 1


def test_proactive_refresh_runs_before_building_session_headers() -> None:
    t = FakeTransport([httpx.Response(200, json={"OrderId": 7})])
    parts = _ctx(t, ["NEW"])
    parts.clock.advance(1080)
    out = parts.ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert t.sent[0].headers["Session"] == "NEW"


def test_proactive_refresh_uses_generation_captured_before_stale_check() -> None:
    t = FakeTransport([httpx.Response(200, json={"OrderId": 7})])
    clk = FakeClock()
    racing_session = _RacingSession()
    logon_calls: list[str] = []

    def do_logon() -> str:
        logon_calls.append("called")
        return "NEW"

    ctx = CallContext(
        config=ClientConfig(base_url="https://api.example"),
        transport=t,
        session=cast(SessionManager, racing_session),
        clock=clk,
        limiter=SlidingWindowLimiter(500, 5.0, clk),
        retry=RetryPolicy(3),
        logon=do_logon,
        jitter=_one_jitter,
    )

    out = ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert out.order_id == 7
    assert racing_session.refresh_seen_generations == [1]
    assert logon_calls == []
    assert t.sent[0].headers["Session"] == "OTHER"


def test_4xx_maps_to_api_error() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                400,
                json={"ErrorCode": 4002, "ErrorMessage": "bad", "HttpStatus": 400},
            )
        ]
    )
    with pytest.raises(StoneXAPIError) as exc_info:
        _ctx(t, []).ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.error_code == 4002 and exc_info.value.http_status == 400


def test_map_error_uses_wire_status_when_body_http_status_is_stale() -> None:
    err = map_error(
        _spec(),
        httpx.Response(
            400,
            json={"ErrorCode": 4002, "ErrorMessage": "bad", "HttpStatus": 500},
        ),
    )
    assert err.http_status == 400


def test_pipeline_api_error_headers_do_not_expose_raw_session_token() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                400,
                headers={"X-Request-Id": "req-400", "X-Correlation-Id": "corr-400"},
                json={"ErrorCode": 4002, "ErrorMessage": "bad", "HttpStatus": 400},
            )
        ]
    )
    with pytest.raises(StoneXAPIError) as exc_info:
        _ctx(t, []).ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.headers.get("x-request-id") == "req-400"
    assert exc_info.value.headers.get("x-correlation-id") == "corr-400"
    assert "OLD" not in exc_info.value.headers.values()
    assert "Session" not in exc_info.value.headers


def test_pipeline_auth_error_headers_do_not_expose_raw_session_token() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                401,
                headers={"X-Request-Id": "req-401", "X-Correlation-Id": "corr-401"},
                json={"ErrorCode": 4010, "ErrorMessage": "bad", "HttpStatus": 401},
            )
        ]
    )
    with pytest.raises(AuthenticationError) as exc_info:
        _ctx(t, []).ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert exc_info.value.headers.get("x-request-id") == "req-401"
    assert exc_info.value.headers.get("x-correlation-id") == "corr-401"
    assert "OLD" not in exc_info.value.headers.values()
    assert "Session" not in exc_info.value.headers


def test_map_error_public_helper_uses_spec_context_and_response_headers() -> None:
    err = map_error(
        _spec(),
        httpx.Response(
            400,
            headers={
                "X-Request-Id": "req-public",
                "X-Correlation-Id": "corr-public",
                "Authorization": "Bearer SECRET",
            },
            json={"ErrorCode": 4002, "ErrorMessage": "bad", "HttpStatus": 400},
        ),
    )
    assert type(err) is StoneXAPIError
    assert err.error_code == 4002
    assert err.method == "GET"
    assert err.path == "/order/{OrderId}"
    assert err.headers.get("x-request-id") == "req-public"
    assert err.headers.get("x-correlation-id") == "corr-public"
    assert err.headers.get("authorization") == "***"
    assert "Bearer SECRET" not in err.headers.values()


def test_map_error_redacts_secret_response_headers_in_headers_and_repr() -> None:
    secret_headers = {
        "Set-Cookie": "sessionid=COOKIE-SECRET",
        "Cookie": "client=COOKIE-IN",
        "Proxy-Authorization": "Basic PROXY-SECRET",
        "X-Api-Key": "X-API-SECRET",
        "Api-Key": "API-SECRET",
        "App-Key": "APP-DASH-SECRET",
        "App_Key": "APP-UNDERSCORE-SECRET",
        "AppKey": "APPKEY-SECRET",
        "Password": "PASSWORD-SECRET",
        "Session": "SESSION-SECRET",
        "Authorization": "Bearer AUTH-SECRET",
        "X-Request-Id": "req-visible",
        "X-Correlation-Id": "corr-visible",
    }
    err = map_error(
        _spec(),
        httpx.Response(
            400,
            headers=secret_headers,
            json={"ErrorCode": 4002, "ErrorMessage": "bad", "HttpStatus": 400},
        ),
    )

    assert err.headers.get("x-request-id") == "req-visible"
    assert err.headers.get("x-correlation-id") == "corr-visible"
    assert err.headers.get("set-cookie") == "***"
    assert err.headers.get("cookie") == "***"
    assert err.headers.get("proxy-authorization") == "***"
    assert err.headers.get("x-api-key") == "***"
    assert err.headers.get("api-key") == "***"
    assert err.headers.get("app-key") == "***"
    assert err.headers.get("app_key") == "***"
    assert err.headers.get("appkey") == "***"
    assert err.headers.get("password") == "***"
    assert err.headers.get("session") == "***"
    assert err.headers.get("authorization") == "***"

    text = repr(err)
    for secret in secret_headers.values():
        if secret not in {"req-visible", "corr-visible"}:
            assert secret not in text


def test_map_error_4010_returns_authentication_error() -> None:
    err = map_error(
        _spec(),
        httpx.Response(401, json={"ErrorCode": 4010, "ErrorMessage": "bad", "HttpStatus": 401}),
    )
    assert isinstance(err, AuthenticationError)
    assert err.error_code == 4010


def test_map_error_5002_without_429_returns_api_error() -> None:
    err = map_error(
        _spec(),
        httpx.Response(
            400,
            headers={"Retry-After": "2"},
            json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 400},
        ),
    )
    assert type(err) is StoneXAPIError
    assert err.error_code == 5002


def test_map_error_rate_limit_parses_retry_after_http_date() -> None:
    future = datetime.now(UTC) + timedelta(seconds=120)
    err = map_error(
        _spec(),
        httpx.Response(
            429,
            headers={"Retry-After": format_datetime(future, usegmt=True)},
            json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
        ),
    )
    assert isinstance(err, RateLimitError)
    assert err.retry_after is not None
    assert 0.0 < err.retry_after <= 180.0


def test_map_error_rate_limit_parses_past_and_malformed_retry_after_dates() -> None:
    past = datetime.now(UTC) - timedelta(seconds=60)
    past_err = map_error(
        _spec(),
        httpx.Response(
            429,
            headers={"Retry-After": format_datetime(past, usegmt=True)},
            json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
        ),
    )
    assert isinstance(past_err, RateLimitError)
    assert past_err.retry_after == 0.0

    malformed_err = map_error(
        _spec(),
        httpx.Response(
            429,
            headers={"Retry-After": "not a date"},
            json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
        ),
    )
    assert isinstance(malformed_err, RateLimitError)
    assert malformed_err.retry_after is None


@pytest.mark.parametrize("retry_after", ["inf", "infinity", "nan"])
def test_map_error_rate_limit_ignores_non_finite_retry_after(retry_after: str) -> None:
    err = map_error(
        _spec(),
        httpx.Response(
            429,
            headers={"Retry-After": retry_after},
            json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
        ),
    )

    assert isinstance(err, RateLimitError)
    assert err.retry_after is None


def test_429_idempotent_call_backs_off_then_replays() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    parts = _ctx(t, [], retry=RetryPolicy(1))
    out = parts.ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert len(t.sent) == 2
    assert parts.clock.now() == 2.0


def test_async_429_idempotent_call_backs_off_then_replays() -> None:
    async def run() -> None:
        t = AsyncFakeTransport(
            [
                httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                    json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
                ),
                httpx.Response(200, json={"OrderId": 7}),
            ]
        )
        parts = await _actx(t, [], retry=RetryPolicy(1))

        out = await parts.ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert out.order_id == 7
        assert len(t.sent) == 2
        assert parts.clock.now() == 2.0

    asyncio.run(run())


def test_rate_limit_bucket_uses_independent_windows() -> None:
    t = FakeTransport(
        [
            httpx.Response(200, json={"OrderId": 1}),
            httpx.Response(200, json={"OrderId": 2}),
            httpx.Response(200, json={"OrderId": 3}),
        ]
    )
    cfg = ClientConfig(
        base_url="https://api.example",
        rate_limit_max=1,
        rate_limit_window_seconds=5.0,
    )
    parts = _ctx(t, [], config=cfg)

    parts.ctx.invoke(_bucket_spec("orders"), path_params={})
    parts.ctx.invoke(_bucket_spec("prices"), path_params={})

    assert parts.clock.now() == 0.0

    parts.ctx.invoke(_bucket_spec("orders"), path_params={})

    assert parts.clock.now() == 5.0


def test_5002_without_429_is_not_retried_as_rate_limit() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                400,
                headers={"Retry-After": "1"},
                json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 400},
            ),
        ]
    )
    parts = _ctx(t, [], retry=RetryPolicy(1))

    with pytest.raises(StoneXAPIError) as exc_info:
        parts.ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert type(exc_info.value) is StoneXAPIError
    assert exc_info.value.error_code == 5002
    assert len(t.sent) == 1
    assert parts.clock.now() == 0.0


def test_rate_limit_raises_when_retry_budget_is_exhausted() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
            )
        ]
    )
    cfg = ClientConfig(base_url="https://api.example", retry_budget_seconds=1.0)
    with pytest.raises(RateLimitError) as exc_info:
        _ctx(t, [], retry=RetryPolicy(1), config=cfg).ctx.invoke(
            _spec(),
            path_params={"OrderId": 7},
        )

    assert exc_info.value.retry_after == 2.0
    assert len(t.sent) == 1


def test_async_rate_limit_raises_when_retry_budget_is_exhausted() -> None:
    async def run() -> None:
        t = AsyncFakeTransport(
            [
                httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                    json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
                )
            ]
        )
        parts = await _actx(
            t,
            [],
            retry=RetryPolicy(1),
            config=ClientConfig(base_url="https://api.example", retry_budget_seconds=1.0),
        )

        with pytest.raises(RateLimitError) as exc_info:
            await parts.ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert exc_info.value.retry_after == 2.0
        assert len(t.sent) == 1

    asyncio.run(run())


def test_non_idempotent_post_is_not_retried_for_rate_limit() -> None:
    t = FakeTransport(
        [
            httpx.Response(
                429,
                headers={"Retry-After": "1"},
                json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
            )
        ]
    )
    with pytest.raises(RateLimitError):
        _ctx(t, [], retry=RetryPolicy(1)).ctx.invoke(
            _spec(method="POST", idempotent=False),
            path_params={"OrderId": 7},
        )

    assert len(t.sent) == 1


def test_idempotent_503_uses_retry_policy_backoff() -> None:
    t = FakeTransport(
        [
            httpx.Response(503, json={"ErrorCode": 5030, "ErrorMessage": "retry"}),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    parts = _ctx(t, [], retry=RetryPolicy(1))
    out = parts.ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert len(t.sent) == 2
    assert parts.clock.now() == 1.0


def test_async_idempotent_503_uses_retry_policy_backoff() -> None:
    async def run() -> None:
        t = AsyncFakeTransport(
            [
                httpx.Response(503, json={"ErrorCode": 5030, "ErrorMessage": "retry"}),
                httpx.Response(200, json={"OrderId": 7}),
            ]
        )
        parts = await _actx(t, [], retry=RetryPolicy(1))

        out = await parts.ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert out.order_id == 7
        assert len(t.sent) == 2
        assert parts.clock.now() == 1.0

    asyncio.run(run())


def test_idempotent_503_uses_injected_jitter_for_backoff() -> None:
    t = FakeTransport(
        [
            httpx.Response(503, json={"ErrorCode": 5030, "ErrorMessage": "retry"}),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    parts = _ctx(t, [], retry=RetryPolicy(1), jitter=lambda: 0.5)

    out = parts.ctx.invoke(_spec(), path_params={"OrderId": 7})

    assert out.order_id == 7
    assert len(t.sent) == 2
    assert parts.clock.now() == 0.75


def test_transport_errors_retry_only_when_policy_allows() -> None:
    t = FakeTransport(
        [
            httpx.ConnectError("temporary"),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )
    parts = _ctx(t, [], retry=RetryPolicy(1))
    out = parts.ctx.invoke(_spec(), path_params={"OrderId": 7})
    assert out.order_id == 7
    assert len(t.sent) == 2
    assert parts.clock.now() == 1.0


def test_async_transport_errors_retry_only_when_policy_allows() -> None:
    async def run() -> None:
        t = AsyncFakeTransport(
            [
                httpx.ConnectError("temporary"),
                httpx.Response(200, json={"OrderId": 7}),
            ]
        )
        parts = await _actx(t, [], retry=RetryPolicy(1))

        out = await parts.ctx.ainvoke(_spec(), path_params={"OrderId": 7})

        assert out.order_id == 7
        assert len(t.sent) == 2
        assert parts.clock.now() == 1.0

    asyncio.run(run())


def test_transport_error_includes_endpoint_context_when_not_retried() -> None:
    t = FakeTransport([httpx.ConnectError("network down")])

    with pytest.raises(TransportError) as exc_info:
        _ctx(t, [], retry=RetryPolicy(0)).ctx.invoke(_spec(), path_params={"OrderId": 7})

    err = exc_info.value
    assert err.method == "GET"
    assert err.path == "/order/{OrderId}"
    assert err.attempt == 0
    assert "network down" in str(err)


def test_business_status_checker_raises_when_decoder_marks_rejected() -> None:
    model = _StatusResp.model_validate({"Status": 6, "StatusReason": 42})

    with pytest.raises(OrderRejectedError) as exc_info:
        check_business_status(
            model,
            lambda status, status_reason: BusinessStatus(
                is_rejection=status == 6,
                reason=f"reason {status_reason}",
            ),
        )

    assert exc_info.value.status == 6
    assert exc_info.value.status_reason == 42
    assert exc_info.value.reason == "reason 42"
    assert exc_info.value.method is None
    assert exc_info.value.path is None
    assert exc_info.value.http_status is None


def test_business_status_checker_accepts_mapping_payload() -> None:
    with pytest.raises(OrderRejectedError) as exc_info:
        check_business_status(
            {"Status": 6, "StatusReason": 42},
            lambda status, status_reason: BusinessStatus(
                is_rejection=status == 6,
                reason=f"reason {status_reason}",
            ),
        )

    assert exc_info.value.status == 6
    assert exc_info.value.status_reason == 42
    assert exc_info.value.reason == "reason 42"


def test_invoke_checks_business_status_with_configured_decoder() -> None:
    t = FakeTransport([httpx.Response(200, json={"Status": 6, "StatusReason": 42})])
    parts = _ctx(
        t,
        [],
        status_decoder=lambda status, status_reason: BusinessStatus(
            is_rejection=status == 6,
            reason=f"reason {status_reason}",
        ),
    )

    with pytest.raises(OrderRejectedError) as exc_info:
        parts.ctx.invoke(_status_spec())

    assert exc_info.value.status == 6
    assert exc_info.value.status_reason == 42
    assert exc_info.value.reason == "reason 42"
    assert exc_info.value.method == "POST"
    assert exc_info.value.path == "/status"
    assert exc_info.value.http_status == 200


def test_invoke_rejects_business_status_by_default() -> None:
    t = FakeTransport([httpx.Response(200, json={"Status": 5, "StatusReason": 42})])

    with pytest.raises(OrderRejectedError) as exc_info:
        _ctx(t, []).ctx.invoke(_status_spec())

    assert exc_info.value.status == 5
    assert exc_info.value.status_reason == 42
    assert exc_info.value.reason == "OrdersinOCOPairmustbeeitherStoporLimit"


def test_default_business_status_decoder_ignores_non_order_specs() -> None:
    t = FakeTransport([httpx.Response(200, json={"Status": 5, "StatusReason": 42})])

    out = _ctx(t, []).ctx.invoke(_status_spec(bucket="market"))

    assert out.status == 5
    assert out.status_reason == 42


def test_default_business_status_decoder_falls_back_for_unknown_reasons() -> None:
    decision = default_status_decoder(5, 9999)

    assert isinstance(decision, BusinessStatus)
    assert decision.is_rejection is True
    assert decision.reason == "9999"


def test_default_business_status_allows_accepted_ok_status() -> None:
    t = FakeTransport([httpx.Response(200, json={"Status": 2, "StatusReason": 1})])

    out = _ctx(t, []).ctx.invoke(_status_spec())

    assert out.status == 2
    assert out.status_reason == 1


def test_default_business_status_allows_nonrejection_lifecycle_status() -> None:
    # Open (3) is a normal filled/working outcome, not a rejection: the response is returned.
    t = FakeTransport([httpx.Response(200, json={"Status": 3, "StatusReason": 1})])

    out = _ctx(t, []).ctx.invoke(_status_spec())

    assert out.status == 3
    assert out.status_reason == 1


def test_default_business_status_rejects_redcard_status() -> None:
    t = FakeTransport([httpx.Response(200, json={"Status": 10, "StatusReason": 1})])

    with pytest.raises(OrderRejectedError) as exc_info:
        _ctx(t, []).ctx.invoke(_status_spec())

    assert exc_info.value.status == 10
    assert exc_info.value.status_reason == 1
    assert exc_info.value.reason == "RedCard"


def test_default_business_status_rejection_missing_reason_uses_status_name() -> None:
    decision = default_status_decoder(10, None)

    assert isinstance(decision, BusinessStatus)
    assert decision.is_rejection is True
    assert decision.reason == "RedCard"


def test_business_status_checker_is_noop_without_status_or_rejection() -> None:
    check_business_status(
        _Resp.model_validate({"OrderId": 7}),
        lambda status, status_reason: BusinessStatus(False),
    )
    check_business_status(
        _StatusResp.model_validate({"Status": 1, "StatusReason": None}),
        lambda status, status_reason: BusinessStatus(is_rejection=status == 6),
    )
