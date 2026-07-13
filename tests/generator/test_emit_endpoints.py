from __future__ import annotations

from pathlib import Path

import pytest

from stonepy._core.status import StatusDomain
from stonepy._generator.__main__ import main
from stonepy._generator.catalog import Catalog, EndpointRecord, TypeRecord
from stonepy._generator.emit_endpoints import (
    emit_all,
    is_host_rooted,
    render_binding,
    resolved_path,
    resolved_status_domain,
    target_module,
)

FIX = Path(__file__).parent / "fixtures"


def _endpoint(
    *,
    name: str = "GetOrder",
    logical_name: str | None = "GetOrder",
    method: str | None = "GET",
    target: str | None = "order",
    path: str = "/order/{OrderId}",
    parameters: list[dict[str, object]] | None = None,
    request_type: str | None = None,
    response_type: str | None = "OrderResponseDTO",
) -> EndpointRecord:
    return EndpointRecord(
        name=name,
        logical_name=logical_name,
        version="v1",
        description=None,
        method=method,
        target=target,
        uri_template=path,
        path=path,
        content_type="application/json",
        envelope="JSON",
        parameters=parameters or [],
        request_type=request_type,
        response_type=response_type,
        source_url=None,
        source_file=None,
        last_updated=None,
        raw={"name": name},
    )


def _datatype(name: str) -> TypeRecord:
    return TypeRecord(
        name=name,
        catalog_name=name,
        version="v1",
        description=None,
        properties=[],
        source_url=None,
        source_file=None,
        last_updated=None,
        raw={"name": name, "properties": []},
    )


def test_resolved_path_applies_active_stop_limit_order_override() -> None:
    # The active-stop-limit query is a v1-style "/order/{orderId}/activeStopLimitOrder" route
    # (verified live); the catalog's "/v2{orderId}/..." template 404s, so an override supplies the
    # real path that the emitted spec and the generated contract test must agree on.
    typo = _endpoint(
        name="GetActiveStopLimitOrder v2",
        logical_name="GetActiveStopLimitOrder",
        target="order",
        path="/order/v2{orderId}/activeStopLimitOrder?clientAccountId={clientAccountId}",
    )
    assert (
        resolved_path(typo)
        == "/order/{orderId}/activeStopLimitOrder?clientAccountId={clientAccountId}"
    )
    # An endpoint without a declared override keeps its catalog path verbatim.
    assert resolved_path(_endpoint(path="/order/{OrderId}")) == "/order/{OrderId}"


def test_resolved_path_dedoubles_v2_endpoints() -> None:
    # The catalog composes a v2 path as "/{target}{uri_template}", doubling the resource segment
    # the uri_template already carries; resolved_path returns the uri_template (the real route).
    doubled = EndpointRecord(
        name="GetMarketSpread v2",
        logical_name="GetMarketSpread",
        version="v2",
        description=None,
        method="GET",
        target="market",
        uri_template="/v2/market/spread?clientAccountId={clientAccountId}",
        path="/market/v2/market/spread?clientAccountId={clientAccountId}",
        content_type="application/json",
        envelope="JSON",
        parameters=[],
        request_type=None,
        response_type="GetMarketInformationResponseDTO",
        source_url=None,
        source_file=None,
        last_updated=None,
        raw={"name": "GetMarketSpread v2"},
    )
    assert resolved_path(doubled) == "/v2/market/spread?clientAccountId={clientAccountId}"


def test_resolved_path_applies_v2_route_overrides() -> None:
    # Endpoints whose documented uri_template is itself wrong get a verified path override.
    save_order = _endpoint(name="SaveOrder v2", target="order", path="/v2/save")
    assert resolved_path(save_order) == "/v2/order"
    open_position = _endpoint(
        name="GetOpenPosition v2",
        target="order",
        path="/v2/{orderId}/openPosition?clientAccountId={clientAccountId}",
    )
    assert (
        resolved_path(open_position)
        == "/v2/order/{orderId}/openPosition?clientAccountId={clientAccountId}"
    )
    user_pref = _endpoint(name="GetUserPreference v2", target="preference", path="/v2/Preferences")
    assert resolved_path(user_pref) == "/v2/Preference"


