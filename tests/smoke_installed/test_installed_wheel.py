"""Smoke tests copied outside the checkout to exercise the published wheel."""

from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest
import respx

import stonepy
from stonepy import ClientConfig, StoneXClient

pytestmark = pytest.mark.skipif(
    os.environ.get("STONEPY_SMOKE_INSTALLED") != "1", reason="installed-wheel smoke test disabled"
)


def test_installed_wheel_imports_and_reports_version() -> None:
    assert stonepy.__file__ is not None
    assert "site-packages" in Path(stonepy.__file__).resolve().parts
    assert stonepy.__version__ == version("stonepy")


@respx.mock
def test_installed_wheel_client_call_with_respx() -> None:
    route = respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(
            200, json={"ClientPreferences": [{"Key": "wheel-smoke", "Value": "installed"}]}
        )
    )
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        response = client.client_preference.get_client_preferences_list(["wheel-smoke"], 1)
    assert response.client_preferences is not None
    assert [(item.key, item.value) for item in response.client_preferences] == [
        ("wheel-smoke", "installed")
    ]
    assert route.call_count == 1
    assert route.calls[0].request.url.params["keys"] == "wheel-smoke"
