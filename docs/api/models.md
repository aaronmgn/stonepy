# Models (DTOs)

Request and response DTO bodies are [Pydantic](https://docs.pydantic.dev/) models exported from
`stonepy.models`. Some methods take primitive parameters, and some return bare scalars or lists.
DTO naming follows the upstream API:

- request DTO names end in `RequestDTO` or `RequestDTOv2`,
- response DTO names end in `ResponseDTO` or `ResponseDTOv2`.

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
