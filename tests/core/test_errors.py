from stonepy._core.errors import (
    AuthenticationError,
    OrderRejectedError,
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
