# Models (DTOs)

Request and response DTO bodies are [Pydantic](https://docs.pydantic.dev/) models exported from
`stonepy.models`. Some methods take primitive parameters, and some return bare scalars or lists.
DTO naming follows the upstream API:

- endpoint request DTOs often end in `RequestDTO` or `RequestDTOv2`,
- response DTOs often end in `ResponseDTO` or `ResponseDTOv2`,
- shared DTOs have strict request-side twins named `Request<Name>`.

Because every model is fully typed, your editor autocompletes each field and `mypy` validates your
payloads. Every model carries a description and per-field documentation sourced from the upstream
API; the same prose feeds editor tooltips and each model's JSON schema (`model_json_schema()`).

Every model has its own page under [**All models**](../reference/models/), grouped into request
models, response models, enums, and other models. A few common examples:

## Session

- [`ApiLogOnRequestDTO`](../reference/models/ApiLogOnRequestDTO.md)
- [`ApiLogOnResponseDTOv2`](../reference/models/ApiLogOnResponseDTOv2.md)

## Orders

- [`NewTradeOrderRequestDTO`](../reference/models/NewTradeOrderRequestDTO.md)
- [`NewStopLimitOrderRequestDTO`](../reference/models/NewStopLimitOrderRequestDTO.md)
- [`CancelOrderRequestDTO`](../reference/models/CancelOrderRequestDTO.md)

## Request-side variants of shared DTOs

Request roots subclass `RequestModel` and reject unknown fields. Shared nested DTOs use
`RequestVariantModel` twins so request validation stays strict at every nesting level. Their
original `ResponseModel` classes remain tolerant and retain their names, aliases, defaults,
field documentation, and secret-field representation settings. Variants preserve those field
settings and all-optional defaults while rejecting unknown keys with `ValidationError`.

Tolerant instances are rejected in request positions with `ValidationError`. Construct the
corresponding variant or supply a mapping, including when passing a request body to an endpoint.
Variants accept only the exact alias or Python field name (no case-insensitive remap). For example,
`RequestApiStopLimitOrderDTOv2` accepts `TriggerPrice` and `trigger_price`, but rejects `triggerPrice`.
Response models continue to accept case-insensitive keys and ignore unknown nested fields.

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
