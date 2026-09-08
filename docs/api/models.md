# Models (DTOs)

Request and response DTO bodies are [Pydantic](https://docs.pydantic.dev/) models exported from
`stonepy.models`. Some methods take primitive parameters, and some return bare scalars or lists.
DTO naming follows the upstream API:

- endpoint request DTOs often end in `RequestDTO` or `RequestDTOv2`,
- response DTOs often end in `ResponseDTO` or `ResponseDTOv2`,
- shared DTOs used in requests have strict request-side twins named `Request<Name>`.

Model annotations support editor autocomplete and static checks; Pydantic performs runtime payload
validation. Every model accepts both the wire alias and the snake_case field name, and both
spellings are checked statically by mypy and pyright. Mixing alias and snake_case keywords in one
call is valid at runtime but rejected by type checkers. See the
[constructor typing notes](../installation.md#type-checking-pep-561) for examples.
Generated DTOs carry descriptions and per-field documentation sourced from
the upstream API; the same prose feeds editor tooltips and each model's JSON schema
(`model_json_schema()`).

`preference.delete_user_preference`, `preference.save_user_preference`, and `price_alert.save_pa`
return `stonepy.UnspecifiedResponse` because their catalog records document no response body.
Import it with `from stonepy import UnspecifiedResponse` for annotations or `isinstance()` checks.
Empty bodies and JSON null produce an empty model; unexpected object fields are preserved in
`model_extra`.

Every generated DTO has its own page in the **All models** navigation section, grouped into request
models, response models, enums, and other models. A few common examples:

## Session

- [`ApiLogOnRequestDTO`](../reference/models/ApiLogOnRequestDTO.md)
- [`ApiLogOnResponseDTOv2`](../reference/models/ApiLogOnResponseDTOv2.md)

## Orders

- [`NewTradeOrderRequestDTO`](../reference/models/NewTradeOrderRequestDTO.md)
- [`NewStopLimitOrderRequestDTO`](../reference/models/NewStopLimitOrderRequestDTO.md)
- [`CancelOrderRequestDTO`](../reference/models/CancelOrderRequestDTO.md)

## Assignment validation

Request DTOs remain mutable, but direct field assignments now run Pydantic validation.
Invalid values raise `ValidationError` immediately; accepted values may be coerced using the
same field rules as construction. To migrate, assign valid values at each step instead of
temporarily storing invalid values for later correction or server validation. Valid assignments,
including to previously unset fields, are included when the request is serialized.
Literal wrong-typed assignments to typed DTOs were already mypy errors before this release;
focus the runtime audit on dynamically supplied values, `Any`, unchecked code, and suppressed
diagnostics. Assigning an unknown attribute now raises `ValidationError` with error type
`no_such_attribute`, replacing the previous plain `ValueError` and its message; `except ValueError`
still catches it, but exact exception-type checks and message matching must be updated.

Every nested model reachable from the shipped request DTOs validates its own field assignments.
For example, assigning an invalid `market_id` on a watchlist item raises `ValidationError`.
In-place container edits such as `request.watchlist.items.append(...)` are not intercepted.
Replace the list through its field when you need its new contents validated.

```python
from stonepy.models import RequestApiClientAccountWatchlistItemDTO, SaveWatchlistRequestDTO

request = SaveWatchlistRequestDTO.model_validate(
    {"ClientAccountId": 1, "Watchlist": {"Items": [{"MarketId": 7}]}}
)
new_items = list(request.watchlist.items or [])
new_items.append(RequestApiClientAccountWatchlistItemDTO(market_id=8))
request.watchlist.items = new_items
```

Reassigning an existing DTO instance, including an item in a replacement list, does not deeply
revalidate its internals. Other ways to bypass validation include `model_copy(update=...)` and
direct `__dict__` writes. For validated updates, pass a plain mapping containing nested mappings
and lists to `model_validate(...)`, rather than an existing DTO instance:

```python
data = request.model_dump(mode="python", by_alias=True)
data["ClientAccountId"] = 2
request = SaveWatchlistRequestDTO.model_validate(data)
```

Here the dump converts the existing DTO tree to plain data before the updated data is validated.
When auditing data already changed through a validation bypass, prefer rebuilding from the
original input mapping; serialization of invalid model contents can warn or fail.

An extension-defined nested model must enable assignment validation in its own configuration;
its parent cannot intercept writes to that model's fields. Request submission does not deeply
revalidate existing model instances. Response models do not gain assignment validation.

## Request-side variants of shared DTOs

Request roots subclass `RequestModel` and reject unknown fields. Shared nested DTOs use
`RequestVariantModel` twins so construction and direct field assignment reject unknown fields
at every nesting level, subject to the validation bypasses above. Their
original `ResponseModel` classes remain tolerant and retain their names, aliases, defaults,
field documentation, and secret-field representation settings. Variants preserve those field
settings and all-optional defaults while rejecting unknown keys with `ValidationError`.

Tolerant instances are rejected in request positions with `ValidationError`. Construct the
corresponding variant or supply a mapping, including when passing a request body to an endpoint.
Variants accept only the exact alias or Python field name (no case-insensitive remap). For example,
`RequestApiStopLimitOrderDTOv2` accepts `TriggerPrice` and `trigger_price`, but rejects `triggerPrice`.
Response models continue to accept case-insensitive keys and ignore unknown nested fields.

To convert a tolerant instance you already hold, dump its aliases and validate the result:

```python
from stonepy.models import ApiIfDoneDTOv2, RequestApiIfDoneDTOv2

existing = ApiIfDoneDTOv2.model_validate({"Stop": {"TriggerPrice": "1.25"}})
request_if_done = RequestApiIfDoneDTOv2.model_validate(existing.model_dump(by_alias=True))
```

A dump cannot recover fields the tolerant parse already discarded. Rebuild from the original
input when you need to detect or correct those fields before sending a request.

| Original tolerant DTO | Strict request variant |
| --- | --- |
| `ApiClientAccountWatchlistDTO` | `RequestApiClientAccountWatchlistDTO` |
| `ApiClientAccountWatchlistItemDTO` | `RequestApiClientAccountWatchlistItemDTO` |
| `ApiClientPreferencesOverriddenSettingSaveDTO` | `RequestApiClientPreferencesOverriddenSettingSaveDTO` |
| `ApiClientPreferencesOverriddenSettingsSaveDTO` | `RequestApiClientPreferencesOverriddenSettingsSaveDTO` |
| `ApiClientPreferencesOverridenSettingSaveDTO` | `RequestApiClientPreferencesOverridenSettingSaveDTO` |
| `ApiClientPreferencesOverridenSettingsSaveDTO` | `RequestApiClientPreferencesOverridenSettingsSaveDTO` |
| `ApiDateTimeOffsetDTO` | `RequestApiDateTimeOffsetDTO` |
| `ApiFxFinancingDTO` | `RequestApiFxFinancingDTO` |
| `ApiIfDoneDTOv2` | `RequestApiIfDoneDTOv2` |
| `ApiKnockoutDTO` | `RequestApiKnockoutDTO` |
| `ApiMarketEodDTO` | `RequestApiMarketEodDTO` |
| `ApiMarketInformationDTOv2` | `RequestApiMarketInformationDTOv2` |
| `ApiMarketInformationSaveDTO` | `RequestApiMarketInformationSaveDTO` |
| `ApiMarketSpreadDTO` | `RequestApiMarketSpreadDTO` |
| `ApiStepMarginBandDTO` | `RequestApiStepMarginBandDTO` |
| `ApiStepMarginDTO` | `RequestApiStepMarginDTO` |
| `ApiStopLimitOrderDTOv2` | `RequestApiStopLimitOrderDTOv2` |
| `ApiTradingDayTimesDTO` | `RequestApiTradingDayTimesDTO` |
| `ClientPreferenceKeyDTO` | `RequestClientPreferenceKeyDTO` |
| `CorporateActionsDTO` | `RequestCorporateActionsDTO` |
| `IdentifierDTO` | `RequestIdentifierDTO` |
| `MarketPricesDTO` | `RequestMarketPricesDTO` |
| `OrderRequestDTO` | `RequestOrderRequestDTO` |
| `PreferenceDTO` | `RequestPreferenceDTO` |
| `Timestamp` | `RequestTimestamp` |

Five variant sources are reached by no endpoint response today:
`ApiClientPreferencesOverriddenSettingSaveDTO`, `ApiClientPreferencesOverriddenSettingsSaveDTO`,
`ApiIfDoneDTOv2`, `ApiMarketInformationSaveDTO`, and `OrderRequestDTO`. Their tolerant classes remain
because they are exported `ResponseModel`s referenced by other exported models, including
`ApiOrderDTOv2.if_done`. They are retained deliberately rather than converted in place.
