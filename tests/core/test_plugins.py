from collections.abc import Callable
from typing import cast, get_args, get_type_hints

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pytest import LogCaptureFixture

from stonepy import StoneXClient
from stonepy._core.config import ClientConfig
from stonepy._core.plugins import discover_plugin_resources, load_plugin_resources
from stonepy._core.resource import BaseResource


class _EP:
    def __init__(self, name: str, loader: Callable[[], object]) -> None:
        self.name = name
        self._loader = loader

    def load(self) -> object:
        return self._loader()


def _resource_type(name: str) -> type[BaseResource]:
    return cast(type[BaseResource], type(name, (BaseResource,), {}))


def _resource_type_with_requirement(name: str, requirement: str) -> type[BaseResource]:
    resource = _resource_type(name)
    resource.requires_stonepy = requirement  # type: ignore[attr-defined]
    return resource


def _raise_boom() -> object:
    raise RuntimeError("boom")


def test_disabled_returns_empty() -> None:
    assert (
        load_plugin_resources(enable=False, allow_overrides=(), known=set(), entry_points=[]) == {}
    )


def test_entry_points_are_typed_with_protocol() -> None:
    hints = get_type_hints(load_plugin_resources)
    entry_points_hint = hints["entry_points"]

    assert "EntryPoint" in repr(get_args(entry_points_hint)[0])


def test_duplicate_without_override_raises() -> None:
    ep = _EP("order", lambda: _resource_type("X"))
    with pytest.raises(ValueError, match="order"):
        load_plugin_resources(enable=True, allow_overrides=(), known={"order"}, entry_points=[ep])


def test_duplicate_with_override_is_allowed() -> None:
    resource = _resource_type("OrderPlugin")
    ep = _EP("order", lambda: resource)

    out = load_plugin_resources(
        enable=True,
        allow_overrides=("order",),
        known={"order"},
        entry_points=[ep],
    )

    assert out == {"order": resource}


def test_duplicate_third_party_plugin_names_raise() -> None:
    first = _EP("extra", lambda: _resource_type("FirstPlugin"))
    second = _EP("extra", lambda: _resource_type("SecondPlugin"))

    with pytest.raises(ValueError, match="extra"):
        load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[first, second],
        )


def test_duplicate_allowed_override_candidates_raise() -> None:
    first = _EP("order", lambda: _resource_type("FirstOrderPlugin"))
    second = _EP("order", lambda: _resource_type("SecondOrderPlugin"))

    with pytest.raises(ValueError, match="order"):
        load_plugin_resources(
            enable=True,
            allow_overrides=("order",),
            known={"order"},
            entry_points=[first, second],
        )


def test_duplicate_failing_then_successful_plugin_names_raise() -> None:
    bad = _EP("extra", _raise_boom)
    good = _EP("extra", lambda: _resource_type("ExtraPlugin"))

    with pytest.raises(ValueError, match="extra"):
        load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[bad, good],
        )


def test_duplicate_successful_then_failing_plugin_names_raise() -> None:
    good = _EP("extra", lambda: _resource_type("ExtraPlugin"))
    bad = _EP("extra", _raise_boom)

    with pytest.raises(ValueError, match="extra"):
        load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[good, bad],
        )


def test_failing_plugin_is_skipped_and_logged(caplog: LogCaptureFixture) -> None:
    bad = _EP("bad", _raise_boom)
    good_resource = _resource_type("ExtraPlugin")
    good = _EP("extra", lambda: good_resource)

    with caplog.at_level("WARNING", logger="stonepy.plugins"):
        out = load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[bad, good],
        )

    assert out == {"extra": good_resource}
    assert "plugin bad failed to load: boom; continuing" in caplog.text


