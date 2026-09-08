from __future__ import annotations

import ast
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, Mock, call

import pytest

from stonepy import (
    AuthenticationError,
    ResponseParseError,
    StoneXAPIError,
    StoneXClient,
    TransportError,
)
from stonepy._endpoints.price_alert import GET_PA_SPEC
from stonepy.models import AccountResult, PriceAlertResponseDTO, SaveAlertResponseDTOv2
from tests.live import _safety as live_safety
from tests.live import conftest as live_fixtures
from tests.live import test_live_audit_probes as probes
from tests.live._contract_mismatch import ExpectedLiveContractMismatch, as_contract_mismatch
from tests.live._safety import (
    REQUIRED_VARIABLES,
    approved_live_account,
    expected_client_account_id,
    live_client,
    live_tests_enabled,
    missing_live_requirements,
    validate_live_target,
)


def _environment() -> dict[str, str]:
    return {
        "STONEX_LIVE": "1",
        "STONEX_USERNAME": "demo",
        "STONEX_PASSWORD": "password",
        "STONEX_APP_KEY": "key",
        "STONEX_LIVE_CLIENT_ACCOUNT_ID": "123",
    }


@pytest.mark.parametrize("opt_in", [None, "", "0", "true", " 1"])
def test_live_requires_explicit_opt_in(opt_in: str | None) -> None:
    environ = _environment()
    if opt_in is None:
        del environ["STONEX_LIVE"]
    else:
        environ["STONEX_LIVE"] = opt_in
    assert not live_tests_enabled(environ)
    assert missing_live_requirements(environ) == ["STONEX_LIVE=1"]
    assert live_tests_enabled(_environment())


def test_live_requires_client_account_id() -> None:
    environ = _environment()
    del environ["STONEX_LIVE_CLIENT_ACCOUNT_ID"]
    assert not live_tests_enabled(environ)
    assert missing_live_requirements(environ) == ["STONEX_LIVE_CLIENT_ACCOUNT_ID"]
    assert expected_client_account_id(_environment()) == 123


@pytest.mark.parametrize("name", REQUIRED_VARIABLES)
@pytest.mark.parametrize("value", ["", "   "])
def test_live_requires_nonempty_settings(name: str, value: str) -> None:
    environ = _environment()
    environ[name] = value
    assert not live_tests_enabled(environ)
    assert missing_live_requirements(environ) == [name]


@pytest.mark.parametrize("value", ["", "abc", "0", "-1", "1.2"])
def test_live_requires_valid_account_id(value: str) -> None:
    with pytest.raises(ValueError, match="STONEX_LIVE_CLIENT_ACCOUNT_ID"):
        expected_client_account_id({"STONEX_LIVE_CLIENT_ACCOUNT_ID": value})


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.example/TradingAPI",
        "http://ciapi.cityindex.com/TradingAPI",
        "https://ciapi.cityindex.com.evil.example/TradingAPI",
        "https://ciapi.cityindex.com./TradingAPI",
        "https://ciapi.cityindex.com:8443/TradingAPI",
        "https://ciapipreprod.cityindextest9.co.uk:8444/TradingAPI",
        "https://ciapi.cityindex.com:invalid/TradingAPI",
        "https://ciapi.cityindex.com:65536/TradingAPI",
        "https://ciapi.cityindex.com@api.example/TradingAPI",
        "https://user:password@ciapi.cityindex.com/TradingAPI",
        "https://@ciapi.cityindex.com/TradingAPI",
        "https://[invalid/TradingAPI",
        "https://ciapi.cityindex.com\n/TradingAPI",
        "",
    ],
)
def test_live_rejects_non_demo_target(base_url: str) -> None:
    with pytest.raises(ValueError, match="live target hostname") as exc_info:
        validate_live_target(base_url)
    assert "TradingAPI" not in str(exc_info.value)
    assert "password" not in str(exc_info.value)


@pytest.mark.parametrize(
    "host",
    [
        "ciapi.cityindex.com",
        "CIAPI.CITYINDEX.COM:443",
        "ciapipreprod.cityindextest9.co.uk",
        "ciapipreprod.cityindextest9.co.uk:443",
        "CIAPIPREPROD.CITYINDEXTEST9.CO.UK:8443",
    ],
)
def test_live_accepts_only_exact_demo_host(host: str) -> None:
    validate_live_target(f"https://{host}/TradingAPI")


