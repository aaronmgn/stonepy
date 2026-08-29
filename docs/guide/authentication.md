# Authentication & sessions

Calling `client.session.log_on(...)` establishes the authenticated session token that the client
attaches to every subsequent request. The token is held by the client for the life of its context
manager.

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

If you supply `app_key`, `username`, and `password` on `ClientConfig` (directly or via
`ClientConfig.from_env()`), the client refreshes the session automatically:

- it re-authenticates as a synchronous pre-request step when the stored token reaches
  `ClientConfig.proactive_refresh_seconds` (default `1080.0`, i.e. 18 minutes), and
- it transparently re-logs-on if a request is rejected with an expired-session error.

The proactive step is fail-soft. If it raises a stonepy error, the client logs one warning on
`stonepy.pipeline` and sends the request with the existing token. The normal reactive `401`
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
    Without those credentials you must call `log_on` yourself and manage re-authentication.

## Credential handling

`stonepy` transmits your credentials (username, password, app key, session token) to the
configured API host and redacts them from its logs and exception output. You remain responsible
for storing them securely - for example in environment variables or a secrets manager - and never
committing them to source control.
