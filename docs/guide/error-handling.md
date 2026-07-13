# Error handling

All library exceptions inherit from `StoneXError`, so a single `except StoneXError` catches
everything stonepy can raise. Catch the more specific subclasses when you need to react to a
particular failure.

```python
from stonepy import (
    ClientConfig,
    ConfigurationError,
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
| `StoneXAPIError` | A non-success API response; exposes `http_status`, `error_code`, `error_message`. |
| `ResponseParseError` | The response body did not match the expected schema. |
| `TransportError` | The request never completed (connection or timeout error). |

See the [Errors API reference](../api/errors.md) for the full signatures.
