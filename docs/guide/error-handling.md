# Error handling

All library exceptions inherit from `StoneXError`, so a single `except StoneXError` catches
everything stonepy can raise. Catch the more specific subclasses when you need to react to a
particular failure.

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
