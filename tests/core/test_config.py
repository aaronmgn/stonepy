import pytest
from pytest import MonkeyPatch

from stonepy import __version__
from stonepy._core.config import ClientConfig
from stonepy._core.logging import redact, safe_repr


def test_from_env_reads_credentials(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("STONEX_BASE_URL", "https://demo.example/api")
    monkeypatch.setenv("STONEX_USERNAME", "alice")
    monkeypatch.setenv("STONEX_PASSWORD", "pw")
    monkeypatch.setenv("STONEX_APP_KEY", "ENV-K")
    cfg = ClientConfig.from_env(app_key="K")
    assert cfg.base_url == "https://demo.example/api"
    assert cfg.username == "alice"
    assert cfg.password == "pw"
    assert cfg.app_key == "K"


def test_client_config_documents_required_base_url_and_env_constructor() -> None:
    assert ClientConfig.__doc__ is not None
    assert "base_url" in ClientConfig.__doc__
    assert "from_env" in ClientConfig.__doc__


def test_default_user_agent_uses_package_version() -> None:
    assert ClientConfig(base_url="https://x").user_agent == f"stonepy/{__version__}"


def test_explicit_overrides_win(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("STONEX_USERNAME", "env-user")
    cfg = ClientConfig.from_env(base_url="https://x", username="explicit")
    assert cfg.username == "explicit"


def test_from_env_requires_base_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("STONEX_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="base_url is required"):
        ClientConfig.from_env()


def test_from_env_none_override_falls_back_to_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("STONEX_BASE_URL", "https://x")
    monkeypatch.setenv("STONEX_APP_KEY", "ENV-K")
    cfg = ClientConfig.from_env(app_key=None)
    assert cfg.app_key == "ENV-K"


def test_from_env_status_decoder_none_disables_default() -> None:
    cfg = ClientConfig.from_env(base_url="https://x", status_decoder=None)

    assert cfg.status_decoder is None


def test_from_env_unknown_override_raises_type_error() -> None:
    with pytest.raises(TypeError):
        ClientConfig.from_env(base_url="https://x", unknown=True)  # type: ignore[call-arg]


def test_config_repr_omits_secret_fields() -> None:
    cfg = ClientConfig(base_url="https://x", app_key="APP-SECRET", password="PW-SECRET")
    text = repr(cfg)
    assert "APP-SECRET" not in text
    assert "PW-SECRET" not in text
    assert all(name not in text for name in ("app_key", "password", "proxy"))
    assert "username" in text


def test_safe_repr_redacts_default_secret_keys() -> None:
    text = safe_repr(
        {
            "Session": "SESSION-VALUE",
            "Password": "PASSWORD-VALUE",
            "AppKey": "APPKEY-VALUE",
            "Authorization": "AUTH-VALUE",
        }
    )
    assert "SESSION-VALUE" not in text
    assert "PASSWORD-VALUE" not in text
    assert "APPKEY-VALUE" not in text
    assert "AUTH-VALUE" not in text
    assert text.count("***") == 4


def test_safe_repr_merges_custom_secret_keys_with_defaults() -> None:
    text = safe_repr({"Password": "PASSWORD-VALUE", "token": "TOKEN-VALUE"}, secret_keys={"token"})
    assert "PASSWORD-VALUE" not in text
    assert "TOKEN-VALUE" not in text
    assert text.count("***") == 2


def test_redact_masks_middle() -> None:
    assert redact("SECRET-TOKEN-12345").endswith("***")
    assert "SECRET" not in redact("SECRET-TOKEN-12345")


def test_from_env_uses_dataclass_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import MISSING, fields

    for var in ("STONEX_BASE_URL", "STONEX_APP_KEY", "STONEX_USERNAME", "STONEX_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    config = ClientConfig.from_env(base_url="https://x")
    for field in fields(ClientConfig):
        if field.default is not MISSING:
            assert getattr(config, field.name) == field.default


def test_from_env_unknown_none_override_raises_type_error() -> None:
    with pytest.raises(TypeError, match="unexpected ClientConfig override: unknown"):
        ClientConfig.from_env(base_url="https://x", unknown=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "   ",
        "host/x",
        "https:///x",
        "https://u:p@h/x",
        "https://h:99999/x",
        " https://h",
        "https://h ",
        "ftp://host/x",
        "https://[bad",
        "https://h:bad",
    ],
)
def test_config_rejects_invalid_base_urls(base_url: str) -> None:
    with pytest.raises(ValueError, match="base_url"):
        ClientConfig(base_url=base_url)


@pytest.mark.parametrize("base_url", ["https://[bad", "https://h:secret", "https://h:0"])
def test_invalid_url_errors_do_not_retain_parser_exception_context(base_url: str) -> None:
    with pytest.raises(ValueError, match="base_url must have a valid host and port") as caught:
        ClientConfig(base_url=base_url)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("base_url", [True, 5, None])
def test_config_rejects_wrong_base_url_type(base_url: object) -> None:
    from typing import Any, cast

    with pytest.raises(TypeError, match="base_url"):
        ClientConfig(base_url=cast(Any, base_url))


@pytest.mark.parametrize(
    "field",
    [
        "connect_timeout",
        "read_timeout",
        "write_timeout",
        "pool_timeout",
        "rate_limit_window_seconds",
        "proactive_refresh_seconds",
        "max_connections",
        "rate_limit_max",
        "max_retries",
        "retry_budget_seconds",
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1, True, "5", 1.5])
def test_config_rejects_invalid_numeric_values(field: str, value: object) -> None:
    from typing import Any

    integers = {"max_connections", "rate_limit_max", "max_retries"}
    kwargs: dict[str, Any] = {field: value}
    if (
        value == 0
        and not isinstance(value, bool)
        and field in {"max_retries", "retry_budget_seconds"}
    ):
        assert getattr(ClientConfig(base_url="https://x", **kwargs), field) == value
        return
    if value == 1.5 and field not in integers:
        assert getattr(ClientConfig(base_url="https://x", **kwargs), field) == value
        return
    wrong_type = isinstance(value, (bool, str)) or (field in integers and isinstance(value, float))
    with pytest.raises(TypeError if wrong_type else ValueError, match=field):
        ClientConfig(base_url="https://x", **kwargs)


def test_config_accepts_zero_retry_settings() -> None:
    config = ClientConfig(base_url="https://x", max_retries=0, retry_budget_seconds=0)
    assert config.max_retries == config.retry_budget_seconds == 0


@pytest.mark.parametrize(
    "overrides", [{"connect_timeout": 0}, {"base_url": "https://h:bad"}, {"base_url": True}]
)
def test_from_env_uses_constructor_validation(overrides: dict[str, object]) -> None:
    values = {"base_url": "https://x", **overrides}
    with pytest.raises((TypeError, ValueError)):
        ClientConfig.from_env(**values)  # type: ignore[arg-type]


def test_from_env_override_types_cover_all_init_fields() -> None:
    from dataclasses import fields
    from typing import get_type_hints

    from stonepy import ClientConfigOverrides

    config_types = get_type_hints(ClientConfig)
    override_types = get_type_hints(ClientConfigOverrides)
    assert set(override_types) == {field.name for field in fields(ClientConfig) if field.init}
    assert not ClientConfigOverrides.__required_keys__
    for name, annotation in override_types.items():
        assert annotation == config_types[name] | None