def test_non_class_plugin_export_is_skipped_and_logged(caplog: LogCaptureFixture) -> None:
    bad = _EP("bad", lambda: object())
    good_resource = _resource_type("ExtraPlugin")
    good = _EP("extra", lambda: good_resource)

    with caplog.at_level("WARNING", logger="stonepy.plugins"):
        out = load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[bad, good],
        )

    assert out == {"extra": good_resource}
    assert "plugin bad did not load a BaseResource subclass; continuing" in caplog.text


def test_incompatible_plugin_requirement_raises() -> None:
    ep = _EP("future", lambda: _resource_type_with_requirement("FuturePlugin", ">=9.0,<10"))

    with pytest.raises(ValueError, match="requires stonepy"):
        load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[ep],
            stonepy_version="0.1.0",
        )


@pytest.mark.parametrize("requirement", ["not-a-requirement", "=>9.0"])
def test_malformed_plugin_requirement_raises(requirement: str) -> None:
    ep = _EP("bad", lambda: _resource_type_with_requirement("BadPlugin", requirement))

    with pytest.raises(ValueError, match="invalid requires_stonepy"):
        load_plugin_resources(
            enable=True,
            allow_overrides=(),
            known=set(),
            entry_points=[ep],
            stonepy_version="0.1.0",
        )


def test_discover_plugin_resources_does_not_read_entry_points_when_disabled(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_entry_points(*, group: str) -> list[object]:
        raise AssertionError(f"unexpected entry point discovery for {group}")

    monkeypatch.setattr("stonepy._core.plugins.metadata_entry_points", fail_entry_points)

    assert (
        discover_plugin_resources(
            enable=False,
            allow_overrides=(),
            known=set(),
            entry_points=None,
        )
        == {}
    )


def test_discover_plugin_resources_reads_entry_points_when_enabled() -> None:
    resource = _resource_type_with_requirement("ExtraPlugin", ">=0.1,<0.2")
    ep = _EP("extra", lambda: resource)

    out = discover_plugin_resources(
        enable=True,
        allow_overrides=(),
        known=set(),
        entry_points=[ep],
        stonepy_version="0.1.0",
    )

    assert out == {"extra": resource}


def test_load_plugin_resources_defaults_to_installed_package_version(
    monkeypatch: MonkeyPatch,
) -> None:
    resource = _resource_type_with_requirement("ExtraPlugin", ">=9.0,<10.0")
    ep = _EP("extra", lambda: resource)
    monkeypatch.setattr("stonepy._core.plugins.metadata_version", lambda name: "9.0.0")

    out = load_plugin_resources(
        enable=True,
        allow_overrides=(),
        known=set(),
        entry_points=[ep],
    )

    assert out == {"extra": resource}


def test_generated_client_instantiates_enabled_plugins(monkeypatch: MonkeyPatch) -> None:
    class ExtraResource(BaseResource):
        def base_url(self) -> str:
            return self._ctx.config.base_url

    captured: dict[str, object] = {}

    def fake_discover(
        *,
        enable: bool,
        allow_overrides: tuple[str, ...],
        known: set[str],
    ) -> dict[str, type[BaseResource]]:
        captured["enable"] = enable
        captured["allow_overrides"] = allow_overrides
        captured["known"] = known
        return {"extra": ExtraResource}

    monkeypatch.setattr("stonepy.client.discover_plugin_resources", fake_discover)
    client = StoneXClient(
        ClientConfig(
            base_url="https://api.example",
            enable_plugins=True,
            allow_overrides=("session",),
        )
    )
    try:
        plugin = client.plugin("extra")

        assert isinstance(plugin, ExtraResource)
        assert plugin.base_url() == "https://api.example"
        # The client passes the loader every built-in resource name so plugins cannot silently
        # shadow one; derive that set from the client's resource properties.
        expected_known = {
            name for name, value in vars(StoneXClient).items() if isinstance(value, property)
        }
        assert "session" in expected_known
        assert captured == {
            "enable": True,
            "allow_overrides": ("session",),
            "known": expected_known,
        }
    finally:
        client.close()
