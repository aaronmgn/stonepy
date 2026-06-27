# Models (DTOs)

All request and response bodies are [Pydantic](https://docs.pydantic.dev/) models exported from
`stonepy.models`. Naming follows the upstream API:

- request DTO names end in `RequestDTO`,
- response DTO names end in `ResponseDTO`,
- v2 variants end in `...DTOv2`.

Because every model is fully typed, your editor autocompletes each field and `mypy` validates your
payloads. There are 237 models in total; a representative selection is documented below, and the
rest follow the same pattern and import directly from `stonepy.models`.

## Session

::: stonepy.models.ApiLogOnRequestDTO

::: stonepy.models.ApiLogOnResponseDTOv2

## Orders

::: stonepy.models.NewTradeOrderRequestDTO

::: stonepy.models.NewStopLimitOrderRequestDTO

::: stonepy.models.CancelOrderRequestDTO
