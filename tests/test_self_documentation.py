"""Guard the self-documentation contract that the docs site and IDE tooling rely on."""

from __future__ import annotations

import enum
import inspect

import pytest

import stonepy
import stonepy.models as models
import stonepy.resources as resources


def _public_model_names() -> list[str]:
    return sorted(models.__all__)


@pytest.mark.parametrize("name", _public_model_names())
def test_every_model_and_enum_has_a_class_docstring(name: str) -> None:
    obj = getattr(models, name)
    assert inspect.isclass(obj)
    assert obj.__doc__ and obj.__doc__.strip(), f"{name} is missing a class docstring"


def test_model_field_descriptions_reach_field_info_and_json_schema() -> None:
    # use_attribute_docstrings lifts each generated field's docstring into its description,
    # so the same prose feeds editor tooltips and ``model_json_schema()``.
    field = models.NewTradeOrderRequestDTO.model_fields["market_id"]
    assert field.description == "The unique identifier for a market."

    schema = models.NewTradeOrderRequestDTO.model_json_schema()
    assert schema["properties"]["MarketId"]["description"] == "The unique identifier for a market."


def test_every_generated_model_field_is_documented() -> None:
    undocumented: list[str] = []
    for name in models.__all__:
        obj = getattr(models, name)
        if isinstance(obj, type) and issubclass(obj, enum.Enum):
            continue
        for field_name, field in obj.model_fields.items():
            if not (field.description and field.description.strip()):
                undocumented.append(f"{name}.{field_name}")
    assert not undocumented, f"models with undocumented fields: {undocumented[:10]}"


@pytest.mark.parametrize("name", sorted(resources.__all__))
def test_every_resource_group_class_has_a_docstring(name: str) -> None:
    obj = getattr(resources, name)
    assert inspect.isclass(obj)
    assert obj.__doc__ and obj.__doc__.strip(), f"{name} is missing a class docstring"


def test_resource_methods_are_documented() -> None:
    # Inherited endpoint methods carry the upstream description as their docstring.
    method = resources.MarketResource.get_market_information
    assert method.__doc__ and method.__doc__.strip()


@pytest.mark.parametrize("name", sorted(set(stonepy.__all__) - {"__version__"}))
def test_public_package_symbols_have_docstrings(name: str) -> None:
    obj = getattr(stonepy, name)
    assert obj.__doc__ and obj.__doc__.strip(), f"stonepy.{name} is missing a docstring"
