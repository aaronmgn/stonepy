import pytest

from stonepy._core.errors import (
    AuthenticationError,
    OrderRejectedError,
    OrderStatusUnknownError,
    RateLimitError,
    StoneXAPIError,
    StoneXError,
)


def test_api_error_carries_context_and_is_stonex_error() -> None:
    err = StoneXAPIError(
        http_status=400,
        error_code=4002,
        error_message="bad",
        method="POST",
        path="/order/newtradeorder",
        raw_body=b"{}",
        headers={},
    )
    assert isinstance(err, StoneXError)
    assert err.http_status == 400 and err.error_code == 4002
    assert "4002" in str(err) and "/order/newtradeorder" in str(err)


def test_api_error_repr_redacts_session_header() -> None:
    err = StoneXAPIError(
        http_status=401,
        error_code=4011,
        error_message="x",
        method="GET",
        path="/p",
        raw_body=None,
        headers={"Session": "SECRET-TOKEN"},
    )
    assert "SECRET-TOKEN" not in repr(err)


def test_auth_error_is_api_error() -> None:
    assert issubclass(AuthenticationError, StoneXAPIError)


def test_public_exception_classes_have_docstrings() -> None:
    assert StoneXAPIError.__doc__
    assert RateLimitError.__doc__
    assert OrderRejectedError.__doc__
    assert OrderStatusUnknownError.__doc__


def test_order_rejected_carries_status() -> None:
    err = OrderRejectedError(status=6, status_reason=42, reason="Suspended", response=object())
    assert err.status == 6 and err.status_reason == 42


def test_order_rejected_repr_omits_attached_response() -> None:
    err = OrderRejectedError(
        status=6,
        status_reason=42,
        reason="Suspended",
        response={"Session": "SECRET"},
        method="POST",
        path="/order/newstoplimitorder",
        http_status=200,
    )

    text = repr(err)

    assert "SECRET" not in text
    assert "POST" in text
    assert "/order/newstoplimitorder" in text


def test_unknown_order_status_is_not_a_rejection_and_warns_against_resubmission() -> None:
    err = OrderStatusUnknownError(
        status=999,
        status_reason=75,
        response={"Session": "SECRET"},
        method="POST",
        path="/order/newtradeorder",
        http_status=200,
    )

    assert isinstance(err, StoneXError)
    assert not isinstance(err, OrderRejectedError)
    assert err.status == 999
    assert err.status_reason == 75
    assert err.method == "POST"
    assert err.path == "/order/newtradeorder"
    assert err.http_status == 200
    assert "MAY OR MAY NOT have been placed" in str(err)
    assert "verify order state before resubmitting" in str(err)
    assert "SECRET" not in repr(err)


def test_response_parse_error_message_has_locations_not_values() -> None:
    import httpx
    import pytest

    from stonepy._core.endpoint import AuthPolicy, EndpointSpec
    from stonepy._core.errors import ResponseParseError
    from stonepy._core.pipeline import parse_response
    from stonepy.models import ApiLogOnResponseDTOv2

    spec = EndpointSpec(
        name="LogOn",
        method="POST",
        path="/v2/session",
        auth_policy=AuthPolicy.NONE,
        rate_limit_bucket="session",
        idempotent=False,
        response_model=ApiLogOnResponseDTOv2,
    )
    secret = "validation-secret"
    with pytest.raises(ResponseParseError) as caught:
        parse_response(spec, httpx.Response(200, json={"Session": {"nested": secret}}))
    text = str(caught.value)
    assert "Session: string_type" in text
    assert secret not in text
    assert "Input should" not in text


def _public_exception_samples() -> list[StoneXError]:
    from stonepy import (
        AuthenticationError,
        ConfigurationError,
        OrderRejectedError,
        OrderStatusUnknownError,
        RateLimitError,
        ResponseParseError,
        TransportError,
    )

    return [
        StoneXError("base"),
        ConfigurationError("configuration"),
        *[
            cls(
                http_status=429,
                error_code=7,
                error_message="message",
                method="POST",
                path="/test",
                raw_body=b"diagnostic",
                headers={"Session": "token"},
            )
            for cls in (StoneXAPIError, AuthenticationError, RateLimitError)
        ],
        OrderRejectedError(status=5, status_reason=2, reason="rejected", response={"a": 1}),
        OrderStatusUnknownError(status=None, status_reason=None, response={"a": 1}),
        ResponseParseError(
            phase="validate",
            http_status=200,
            method="POST",
            path="/test",
            raw_body=b"diagnostic",
            message="safe",
        ),
        TransportError("network", method="GET", path="/test", attempt=2),
    ]


@pytest.mark.parametrize("exc", _public_exception_samples(), ids=lambda exc: type(exc).__name__)
def test_public_exceptions_pickle_round_trip(exc: StoneXError) -> None:
    import pickle

    import stonepy

    public = {
        getattr(stonepy, name)
        for name in stonepy.__all__
        if isinstance(getattr(stonepy, name), type)
        and issubclass(getattr(stonepy, name), StoneXError)
    }
    assert {type(sample) for sample in _public_exception_samples()} == public
    restored = pickle.loads(pickle.dumps(exc))
    assert type(restored) is type(exc)
    assert restored.args == exc.args
    assert str(restored) == str(exc)
    assert repr(restored) == repr(exc)
    assert vars(restored) == vars(exc)
