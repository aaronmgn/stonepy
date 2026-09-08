from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from stonepy._generator import render
from stonepy._generator.catalog import Catalog, load_catalog
from stonepy._generator.emit_models import emit_all
from stonepy._generator.request_graph import (
    RequestVariantNameCollisionError,
    UnsupportedRequestParameterTypeError,
    build_request_type_graph,
    rewrite_request_annotation,
)

FIX = Path(__file__).parent / "fixtures" / "request_graph"
ROOTS = frozenset(
    [
        "ApiAccountInformationSaveRequestDTO",
        "ApiChangePasswordRequestDTO",
        "ApiClientApplicationMessageTranslationRequestDTO",
        "ApiClientCommunicationUpdateRequestDTOv2",
        "ApiClientPreferencesOverriddenSettingsSaveRequestDTO",
        "ApiClientPreferencesOverridenSettingsSaveRequestDTO",
        "ApiLogOnRequestDTO",
        "ApiSaveClientPreferenceRequestDTO",
        "ApiSavePreferencesRequestDTO",
        "ApiValidateSessionRequestDTOv2",
        "CancelOrderRequestDTO",
        "ClientPreferenceRequestDTO",
        "ClientPreferencesRequestDTO",
        "DeleteAllocationProfileRequestDTO",
        "ExecutionVenueRequestDTO",
        "ListActiveOrdersRequestDTO",
        "ListNewsHeadlinesRequestDTO",
        "ListProductInformationDTO",
        "MultipleMarketInformationRequestDTO",
        "NewFixedMarginTradeOrderRequestDTO",
        "NewStopLimitOrderRequestDTO",
        "NewTradeOrderRequestDTO",
        "SaveAlertRequestDTOv2",
        "SaveAllocationProfileRequestDTO",
        "SaveClientPreferenceRequestDTO",
        "SaveMarketInformationRequestDTO",
        "SaveWatchlistRequestDTO",
        "UpdateFixedMarginTradeOrderRequestDTO",
        "UpdateStopLimitOrderRequestDTO",
        "UpdateTradeOrderRequestDTO",
    ]
)
VARIANT_SOURCES = frozenset(
    [
        "ApiClientAccountWatchlistDTO",
        "ApiClientAccountWatchlistItemDTO",
        "ApiClientPreferencesOverriddenSettingSaveDTO",
        "ApiClientPreferencesOverriddenSettingsSaveDTO",
        "ApiClientPreferencesOverridenSettingSaveDTO",
        "ApiClientPreferencesOverridenSettingsSaveDTO",
        "ApiDateTimeOffsetDTO",
        "ApiFxFinancingDTO",
        "ApiIfDoneDTOv2",
        "ApiKnockoutDTO",
        "ApiMarketEodDTO",
        "ApiMarketInformationDTOv2",
        "ApiMarketInformationSaveDTO",
        "ApiMarketSpreadDTO",
        "ApiStepMarginBandDTO",
        "ApiStepMarginDTO",
        "ApiStopLimitOrderDTOv2",
        "ApiTradingDayTimesDTO",
        "ClientPreferenceKeyDTO",
        "CorporateActionsDTO",
        "IdentifierDTO",
        "MarketPricesDTO",
        "OrderRequestDTO",
        "PreferenceDTO",
        "Timestamp",
    ]
)


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog(FIX)


def test_request_graph_includes_transitive_dtos(catalog: Catalog) -> None:
    graph = build_request_type_graph(catalog)
    assert graph.roots == {"RootRequestDTO", "PeerRequestDTO"}
    assert graph.reachable == {
        "ChildDTO",
        "LeafDTO",
        "MarketDTO",
    }
    assert dict(graph.variants) == {name: f"Request{name}" for name in graph.reachable}
    assert graph.request_name("Mode") == "Mode"


