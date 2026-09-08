from urllib.parse import parse_qs, urlsplit

import pytest

from stonepy._core import errors, pipeline, transport
from stonepy._core.logging import SECRET_KEYS, safe_repr
from stonepy._generator import render


@pytest.mark.parametrize("key", sorted(SECRET_KEYS))
@pytest.mark.parametrize("uppercase", [False, True])
def test_secret_keys_union_is_redacted_in_every_context(key: str, uppercase: bool) -> None:
    key = key.upper() if uppercase else key
    assert safe_repr({key: "v"}) == repr({key: "***"})
    assert errors._safe_headers({key: "v"}) == {key: "***"}
    assert pipeline._redact_headers({key: "v"}) == {key: "***"}
    redacted = transport._redact_url_query(f"https://x/?{key}=v")
    assert parse_qs(urlsplit(redacted).query) == {key: ["***"]}
    assert key.lower() in render._SECRET_FIELD_RAW_NAMES
