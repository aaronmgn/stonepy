"""Discover strict request-side DTO dependencies without changing response models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from stonepy._generator import render
from stonepy._generator.catalog import Catalog, is_enum_record, python_name, python_type


class UnsupportedRequestParameterTypeError(ValueError):
    """A compound endpoint parameter needs an unsupported request DTO binding."""


class RequestVariantNameCollisionError(ValueError):
    """A generated request variant would shadow an existing catalog name."""


@dataclass(frozen=True)
class RequestTypeGraph:
    """Request roots and the strict twins of their transitive DTO dependencies."""

    roots: frozenset[str]
    reachable: frozenset[str]
    variants: Mapping[str, str]

    def request_name(self, name: str) -> str:
        """Return the request-side name, preserving roots and enum names."""
        return self.variants.get(name, name)


def request_type_names(catalog: Catalog, known_names: set[str]) -> set[str]:
    """Return endpoint request types and plain body/query model parameters."""
    roots = {endpoint.request_type for endpoint in catalog.endpoints if endpoint.request_type}
    for endpoint in catalog.endpoints:
        for param in endpoint.parameters:
            if (param.get("in") or param.get("location")) not in {"body", "query"}:
                continue
            for key in ("ref", "type"):
                raw_name = param.get(key)
                if (
                    isinstance(raw_name, str)
                    and not any(marker in raw_name for marker in ("[", "]", "|"))
                    and python_name(raw_name) in known_names
                ):
                    roots.add(python_name(raw_name))
    return roots


def build_request_type_graph(catalog: Catalog) -> RequestTypeGraph:
    """Traverse resolved annotations and reject ambiguous request variant bindings.

    Raises:
        UnsupportedRequestParameterTypeError: A compound parameter embeds a non-root DTO.
        RequestVariantNameCollisionError: A strict twin's name is already in the catalog.
    """
    known_names = {rec.name for rec in catalog.datatypes} | {
        python_name(name) for name in catalog.lookups
    }
    model_names = {rec.name for rec in catalog.datatypes if not is_enum_record(rec)}
    roots = request_type_names(catalog, known_names)
    for endpoint in catalog.endpoints:
        for param in endpoint.parameters:
            if (param.get("in") or param.get("location")) not in {"body", "query"}:
                continue
            annotation = python_type(param, known_names)
            raw_type = param.get("type")
            if isinstance(raw_type, str) and any(marker in raw_type for marker in ("[", "|")):
                annotation = raw_type
            embedded = (render._annotation_tokens(annotation) & model_names) - roots
            if embedded - {annotation}:
                raise UnsupportedRequestParameterTypeError(
                    f"{endpoint.target}.{endpoint.name} parameter {param.get('name')}: "
                    f"unsupported compound request annotation {annotation}"
                )

    edges = {
        rec.name: set().union(
            *(
                render._annotation_tokens(
                    render.resolved_field_annotation(rec.name, prop, known_names)
                )
                & model_names
                for prop in rec.properties
            )
        )
        for rec in catalog.datatypes
        if rec.name in model_names
    }
    visited: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name not in visited:
            visited.add(name)
            pending.extend(edges.get(name, set()) - visited)
    reachable = frozenset((visited - roots) & model_names)
    variants = {name: f"Request{name}" for name in sorted(reachable)}
    for original, variant in variants.items():
        if variant in known_names:
            raise RequestVariantNameCollisionError(f"{original}: variant {variant} already exists")
    return RequestTypeGraph(frozenset(roots), reachable, MappingProxyType(variants))


def rewrite_request_annotation(annotation: str, variants: Mapping[str, str]) -> str:
    """Replace whole identifier tokens with their request-side names."""
    return render._IDENTIFIER_RE.sub(lambda match: variants.get(match[0], match[0]), annotation)
