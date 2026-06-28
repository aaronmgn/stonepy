from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_news_headlines_with_source_returns_response() -> None:
    respx.get("https://api.example/news/1/1").mock(return_value=httpx.Response(200, json={}))
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        source = "x"
        category = "x"
        max_results = 1
        resp = client.news.list_news_headlines_with_source(
            source, category, max_results=max_results
        )
        assert resp is not None
    finally:
        client.close()
