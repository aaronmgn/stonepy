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
        ClientConfig.from_env(base_url="https://x", unknown=True)


def test_config_repr_redacts_secret_fields() -> None:
    cfg = ClientConfig(base_url="https://x", app_key="APP-SECRET", password="PW-SECRET")
    text = repr(cfg)
    assert "APP-SECRET" not in text
    assert "PW-SECRET" not in text
    assert "***" in text


def test_config_repr_redacts_proxy_credentials() -> None:
    cfg = ClientConfig(base_url="https://x", proxy="http://user:secret@proxy.example:8080")
    text = repr(cfg)
    assert "secret" not in text
    assert "***" in text


def test_safe_repr_redacts_config_secret_fields() -> None:
    cfg = ClientConfig(base_url="https://x", app_key="APP-SECRET", password="PW-SECRET")
    text = safe_repr(cfg)
    assert "APP-SECRET" not in text
    assert "PW-SECRET" not in text
    assert "***" in text


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
