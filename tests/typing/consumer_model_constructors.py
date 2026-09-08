"""Alias and Python-name constructor forms supported at runtime.

The call-arg ignores record mypy's current rejection of Python names in generated constructors.
The consumer test removes them to pin those diagnostics until constructor typing is resolved.
"""

from pydantic import BaseModel

from stonepy.models import ApiLogOnRequestDTO, IdentifierDTO, RequestIdentifierDTO


def model_constructors() -> tuple[BaseModel, ...]:
    request_alias = ApiLogOnRequestDTO(
        UserName="user", Password="pw", AppKey="key", AppVersion="1", AppComments=""
    )
    request_python = ApiLogOnRequestDTO(  # type: ignore[call-arg]
        user_name="user", password="pw", app_key="key", app_version="1", app_comments=""
    )
    variant_alias = RequestIdentifierDTO(IdentifierCode="id")
    variant_python = RequestIdentifierDTO(identifier_code="id")  # type: ignore[call-arg]
    response_alias = IdentifierDTO(IdentifierCode="id")
    response_python = IdentifierDTO(identifier_code="id")  # type: ignore[call-arg]
    return (
        request_alias,
        request_python,
        variant_alias,
        variant_python,
        response_alias,
        response_python,
    )