def test_status_domains_are_explicit_for_acknowledgements_and_status_reads() -> None:
    trade = _endpoint(
        name="Trade",
        logical_name="Trade",
        method="POST",
        response_type="ApiTradeOrderResponseDTO",
    )
    read = _endpoint(
        name="GetActiveStopLimitOrder",
        logical_name="GetActiveStopLimitOrder",
        response_type="GetActiveStopLimitOrderResponseDTOv2",
    )

    assert resolved_status_domain(trade) is StatusDomain.INSTRUCTION
    assert resolved_status_domain(read) is StatusDomain.NONE
    rendered = render_binding(trade)
    assert "from stonepy._core.status import StatusDomain" in rendered
    assert "status_domain=StatusDomain.INSTRUCTION" in rendered


def test_new_status_bearing_endpoint_requires_reviewed_domain() -> None:
    rec = _endpoint(
        name="FutureTrade",
        logical_name="FutureTrade",
        method="POST",
        response_type="ApiTradeOrderResponseDTO",
    )

    with pytest.raises(ValueError, match="needs an explicit status domain"):
        render_binding(rec)


def test_render_binding_emits_wrapper_docstring_from_description() -> None:
    import dataclasses

    rec = dataclasses.replace(_endpoint(), description="Fetch a single order by id.")

    rendered = render_binding(rec, known_model_names={"OrderResponseDTO"})

    # The summary appears as a docstring in both the sync and async wrappers.
    assert rendered.count('"""Fetch a single order by id."""') == 2


def test_endpoint_summary_falls_back_when_description_missing() -> None:
    from stonepy._generator.emit_endpoints import endpoint_summary

    assert endpoint_summary(_endpoint(name="GetOrder")) == "Call the StoneX GetOrder endpoint."


def test_target_module_normalizes_real_target_casing() -> None:
    assert target_module("userAccount") == "user_account"
    assert target_module("useraccount") == "user_account"
    assert target_module("priceAlert") == "price_alert"
    assert target_module("pricealert") == "price_alert"
    assert target_module("tradeHistory") == "trade_history"


def test_target_module_maps_watchlists_to_watchlist() -> None:
    assert target_module("watchlists") == "watchlist"
    assert target_module("watchlist") == "watchlist"


def test_render_binding_marks_http_idempotent_methods_retry_safe() -> None:
    get_rendered = render_binding(_endpoint(method="GET"))
    put_rendered = render_binding(_endpoint(method="PUT"))
    delete_rendered = render_binding(_endpoint(method="DELETE"))
    post_rendered = render_binding(_endpoint(method="POST"))
    missing_method_rendered = render_binding(_endpoint(method=None))

    assert "idempotent=True" in get_rendered
    assert "idempotent=True" in put_rendered
    assert "idempotent=True" in delete_rendered
    assert "idempotent=False" in post_rendered
    assert 'method="GET"' in missing_method_rendered
    assert "idempotent=True" in missing_method_rendered


def test_read_only_post_query_endpoints_are_retry_safe_by_override() -> None:
    rendered = render_binding(
        _endpoint(
            name="ListActiveOrders",
            logical_name="ListActiveOrders",
            method="POST",
            target="order",
            path="/order/activeorders",
            parameters=[
                {
                    "name": "requestDTO",
                    "type": "ListActiveOrdersRequestDTO",
                    "ref": "ListActiveOrdersRequestDTO",
                    "in": "query",
                }
            ],
            request_type=None,
            response_type="ListActiveOrdersResponseDTO",
        ),
        known_model_names={"ListActiveOrdersRequestDTO", "ListActiveOrdersResponseDTO"},
    )

    assert "idempotent=True" in rendered


def test_render_log_on_v2_uses_logical_symbol_auth_none_and_body_call() -> None:
    rec = _endpoint(
        name="LogOn v2",
        logical_name="LogOn",
        method="POST",
        target="session",
        path="/session/v2/Session",
        parameters=[
            {
                "name": "logOn",
                "type": "ApiLogOnRequestDTO",
                "ref": "ApiLogOnRequestDTO",
                "in": "body",
            }
        ],
        request_type="ApiLogOnRequestDTO",
        response_type="ApiLogOnResponseDTOv2",
    )

    rendered = render_binding(rec)

    assert "LOG_ON_SPEC: EndpointSpec[ApiLogOnResponseDTOv2] = EndpointSpec(" in rendered
    assert "LOG_ON_V2_SPEC" not in rendered
    assert "auth_policy=AuthPolicy.NONE" in rendered
    assert (
        "def log_on(ctx: CallContext, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:"
        in rendered
    )
    assert (
        "async def alog_on(ctx: CallContext, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:"
        in rendered
    )
    assert "return ctx.invoke(LOG_ON_SPEC, body=request)" in rendered
    assert "return await ctx.ainvoke(LOG_ON_SPEC, body=request)" in rendered
    assert "return cast(" not in rendered


