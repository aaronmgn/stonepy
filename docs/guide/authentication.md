# Authentication & sessions

Calling `client.session.log_on(...)` establishes the authenticated session token. The client
attaches the current token to subsequent endpoints that use session authentication. Refresh can
replace the token, and `client.session.delete_session(...)` clears it.

```python
from stonepy import ClientConfig, StoneXClient
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

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
```

## Automatic session refresh

Automatic refresh is enabled in either of these ways:

- Supply `app_key`, `username`, and `password` on `ClientConfig`, directly or via
  `ClientConfig.from_env()`. This lets the client refresh without an explicit `log_on()` call.
- Complete a manual `log_on()` successfully. It installs a replay refresh callable using that
  request, so both proactive and reactive refresh work for the manual session.

The client then refreshes in two situations:

- Proactive refresh runs inline, immediately before the request that needs it - synchronously in
  `StoneXClient` and awaited in `AsyncStoneXClient`, with no background task - when the stored
  token reaches `ClientConfig.proactive_refresh_seconds` (default `1080.0`, i.e. 18 minutes).
  This threshold is based on token age; no server expiry timestamp is consulted.
- After HTTP `401` or `ErrorCode` `4011` (never `4010`) on an authenticated endpoint, the client
  refreshes the session once and replays the request once. This applies to every endpoint,
  including non-idempotent order calls, because this authentication rejection means the server
  did not process the request. Transport, `5xx`, and `429` retries remain idempotency-gated.

The proactive step is fail-soft. If it raises a stonepy error, the client logs one warning on
`stonepy.pipeline` and sends the request with the existing token. The reactive authentication
refresh and one-time replay can still recover the call.

```python
config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    app_key="app-key",
    username="username",
    password="password",
)  # credentials present -> automatic proactive session refresh
```

!!! note
    Config credentials are one way to enable refresh, not the only one. A successful manual
    `log_on()` installs the refresh callable used for that session.

## Credential handling

`stonepy` transmits your credentials (username, password, app key, session token) to the
configured API host. Its own `ClientConfig` and request representations mask values keyed as app
key, password, session, authorization, or proxy. Usernames are not masked, and logging from the
external HTTP stack is not sanitized by stonepy. You remain responsible for storing credentials
securely - for example in environment variables or a secrets manager - and never committing them
to source control.
