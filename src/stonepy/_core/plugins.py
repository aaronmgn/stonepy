"""Out-of-tree resource plugins via entry points: fail-loud, isolated."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import entry_points as metadata_entry_points
from importlib.metadata import version as metadata_version
from typing import Protocol

from stonepy._core.resource import BaseResource

logger = logging.getLogger("stonepy.plugins")
_REQUIREMENT_PART_RE = re.compile(r"(>=|<=|==|>|<)\s*(\d+(?:\.\d+){0,2})")
_FALLBACK_STONEPY_VERSION = "0.1.0"


class _EntryPoint(Protocol):
    name: str

    def load(self) -> object: ...


def load_plugin_resources(
    *,
    enable: bool,
    allow_overrides: tuple[str, ...],
    known: set[str],
    entry_points: Iterable[_EntryPoint],
    stonepy_version: str | None = None,
) -> dict[str, type[BaseResource]]:
    if not enable:
        return {}

    current_version = stonepy_version or _current_stonepy_version()
    seen: set[str] = set()
    loaded: dict[str, type[BaseResource]] = {}
    for ep in entry_points:
        if ep.name in known and ep.name not in allow_overrides:
            raise ValueError(
                f"plugin resource {ep.name!r} collides with a built-in; "
                "add it to allow_overrides to override"
            )
        if ep.name in seen:
            raise ValueError(f"plugin resource {ep.name!r} was declared more than once")
        seen.add(ep.name)
        try:
            resource = ep.load()
        except Exception as exc:  # noqa: BLE001
            logger.warning("plugin %s failed to load: %s; continuing", ep.name, exc)
            continue

        if not isinstance(resource, type) or not issubclass(resource, BaseResource):
            logger.warning("plugin %s did not load a BaseResource subclass; continuing", ep.name)
            continue
        _check_requires_stonepy(ep.name, resource, current_version)
        loaded[ep.name] = resource
    return loaded


def discover_plugin_resources(
    *,
    enable: bool,
    allow_overrides: tuple[str, ...],
    known: set[str],
    entry_points: Iterable[_EntryPoint] | None = None,
    stonepy_version: str | None = None,
) -> dict[str, type[BaseResource]]:
    if not enable:
        return {}
    discovered = (
        entry_points
        if entry_points is not None
        else metadata_entry_points(group="stonepy.resources")
    )
    return load_plugin_resources(
        enable=enable,
        allow_overrides=allow_overrides,
        known=known,
        entry_points=discovered,
        stonepy_version=stonepy_version,
    )


def _check_requires_stonepy(name: str, resource: type, stonepy_version: str) -> None:
    requirement = getattr(resource, "requires_stonepy", None)
    if requirement is None:
        return
    if not isinstance(requirement, str):
        raise ValueError(f"plugin resource {name!r} has invalid requires_stonepy")
    if not _matches_simple_requirement(stonepy_version, requirement):
        raise ValueError(
            f"plugin resource {name!r} requires stonepy {requirement}, "
            f"but current version is {stonepy_version}"
        )


def _current_stonepy_version() -> str:
    try:
        return metadata_version("stonepy")
    except PackageNotFoundError:
        return _FALLBACK_STONEPY_VERSION


def _matches_simple_requirement(version: str, requirement: str) -> bool:
    current = _version_tuple(version)
    for raw_part in requirement.split(","):
        part = raw_part.strip()
        if not part:
            continue
        match = _REQUIREMENT_PART_RE.fullmatch(part)
        if match is None:
            raise ValueError(f"invalid requires_stonepy requirement: {requirement}")
        operator, required_version = match.groups()
        required = _version_tuple(required_version)
        if operator == ">=":
            if current < required:
                return False
            continue
        if operator == ">":
            if current <= required:
                return False
            continue
        if operator == "<=":
            if current > required:
                return False
            continue
        if operator == "<":
            if current >= required:
                return False
            continue
        if operator == "==" and current != required:
            return False
    return True


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    values = [int(part) if part.isdigit() else 0 for part in parts[:3]]
    while len(values) < 3:
        values.append(0)
    return (values[0], values[1], values[2])
