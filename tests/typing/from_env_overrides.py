"""Typed overrides, including deliberate invalid calls for diagnostic tests."""

from stonepy import ClientConfig, ClientConfigOverrides


def valid_overrides() -> ClientConfig:
    overrides: ClientConfigOverrides = {
        "base_url": "https://api.example",
        "read_timeout": 60.0,
        "username": None,
        "status_decoder": None,
    }
    return ClientConfig.from_env(**overrides)


def invalid_keyword() -> ClientConfig:
    return ClientConfig.from_env(base_url="https://api.example", typo=True)  # type: ignore[call-arg]


def invalid_value() -> ClientConfig:
    return ClientConfig.from_env(base_url="https://api.example", max_retries="3")  # type: ignore[arg-type]
