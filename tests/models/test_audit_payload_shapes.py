from __future__ import annotations

from typing import Any, cast, get_args, get_origin

import pytest
from pydantic import TypeAdapter

from stonepy.models import (
    AlertNotification,
    ApiGetCommunityActionsResponseDTO,
    ApiGetMultipleUsersDetailsResponseDTO,
    ApiGetWallItemsForUsersResponseDTO,
    ApiGetWallSubItemsResponseDTO,
    ApiIfDoneDTOv2,
    ApiListFollowedUsersResponseDTO,
    ApiListFollowingUsersResponseDTO,
    ApiListTopholdersDTO,
    ApiListTopholdersForMarketsResponseDTO,
    ApiManagedTradeDTO,
    ApiOpenPositionDTOv2,
    ApiSaveClientPreferenceRequestDTO,
    ApiUserDynamicProfileDTO,
    GetPriceTickResponseDTO,
    ListOpenPositionsResponseDTO,
    NewTradeOrderRequestDTO,
    SaveClientPreferenceRequestDTO,
)


def _allows_list(annotation: object) -> bool:
    if get_origin(annotation) is list:
        return True
    return any(get_origin(item) is list for item in get_args(annotation))


@pytest.mark.parametrize(
    ("model_cls", "field_name"),
    [
        (GetPriceTickResponseDTO, "price_ticks"),
        (ListOpenPositionsResponseDTO, "open_positions"),
        (ApiOpenPositionDTOv2, "managed_trades"),
        (NewTradeOrderRequestDTO, "if_done"),
    ],
)
def test_audited_array_fields_are_typed_as_lists(
    model_cls: type[Any],
    field_name: str,
) -> None:
    field = model_cls.model_fields[field_name]

    assert _allows_list(field.annotation)
    if model_cls is NewTradeOrderRequestDTO:
        assert not field.is_required()


def test_price_tick_response_accepts_array_payload() -> None:
    parsed = GetPriceTickResponseDTO.model_validate({"PriceTicks": [{"Price": "1.23"}]})

    assert parsed.price_ticks is not None
    assert len(parsed.price_ticks) == 1
    assert parsed.price_ticks[0].price is not None


def test_nested_array_payloads_parse_as_lists() -> None:
    position = ApiOpenPositionDTOv2.model_validate({"ManagedTrades": [{"OrderId": 123}]})
    request_if_done = cast(
        list[ApiIfDoneDTOv2],
        TypeAdapter(NewTradeOrderRequestDTO.model_fields["if_done"].annotation).validate_python(
            [{"Stop": {"OrderId": 456}, "Limit": {"OrderId": 789}}],
        ),
    )

    assert isinstance(position.managed_trades, list)
    assert isinstance(position.managed_trades[0], ApiManagedTradeDTO)
    assert isinstance(request_if_done, list)
    assert isinstance(request_if_done[0], ApiIfDoneDTOv2)


def test_alert_notification_zero_decodes_as_none_member() -> None:
    assert AlertNotification(0) is AlertNotification.None_


def test_user_dynamic_profile_numeric_fields_decode_as_ints() -> None:
    profile = ApiUserDynamicProfileDTO.model_validate(
        {
            "NumberFollowed": 2,
            "NumberFollowing": 3,
            "LastTradedMarketId": 123,
        }
    )

    assert profile.number_followed == 2
    assert profile.number_following == 3
    assert profile.last_traded_market_id == 123


@pytest.mark.parametrize(
    ("model_cls", "payload", "field_name"),
    [
        (
            ApiGetCommunityActionsResponseDTO,
            {"CommunityActions": [{"CommunityActionId": 1}]},
            "community_actions",
        ),
        (
            ApiGetWallItemsForUsersResponseDTO,
            {"WallItemsForUsers": [{"ScreenName": "x"}]},
            "wall_items_for_users",
        ),
        (
            ApiGetWallSubItemsResponseDTO,
            {"WallItems": [{"WallItemId": 1}]},
            "wall_items",
        ),
        (
            ApiListFollowedUsersResponseDTO,
            {"FollowingUsers": [{"ScreenName": "x"}]},
            "following_users",
        ),
        (
            ApiListFollowingUsersResponseDTO,
            {"FollowedUsers": [{"ScreenName": "x"}]},
            "followed_users",
        ),
        (
            ApiListTopholdersDTO,
            {"Users": [{"ScreenName": "x"}]},
            "users",
        ),
        (
            ApiListTopholdersForMarketsResponseDTO,
            {"TopHolders": [{"MarketID": 1}]},
            "top_holders",
        ),
        (
            ApiGetMultipleUsersDetailsResponseDTO,
            {"CiConnectUsersDetails": [{"ClientAccountId": 1}]},
            "ci_connect_users_details",
        ),
    ],
)
def test_md_m5_payload_fields_decode_as_lists(
    model_cls: type[Any], payload: dict[str, object], field_name: str
) -> None:
    decoded = model_cls.model_validate(payload)
    value = getattr(decoded, field_name)

    assert isinstance(value, list)
    assert len(value) == 1


def test_client_preference_requests_keep_scalar_dto_shape() -> None:
    api_request = ApiSaveClientPreferenceRequestDTO.model_validate(
        {
            "ClientAccountId": 1,
            "ClientPreference": {"Key": "theme", "Value": "dark"},
        }
    )
    request = SaveClientPreferenceRequestDTO.model_validate(
        {"ClientPreference": {"Key": "theme", "Value": "dark"}}
    )

    assert api_request.client_preference is not None
    assert api_request.client_preference.key == "theme"
    assert request.client_preference is not None
    assert request.client_preference.value == "dark"


def test_new_trade_order_accepts_documented_optional_fields_as_omitted() -> None:
    request = NewTradeOrderRequestDTO.model_validate(
        {
            "MarketId": 1,
            "Currency": "USD",
            "AutoRollover": False,
            "Direction": "Buy",
            "Quantity": "1",
            "QuoteId": 2,
            "PositionMethodId": 1,
            "BidPrice": "1.0",
            "OfferPrice": "1.1",
            "AuditId": "audit",
            "TradingAccountId": 3,
            "Close": [],
            "Reference": "StoneX API",
            "AllocationProfileId": 0,
            "PriceTolerance": 0,
        }
    )

    assert request.order_reference is None
    assert request.source is None
    assert "OrderReference" not in request.model_dump(by_alias=True, exclude_unset=True)
    assert "Source" not in request.model_dump(by_alias=True, exclude_unset=True)
