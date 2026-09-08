# Error handling

`StoneXError` is the base of stonepy's public runtime error hierarchy, so a single
`except StoneXError` catches those runtime failures. Configuration validation
can also raise builtin `TypeError` or `ValueError`. Catch the more specific subclasses when you
need to react to a particular runtime failure.

```python
from stonepy import (
    ClientConfig,
    ConfigurationError,
    OrderStatusUnknownError,
    RateLimitError,
    StoneXAPIError,
    StoneXClient,
    StoneXError,
)
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

try:
    with StoneXClient(config) as client:
        client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="username",
                Password="password",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
except RateLimitError as exc:
    print(exc.retry_after)
except OrderStatusUnknownError as exc:
    # Do not blindly retry: the original write may have succeeded.
    print(exc.status, "verify the order state before resubmitting")
except StoneXAPIError as exc:
    print(exc.http_status, exc.error_code, exc.error_message)
except StoneXError as exc:
    print(exc)
```

## Exception hierarchy

| Exception | Raised when |
| --- | --- |
| `AuthenticationError` | Log-on failed or the session could not be refreshed. |
| `ConfigurationError` | The client has no credentials configured for session refresh. |
| `RateLimitError` | The API returned a rate-limit response; inspect `retry_after`. |
| `OrderRejectedError` | The request was accepted but the order was rejected. |
| `OrderStatusUnknownError` | A write acknowledgement could not be interpreted; the order may or may not have been placed. |
| `StoneXAPIError` | A non-success API response; exposes `http_status`, `error_code`, `error_message`. |
| `ResponseParseError` | The response body did not match the expected schema. |
| `TransportError` | The request never completed (connection or timeout error). |

See the [Errors API reference](../api/errors.md) for the full signatures.

## Rejection semantics

A successful HTTP response is not always a successful order. For endpoints that acknowledge a
write, stonepy uses the endpoint's documented status domain:

| Domain | Rejection behavior |
| --- | --- |
| Instruction | Top-level `InstructionStatus` `RedCard` (2) and `Error` (4) raise `OrderRejectedError`. `Accepted` (1), `YellowCard` (3), and `Pending` (5) return the response. A yellow card is awaiting dealer approval and must not be treated as permission to resubmit. |
| Order | `OrderStatus` `Rejected` (5) and `RedCard` (10) raise. Other lifecycle values, including unknown numeric values, are informational. Simulation responses use this domain. |
| Execution text | `save_order` accepts `Success`, raises `OrderRejectedError` for `Failure`, and raises `OrderStatusUnknownError` for every other supplied text or numeric status. Matching ignores case and surrounding whitespace. |

With status checks enabled, every acknowledgement endpoint in the instruction, order, and
execution-text domains raises `OrderStatusUnknownError` for an empty body or a missing, null,
boolean, or malformed status. These are the affected methods (on both clients):

| Domain | Methods |
| --- | --- |
| Instruction | `order.cancel_order`, `order.order` (also `order.place_order`), `order.trade`, `order.update_order`, `order.update_trade`, `fixed_margin.trade_fm`, `fixed_margin.update_trade_fm` |
| Order | `order.simulate_cancel_order`, `order.simulate_order`, `order.simulate_trade`, `order.simulate_update_order`, `order.simulate_update_trade` |
| Execution text | `order.save_order` |

See the [order](../api/resources.md#order) and [fixed-margin](../api/resources.md#fixed_margin)
endpoint references for their signatures. Setting `status_decoder=None` bypasses these checks;
JSON decoding and response-model validation still apply.

After an instruction acknowledgement passes, stonepy also checks each `Orders[]` item using the
order domain. Fixed-margin responses expose the same two layers as
`InstructionStatusId`/`InstructionStatusReasonId` and `OrderStatusId`/`OrderStatusReasonId`.
Nested quote statuses are not interpreted.

Read endpoints do not run rejection checks. Their status fields describe stored current or
historical state, so a returned `Rejected` order is data rather than a failed read.

`OrderStatusUnknownError` is intentionally not a subclass of `OrderRejectedError`. It means the
acknowledgement for a non-idempotent write was unreadable, so the order **may or may not have been
placed**. Inspect the attached `response`, query the order state, and reconcile by request/order
identifier before resubmitting. A handler that automatically retries `OrderRejectedError` will
therefore never catch this indeterminate case.

Validation, response-parse, and fallback API errors keep ordinary `str`, `repr`, and traceback
text free of request inputs and response bodies. Diagnostic attributes such as `raw_body`,
`response`, and Pydantic `ValidationError.errors()` may still hold secrets; handle them as
sensitive data rather than writing them to ordinary logs.