@pytest.mark.parametrize("observed", [123, 456, None])
def test_live_account_guard_checks_observed_id(observed: int | None) -> None:
    account = AccountResult.model_validate({"ClientAccounts": [{"ClientAccountId": observed}]})
    client = Mock(spec=StoneXClient)
    client.user_account.get_client_and_trading_account.return_value = account
    if observed == 123:
        assert approved_live_account(client, _environment()) is account
    else:
        with pytest.raises(
            AssertionError,
            match=f"live account {observed} is not the approved STONEX_LIVE_CLIENT_ACCOUNT_ID 123",
        ):
            approved_live_account(client, _environment())
    client.user_account.get_client_and_trading_account.assert_called_once_with()


def test_live_target_is_checked_before_client_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock(side_effect=AssertionError("client must not be constructed"))
    monkeypatch.setattr(live_safety, "StoneXClient", constructor)
    with (
        pytest.raises(ValueError, match="live target hostname"),
        live_client({**_environment(), "STONEX_BASE_URL": "https://api.example"}),
    ):
        pytest.fail("unapproved live target was accepted")
    constructor.assert_not_called()


def test_live_client_uses_supplied_environment_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    environ = {**_environment(), "STONEX_BASE_URL": "https://ciapi.cityindex.com/TradingAPI"}
    managed_client = MagicMock(spec=StoneXClient)
    constructor = Mock(return_value=managed_client)
    monkeypatch.setattr(live_safety, "StoneXClient", constructor)
    with live_client(environ) as client:
        assert client is managed_client.__enter__.return_value
    config = constructor.call_args.args[0]
    assert config.base_url == environ["STONEX_BASE_URL"]
    assert config.username == environ["STONEX_USERNAME"]
    assert config.password == environ["STONEX_PASSWORD"]
    assert config.app_key == environ["STONEX_APP_KEY"]
    managed_client.__exit__.assert_called_once_with(None, None, None)


