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

- it re-authenticates in the background before the token expires, controlled by
  `ClientConfig.proactive_refresh_seconds` (default `1080.0`, i.e. 18 minutes), and
- it transparently re-logs-on if a request is rejected with an expired-session error.

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