def test_render_get_path_endpoint_includes_param_and_path_params_call() -> None:
    rec = _endpoint(
        name="GetActiveStopLimitOrder",
        logical_name="GetActiveStopLimitOrder",
        method="GET",
        path="/order/{OrderId}/activestoplimitorder",
        parameters=[
            {
                "name": "OrderId",
                "type": "Integer",
                "ref": None,
                "in": "path",
            }
        ],
        request_type=None,
        response_type="GetActiveStopLimitOrderResponseDTOv2",
    )

    rendered = render_binding(rec)

    assert 'Param(name="OrderId", location="path", python_name="order_id")' in rendered
    assert "def get_active_stop_limit_order(" in rendered
    assert 'path_params={"OrderId": order_id}' in rendered
    assert "idempotent=True" in rendered


def test_uri_template_placeholders_synthesize_params_when_catalog_omits_them() -> None:
    # GetMarketSpread v2 ships an empty parameter list even though its URI templates two query
    # parameters; the binding must still expose them or the request cannot be built.
    rec = _endpoint(
        name="GetMarketSpread v2",
        logical_name="GetMarketSpread",
        method="GET",
        target="market",
        path="/market/v2/market/spread?clientAccountId={clientAccountId}&marketId={marketId}",
        parameters=[],
        request_type=None,
        response_type="GetMarketSpreadResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"GetMarketSpreadResponseDTO"})

    assert 'Param(name="clientAccountId", location="query", python_name="client_account_id")' in (
        rendered
    )
    assert 'Param(name="marketId", location="query", python_name="market_id")' in rendered
    assert "client_account_id" in rendered and "market_id" in rendered


def test_declared_unresolved_response_uses_passthrough_model() -> None:
    rec = _endpoint(
        name="GetNewsHeadlines",
        logical_name="GetNewsHeadlines",
        method="GET",
        target="news",
        path="/news/newsheadlines",
        parameters=[],
        request_type=None,
        response_type="NewsHeadlinesResponseDTO",
    )

    rendered = render_binding(rec, known_model_names=set())

    assert "from typing import TypeAlias" in rendered
    assert "from typing import TypeAlias, cast" not in rendered
    assert "from stonepy._core.models import PassthroughResponseModel" in rendered
    assert "NewsHeadlinesResponseDTO: TypeAlias = PassthroughResponseModel" in rendered
    assert "response_model=NewsHeadlinesResponseDTO" in rendered
    assert "response_model=PassthroughResponseModel" not in rendered
    assert "def get_news_headlines(ctx: CallContext) -> NewsHeadlinesResponseDTO:" in rendered


def test_optional_query_params_are_keyword_defaults_and_omit_none() -> None:
    rec = _endpoint(
        name="ListSpreadMarkets",
        logical_name="ListSpreadMarkets",
        method="GET",
        target="spread",
        path="/spread/markets",
        parameters=[
            {"name": "marketName", "type": "string", "ref": None, "in": "query"},
            {
                "name": "maxResults",
                "type": "integer minValue 1 maxValue 500 required False default 20",
                "ref": None,
                "in": "query",
            },
            {
                "name": "useMobileShortName",
                "type": "boolean default False",
                "ref": None,
                "in": "query",
            },
            {
                "name": "Preferences",
                "type": "string[] required false",
                "ref": None,
                "in": "query",
            },
        ],
        request_type=None,
        response_type="ListSpreadMarketsResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"ListSpreadMarketsResponseDTO"})

    assert "market_name: str" in rendered
    assert "*,\n    max_results: int | None = 20" in rendered
    assert "use_mobile_short_name: bool | None = False" in rendered
    assert "preferences: list[str] | None = None" in rendered
    assert '"maxResults": max_results' in rendered
    assert '"useMobileShortName": use_mobile_short_name' in rendered
    assert '"Preferences": preferences' in rendered


def test_nullable_query_params_are_optional_keyword_defaults() -> None:
    rec = _endpoint(
        name="ListTradeHistory",
        logical_name="ListTradeHistory",
        method="GET",
        target="order",
        path="/order/tradehistory",
        parameters=[
            {
                "name": "TradingAccountId",
                "type": "integer nullable true",
                "ref": None,
                "in": "query",
            },
            {"name": "maxResults", "type": "integer nullable true", "ref": None, "in": "query"},
        ],
        request_type=None,
        response_type="ListTradeHistoryResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"ListTradeHistoryResponseDTO"})

    assert "trading_account_id: int | None = None" in rendered
    assert "max_results: int | None = None" in rendered
    assert '"TradingAccountId": trading_account_id' in rendered
    assert '"maxResults": max_results' in rendered


def test_nullable_body_param_is_optional_while_required_body_param_stays_positional() -> None:
    rec = _endpoint(
        name="GetPA",
        logical_name="GetPA",
        method="GET",
        target="pricealert",
        path="/pricealert/",
        parameters=[
            {"name": "alertId", "type": "integer nullable true", "ref": None, "in": "body"},
            {"name": "ClientAccountId", "type": "integer required True", "ref": None, "in": "body"},
        ],
        request_type=None,
        response_type="PriceAlertResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"PriceAlertResponseDTO"})

    assert "client_account_id: int" in rendered
    assert "alert_id: int | None = None" in rendered
    assert '"alertId": alert_id' in rendered
    assert '"ClientAccountId": client_account_id' in rendered


def test_documented_optional_filters_are_forced_optional_via_override() -> None:
    # ListSpreadMarkets/ListCfdMarkets doc "leave the market name and code parameters empty to
    # return all markets", but the catalog leaves those bare-typed (no required/nullable marker).
    # A curated override forces exactly those filters optional so the "return all" call is
    # reachable; genuinely-required bare params (ClientAccountId) stay required.
    rec = _endpoint(
        name="ListSpreadMarkets",
        logical_name="ListSpreadMarkets",
        method="GET",
        target="spread",
        path="/spread/markets",
        parameters=[
            {
                "name": "searchByMarketName",
                "type": "string minLength 1 maxLength 120",
                "ref": None,
                "in": "query",
            },
            {
                "name": "searchByMarketCode",
                "type": "string minLength 1 maxLength 50",
                "ref": None,
                "in": "query",
            },
            {"name": "ClientAccountId", "type": "integer minValue 1", "ref": None, "in": "query"},
        ],
        request_type=None,
        response_type="ListSpreadMarketsResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"ListSpreadMarketsResponseDTO"})

    assert "search_by_market_name: str | None = None" in rendered
    assert "search_by_market_code: str | None = None" in rendered
    # A bare param NOT in the override stays required positional.
    assert "client_account_id: int" in rendered
    assert "client_account_id: int | None" not in rendered


def test_query_template_placeholder_overrides_catalog_path_location() -> None:
    rec = _endpoint(
        name="ListOpenPositions",
        logical_name="ListOpenPositions",
        method="GET",
        target="order",
        path="/order/openpositions?TradingAccountId={TradingAccountId}",
        parameters=[
            {
                "name": "TradingAccountId",
                "type": "integer nullable true",
                "ref": None,
                "in": "path",
            }
        ],
        request_type=None,
        response_type="ListOpenPositionsResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"ListOpenPositionsResponseDTO"})

    assert (
        'Param(name="TradingAccountId", location="query", python_name="trading_account_id")'
        in rendered
    )
    assert 'path_params={"TradingAccountId": trading_account_id}' not in rendered
    assert 'query={"TradingAccountId": trading_account_id}' in rendered


def test_path_template_placeholder_overrides_catalog_query_location() -> None:
    rec = _endpoint(
        name="GetMarketInformation",
        logical_name="GetMarketInformation",
        method="GET",
        target="market",
        path="/market/{marketId}/information?clientAccountId={clientAccountId}",
        parameters=[
            {"name": "MarketId", "type": "integer", "ref": None, "in": "query"},
            {"name": "ClientAccountId", "type": "integer", "ref": None, "in": "query"},
        ],
        request_type=None,
        response_type="GetMarketInformationResponseDTO",
    )

    rendered = render_binding(rec, known_model_names={"GetMarketInformationResponseDTO"})

    assert 'Param(name="MarketId", location="path", python_name="market_id")' in rendered
    assert (
        'Param(name="ClientAccountId", location="query", python_name="client_account_id")'
        in rendered
    )
    assert 'path_params={"MarketId": market_id}' in rendered
    assert 'query={"ClientAccountId": client_account_id}' in rendered


def test_emit_all_imports_known_model_query_parameter_annotations(tmp_path: Path) -> None:
    # Synthetic endpoint name (not a real overridden endpoint like ListActiveOrders, which the
    # generator forces to a body param): this exercises the generic known-model query-param path.
    catalog = Catalog(
        endpoints=[
            _endpoint(
                name="ListGizmos",
                logical_name="ListGizmos",
                method="POST",
                target="gizmo",
                path="/gizmo/list",
                parameters=[
                    {
                        "name": "requestDTO",
                        "type": "ListGizmosRequestDTO",
                        "ref": "ListGizmosRequestDTO",
                        "in": "query",
                    }
                ],
                request_type=None,
                response_type="ListGizmosResponseDTO",
            )
        ],
        datatypes=[
            _datatype("ListGizmosRequestDTO"),
            _datatype("ListGizmosResponseDTO"),
        ],
        lookups={},
        unresolved=set(),
    )

    emit_all(catalog, tmp_path)

    rendered = (tmp_path / "_endpoints" / "gizmo.py").read_text(encoding="utf-8")
    assert "from typing import cast" not in rendered
    assert "from stonepy.models import ListGizmosRequestDTO, ListGizmosResponseDTO" in rendered
    assert "request_dto: ListGizmosRequestDTO" in rendered
    assert "request_model=ListGizmosRequestDTO" in rendered
    assert "return cast(" not in rendered
    assert "LIST_GIZMOS_SPEC: EndpointSpec[ListGizmosResponseDTO] = EndpointSpec(" in rendered
    assert (
        "return ctx.invoke(\n"
        "        LIST_GIZMOS_SPEC,\n"
        "        query=request_dto.model_dump("
        'by_alias=True, exclude_unset=True, mode="python"),\n'
        "    )" in rendered
    )


def test_primitive_body_params_are_typed_and_catalog_keyed() -> None:
    rec = _endpoint(
        name="DeleteSession",
        logical_name="DeleteSession",
        method="POST",
        target="session",
        path="/session/deleteSession",
        parameters=[
            {"name": "UserName", "type": "string", "ref": None, "in": "body"},
            {"name": "Session", "type": "string", "ref": None, "in": "body"},
        ],
        request_type=None,
        response_type="ApiLogOffResponseDTO",
    )

    rendered = render_binding(rec)

    assert "body: Mapping[str, object]" not in rendered
    assert "def delete_session(ctx: CallContext, user_name: str, session: str)" in rendered
    assert 'body={"UserName": user_name, "Session": session}' in rendered


def test_emit_all_writes_grouped_endpoint_modules_and_deterministic_init(tmp_path: Path) -> None:
    catalog = Catalog(
        endpoints=[
            _endpoint(
                name="LogOn v2",
                logical_name="LogOn",
                method="POST",
                target="session",
                path="/session/v2/Session",
                parameters=[
                    {
                        "name": "logOn",
                        "type": "ApiLogOnRequestDTO",
                        "ref": "ApiLogOnRequestDTO",
                        "in": "body",
                    }
                ],
                request_type="ApiLogOnRequestDTO",
                response_type="ApiLogOnResponseDTOv2",
            ),
            _endpoint(
                name="GetOrder",
                logical_name="GetOrder",
                method="GET",
                target="order",
                path="/order/{OrderId}",
                parameters=[
                    {
                        "name": "OrderId",
                        "type": "Integer",
                        "ref": None,
                        "in": "path",
                    }
                ],
                request_type=None,
                response_type="OrderResponseDTO",
            ),
        ],
        datatypes=[
            _datatype("ApiLogOnRequestDTO"),
            _datatype("ApiLogOnResponseDTOv2"),
            _datatype("OrderResponseDTO"),
        ],
        lookups={},
        unresolved=set(),
    )

    emit_all(catalog, tmp_path)
    first_init = (tmp_path / "_endpoints" / "__init__.py").read_text(encoding="utf-8")
    emit_all(catalog, tmp_path)

    assert (tmp_path / "_endpoints" / "order.py").exists()
    assert (tmp_path / "_endpoints" / "session.py").exists()
    assert (tmp_path / "_endpoints" / "__init__.py").read_text(encoding="utf-8") == first_init
    # The package re-exports the target *submodules*, never the binding functions/specs:
    # re-exporting a function such as ``order`` would shadow the ``order`` submodule and
    # break ``from stonepy._endpoints import order as _ep``.
    assert "from . import order, session" in first_init
    assert '"order"' in first_init and '"session"' in first_init
    assert "aget_order" not in first_init
    assert "GET_ORDER_SPEC" not in first_init


def test_cli_parses_supported_commands_with_fixture_catalog(tmp_path: Path) -> None:
    command_args = {
        "models": ["models"],
        "endpoints": ["endpoints"],
        "all": ["all"],
        "client": ["client"],
        "scaffold": ["scaffold", "order", "CancelOrder"],
    }
    for command, args in command_args.items():
        out_dir = tmp_path / command
        assert (
            main(
                [
                    *args,
                    "--catalog-root",
                    str(FIX),
                    "--out-dir",
                    str(out_dir),
                    "--allow-unresolved",
                    "--allow-unfrozen-catalog",
                ]
            )
            == 0
        )


def test_cli_rejects_unexpected_unresolved_catalog(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unexpected unresolved"):
        main(
            [
                "models",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
                "--allow-unfrozen-catalog",
            ]
        )


def test_cli_rejects_unfrozen_catalog(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="catalog"):
        main(
            [
                "models",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
                "--allow-unresolved",
            ]
        )


def test_cli_rejects_scaffold_only_args_for_non_scaffold_command(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "models",
                "order",
                "CancelOrder",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
            ]
        )

    with pytest.raises(SystemExit):
        main(["models", "--force", "--catalog-root", str(FIX), "--out-dir", str(tmp_path)])


def test_log_on_path_override_is_host_rooted() -> None:
    rec = _endpoint(
        name="LogOn v2",
        logical_name="LogOn",
        method="POST",
        target="session",
        path="/session/v2/Session",
        response_type="ApiLogOnResponseDTOv2",
    )

    assert resolved_path(rec) == "/v2/session"
    assert is_host_rooted(rec) is True

    rendered = render_binding(rec, known_model_names={"ApiLogOnResponseDTOv2"})
    assert 'path="/v2/session"' in rendered
    assert "host_rooted=True" in rendered


def test_default_endpoint_is_not_host_rooted() -> None:
    rec = _endpoint()

    assert is_host_rooted(rec) is False
    assert "host_rooted" not in render_binding(rec, known_model_names={"OrderResponseDTO"})


def test_client_and_trading_account_path_override_is_host_rooted() -> None:
    rec = _endpoint(
        name="GetClientAndTradingAccount v2",
        logical_name="GetClientAndTradingAccount",
        method="GET",
        target="userAccount",
        path="/userAccount/v2/userAccount/ClientAndTradingAccount",
        response_type="AccountInformationResponseDTOv2",
    )

    assert resolved_path(rec) == "/v2/UserAccount/ClientAndTradingAccount"
    assert is_host_rooted(rec) is True
    assert "host_rooted=True" in render_binding(
        rec, known_model_names={"AccountInformationResponseDTOv2"}
    )


def test_client_account_margin_uses_v1_path_and_stays_base_rooted() -> None:
    rec = _endpoint(
        name="GetClientAccountMargin v2",
        logical_name="GetClientAccountMargin",
        method="GET",
        target="margin",
        path="/margin/v2/margin/clientAccountMargin?clientAccountId={clientAccountId}",
        response_type="ClientAccountMarginResponseDTO",
    )

    assert resolved_path(rec) == "/margin/ClientAccountMargin"
    assert is_host_rooted(rec) is False
    assert "host_rooted" not in render_binding(
        rec, known_model_names={"ClientAccountMarginResponseDTO"}
    )