def test_live_suite_collects_independently() -> None:
    executable = Path(sys.executable).with_name("pytest.exe" if os.name == "nt" else "pytest")
    assert executable.is_file(), "pytest console entry point is missing"
    environ = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    environ["STONEX_LIVE"] = "0"
    # Use the console script: python -m pytest would put cwd on sys.path and hide this regression.
    result = subprocess.run(
        [
            str(executable),
            "tests/live",
            "-m",
            "live",
            "-p",
            "no:cov",
            "-p",
            "no:cacheprovider",
            "--collect-only",
            "-q",
            "-o",
            "addopts=",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environ,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "test_get_pa_selected_binding_honors_filters" in result.stdout


def test_live_collection_skip_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*REQUIRED_VARIABLES, "STONEX_LIVE"):
        monkeypatch.delenv(name, raising=False)
    live_item = Mock(keywords={"live": True})
    unit_item = Mock(keywords={})
    live_fixtures.pytest_collection_modifyitems(Mock(spec=pytest.Config), [live_item, unit_item])
    reason = live_item.add_marker.call_args.args[0].kwargs["reason"]
    assert reason == "live tests disabled: set STONEX_LIVE=1, " + ", ".join(REQUIRED_VARIABLES)
    unit_item.add_marker.assert_not_called()


@pytest.mark.parametrize("name", REQUIRED_VARIABLES)
@pytest.mark.parametrize("value", [None, "", "   "])
def test_live_collection_rejects_missing_settings_after_opt_in(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str | None
) -> None:
    for key, setting in _environment().items():
        monkeypatch.setenv(key, setting)
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    live_item = Mock(keywords={"live": True})
    with pytest.raises(pytest.UsageError, match=f"^live tests enabled but unconfigured: {name}$"):
        live_fixtures.pytest_collection_modifyitems(Mock(spec=pytest.Config), [live_item])
    live_item.add_marker.assert_not_called()


def test_live_collection_accepts_complete_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _environment().items():
        monkeypatch.setenv(name, value)
    live_item = Mock(keywords={"live": True})
    live_fixtures.pytest_collection_modifyitems(Mock(spec=pytest.Config), [live_item])
    live_item.add_marker.assert_not_called()


def test_strict_live_xfails_have_raises_restrictions() -> None:
    for path in (Path(__file__).parent / "live").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or ast.unparse(node.func) != "pytest.mark.xfail":
                continue
            keywords = {keyword.arg: keyword.value for keyword in node.keywords}
            strict = keywords.get("strict")
            if isinstance(strict, ast.Constant) and strict.value is True:
                assert "raises" in keywords, (
                    f"{path.name}:{node.lineno}: strict xfail needs raises="
                )


@pytest.mark.parametrize("status", [400, 401, 403, 404, 405, 415, 429, 500])
@pytest.mark.parametrize("error_type", [StoneXAPIError, AuthenticationError])
def test_live_contract_mismatch_restricts_http_failures(
    status: int, error_type: type[StoneXAPIError]
) -> None:
    exc = error_type(
        http_status=status,
        error_code=None,
        error_message=None,
        method="POST",
        path="/probe",
        raw_body=b"",
        headers={},
    )
    mismatch = as_contract_mismatch(exc)
    expected = error_type is StoneXAPIError and status in {400, 404, 405, 415}
    assert isinstance(mismatch, ExpectedLiveContractMismatch) is expected


def test_live_contract_mismatch_restricts_non_http_failures() -> None:
    exc = ResponseParseError(
        phase="validate",
        http_status=200,
        method="GET",
        path="/probe",
        raw_body=b"",
        message="shape",
    )
    assert isinstance(as_contract_mismatch(exc), ExpectedLiveContractMismatch)
    assert (
        as_contract_mismatch(TransportError("down", method="GET", path="/probe", attempt=0)) is None
    )
    assert as_contract_mismatch(AssertionError("bug")) is None


def _probe_client() -> Mock:
    client = Mock(spec=StoneXClient)
    client._ctx = Mock()
    market = client.market.get_market_information.return_value.market_information
    market.prices.offer_price = Decimal("2")
    client.price_alert.save_price_alert.side_effect = [
        SaveAlertResponseDTOv2(AlertId=101),
        SaveAlertResponseDTOv2(AlertId=102),
    ]
    client.price_alert.delete_pa.return_value = True
    return client


@pytest.mark.parametrize("query_fails", [False, True])
@pytest.mark.parametrize("body_honors_filter", [False, True])
def test_get_pa_probe_records_both_bindings_and_checks_production(
    capsys: pytest.CaptureFixture[str], query_fails: bool, body_honors_filter: bool
) -> None:
    client = _probe_client()
    filtered = PriceAlertResponseDTO.model_validate({"PriceAlerts": [{"AlertId": 101}]})
    unfiltered = PriceAlertResponseDTO.model_validate(
        {"PriceAlerts": [{"AlertId": 101}, {"AlertId": 102}]}
    )
    client._ctx.invoke.side_effect = [
        RuntimeError("query failed") if query_fails else filtered,
        filtered if body_honors_filter else unfiltered,
    ]
    production_location = GET_PA_SPEC.params[0].location
    production_honors = body_honors_filter if production_location == "body" else not query_fails
    if production_honors:
        probes.test_get_pa_selected_binding_honors_filters(client, {"cid": 123, "mid": 456})
    else:
        with pytest.raises(AssertionError, match=f"production GetPA {production_location} binding"):
            probes.test_get_pa_selected_binding_honors_filters(client, {"cid": 123, "mid": 456})
    output = capsys.readouterr().out
    assert "location='query'" in output and "location='body'" in output
    assert output.count("account_filter='unverified'") == 2
    for recorded, location in zip(
        client._ctx.invoke.call_args_list, ("query", "body"), strict=True
    ):
        assert recorded.kwargs == {location: {"alertId": 101, "ClientAccountId": 123}}
        assert [param.location for param in recorded.args[0].params] == [location, location]
    requests = [recorded.args[0] for recorded in client.price_alert.save_price_alert.call_args_list]
    assert requests[0].comment != requests[1].comment
    assert all(request.notification_method == 1 for request in requests)
    assert client.price_alert.delete_pa.call_args_list == [
        call(alert_id=101, client_account_id=123),
        call(alert_id=102, client_account_id=123),
    ]


def test_get_pa_probe_cleans_up_if_second_creation_fails() -> None:
    client = _probe_client()
    client.price_alert.save_price_alert.side_effect = [
        SaveAlertResponseDTOv2(AlertId=101),
        RuntimeError("save failed"),
    ]
    with pytest.raises(RuntimeError, match="save failed"):
        probes.test_get_pa_selected_binding_honors_filters(client, {"cid": 123, "mid": 456})
    client.price_alert.delete_pa.assert_called_once_with(alert_id=101, client_account_id=123)


@pytest.mark.parametrize("failure", [RuntimeError("delete failed"), False])
def test_get_pa_probe_attempts_every_cleanup(failure: Exception | bool) -> None:
    client = _probe_client()
    client.price_alert.delete_pa.side_effect = [failure, True]
    with pytest.raises(ExceptionGroup, match="failed to delete probe alerts"):
        probes._delete_probe_alerts(client, 123, [101, 102])
    assert client.price_alert.delete_pa.call_count == 2
