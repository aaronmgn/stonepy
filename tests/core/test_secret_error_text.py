"""Regression coverage for secrets in ordinary exception and traceback text."""

import asyncio
import traceback
from collections.abc import Sequence

import httpx
import pytest
import respx
from pydantic import ValidationError

from stonepy import (
    AsyncStoneXClient,
    ClientConfig,
    ResponseParseError,
    StoneXAPIError,
    StoneXClient,
)
from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.models import ListResponse, ResponseModel, ScalarResponse
from stonepy._core.pipeline import parse_response
from stonepy.models import ApiLogOnRequestDTO, ApiStopLimitOrderDTOv2


def _assert_secret_free_exception(exc: BaseException, secrets: Sequence[str]) -> None:
    pending = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for rendered in (str(current), repr(current), "".join(traceback.format_exception(current))):
            for secret in secrets:
                assert secret not in rendered
        pending.extend(e for e in (current.__cause__, current.__context__) if e is not None)


def _request(secret: str) -> ApiLogOnRequestDTO:
    return ApiLogOnRequestDTO.model_validate(
        {
            "UserName": "alice",
            "Password": secret,
            "AppKey": secret,
            "AppVersion": "stonepy",
            "AppComments": "",
        }
    )


def test_logon_request_missing_field_hides_secrets() -> None:
    secret = "missing-request-secret"
    payload = {"UserName": "alice", "Password": secret, "AppKey": secret}
    with pytest.raises(ValidationError) as caught:
        ApiLogOnRequestDTO.model_validate(payload)
    _assert_secret_free_exception(caught.value, [secret])


@respx.mock
def test_sync_logon_response_validation_hides_secrets() -> None:
    secret = "sync-response-secret"
    respx.post("https://api.example/v2/session").respond(200, json={"Session": {"nested": secret}})
    with (
        StoneXClient(ClientConfig(base_url="https://api.example")) as client,
        pytest.raises(ResponseParseError) as caught,
    ):
        client.session.log_on(_request(secret))
    _assert_secret_free_exception(caught.value, [secret])
    assert caught.value.raw_body is not None and secret.encode() in caught.value.raw_body
    assert caught.value.__context__ is None and caught.value.__cause__ is None


@respx.mock
def test_async_logon_response_validation_hides_secrets() -> None:
    secret = "async-response-secret"
    respx.post("https://api.example/v2/session").respond(200, json={"Session": {"nested": secret}})

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            with pytest.raises(ResponseParseError) as caught:
                await client.session.log_on(_request(secret))
        _assert_secret_free_exception(caught.value, [secret])
        assert caught.value.__context__ is None and caught.value.__cause__ is None

    asyncio.run(run())


@respx.mock
def test_sync_non_json_error_body_hides_secrets() -> None:
    secret = "sync-html-secret"
    body = f"<html>{secret}</html>".encode()
    respx.post("https://api.example/v2/session").respond(500, content=body)
    with (
        StoneXClient(ClientConfig(base_url="https://api.example", max_retries=0)) as client,
        pytest.raises(StoneXAPIError) as caught,
    ):
        client.session.log_on(_request(secret))
    _assert_secret_free_exception(caught.value, [secret])
    assert caught.value.raw_body == body


@respx.mock
def test_async_non_json_error_body_hides_secrets() -> None:
    secret = "async-html-secret"
    body = f"<html>{secret}</html>".encode()
    respx.post("https://api.example/v2/session").respond(500, content=body)

    async def run() -> None:
        async with AsyncStoneXClient(
            ClientConfig(base_url="https://api.example", max_retries=0)
        ) as client:
            with pytest.raises(StoneXAPIError) as caught:
                await client.session.log_on(_request(secret))
        _assert_secret_free_exception(caught.value, [secret])
        assert caught.value.raw_body == body

    asyncio.run(run())


def test_root_response_validation_hides_secrets() -> None:
    secret = "root-response-secret"
    for model in (ListResponse[ResponseModel], ScalarResponse[int]):
        with pytest.raises(ValidationError) as caught:
            model.model_validate(secret)
        _assert_secret_free_exception(caught.value, [secret])


def test_decode_error_has_no_sensitive_exception_chain() -> None:
    secret = "decode-response-secret"
    body = f"not-json-{secret}".encode()
    spec = EndpointSpec(
        name="Decode",
        method="GET",
        path="/decode",
        response_model=ResponseModel,
        auth_policy=AuthPolicy.NONE,
        idempotent=True,
        rate_limit_bucket="default",
    )
    with pytest.raises(ResponseParseError) as caught:
        parse_response(spec, httpx.Response(200, content=body))
    _assert_secret_free_exception(caught.value, [secret])
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.raw_body == body
    assert "invalid JSON response (JSONDecodeError)" in str(caught.value)


def test_date_validator_message_hides_input() -> None:
    secret = "expiry-date-secret"
    payload = {"ExpiryDateTimeUTC": secret}
    with pytest.raises(ValidationError) as caught:
        ApiStopLimitOrderDTOv2.model_validate(payload)
    _assert_secret_free_exception(caught.value, [secret])


def test_base_url_rejects_userinfo() -> None:
    secret = "userinfo-password-secret"
    url = f"https://u:{secret}@host/x"
    with pytest.raises(ValueError, match="base_url must not embed credentials") as caught:
        ClientConfig(base_url=url)
    _assert_secret_free_exception(caught.value, [secret])