def test_request_graph_applies_field_type_overrides(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = next(rec for rec in catalog.datatypes if rec.name == "ChildDTO")
    child.properties.append({"name": "Spreads", "type": "string"})
    assert "ApiMarketSpreadDTO" not in build_request_type_graph(catalog).reachable
    monkeypatch.setattr(
        render, "_FIELD_TYPE_OVERRIDES", {("ChildDTO", "Spreads"): "list[ApiMarketSpreadDTO]"}
    )
    assert "ApiMarketSpreadDTO" in build_request_type_graph(catalog).reachable


def test_request_graph_uses_type_only_dependencies(catalog: Catalog) -> None:
    assert "LeafDTO" in build_request_type_graph(catalog).reachable


def test_request_graph_terminates_on_cycles(catalog: Catalog) -> None:
    leaf = next(rec for rec in catalog.datatypes if rec.name == "LeafDTO")
    leaf.properties.append({"name": "Self", "type": "LeafDTO"})
    assert len(build_request_type_graph(catalog).reachable) == 3


def test_request_graph_keeps_root_as_dependency_unchanged(catalog: Catalog) -> None:
    graph = build_request_type_graph(catalog)
    assert graph.request_name("PeerRequestDTO") == "PeerRequestDTO"
    assert "PeerRequestDTO" not in graph.variants


def test_request_variant_name_collision_fails(catalog: Catalog) -> None:
    catalog.datatypes.append(replace(catalog.datatypes[1], name="RequestChildDTO"))
    with pytest.raises(RequestVariantNameCollisionError, match="ChildDTO.*RequestChildDTO"):
        build_request_type_graph(catalog)


@pytest.mark.parametrize(
    "annotation", ["ChildDTO []", "list[ChildDTO]", "dict[str, ChildDTO]", "ChildDTO | None"]
)
def test_compound_non_root_parameter_fails_generation(catalog: Catalog, annotation: str) -> None:
    catalog.endpoints[0].parameters.append({"name": "children", "in": "query", "type": annotation})
    with pytest.raises(UnsupportedRequestParameterTypeError, match="fixture.Save.*children"):
        build_request_type_graph(catalog)


def test_production_catalog_graph_matches_inventory() -> None:
    root = os.environ.get("STONEPY_CATALOG")
    if not root:
        pytest.skip("STONEPY_CATALOG is unset")
    graph = build_request_type_graph(load_catalog(Path(root)))
    assert graph.roots == ROOTS
    assert graph.reachable == VARIANT_SOURCES


def test_request_annotation_rewrites_only_identifiers() -> None:
    assert (
        rewrite_request_annotation(
            "dict[str, list[ChildDTO]] | ChildDTOExtra | None", {"ChildDTO": "RequestChildDTO"}
        )
        == "dict[str, list[RequestChildDTO]] | ChildDTOExtra | None"
    )


def test_request_variant_generation_is_byte_stable(catalog: Catalog, tmp_path: Path) -> None:
    emit_all(catalog, tmp_path)
    first = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*.py")}
    emit_all(catalog, tmp_path)
    assert first == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*.py")}
    child = first[Path("models/RequestChildDTO.py")].decode()
    assert "repr=False" in child
    assert "Request-side variant of ChildDTO: rejects unknown fields." in child
    assert "PeerRequestDTO | None" in child


def test_endpoint_request_annotations_preserve_response_identity(catalog: Catalog) -> None:
    from stonepy._generator.emit_endpoints import _binding
    from stonepy._generator.request_graph import RequestTypeGraph

    # Exercise the binding boundary with a shared DTO in both request and response positions.
    # Production's plain endpoint DTO parameters are all roots today.
    rec = replace(
        catalog.endpoints[0],
        request_type="ChildDTO",
        response_type="ChildDTO",
        parameters=[{"name": "child", "in": "body", "type": "ChildDTO"}],
    )
    graph = RequestTypeGraph(frozenset(), frozenset({"ChildDTO"}), {"ChildDTO": "RequestChildDTO"})
    binding = _binding(rec, known_model_names={"ChildDTO"}, request_graph=graph)
    assert binding.request_model == "RequestChildDTO"
    assert binding.request_annotation == "RequestChildDTO"
    assert binding.params[0].annotation == "RequestChildDTO"
    assert binding.response_annotation == "ChildDTO"
    assert binding.response_model == "ChildDTO"
    assert binding.model_imports == {"ChildDTO", "RequestChildDTO"}
