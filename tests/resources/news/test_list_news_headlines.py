from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import ListNewsHeadlinesRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_news_headlines_returns_response() -> None:
    respx.post("https://api.example/news/headlines").mock(return_value=httpx.Response(200, json={}))
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = ListNewsHeadlinesRequestDTO.model_construct()
        resp = client.news.list_news_headlines(request)
        assert resp is not None
    finally:
        client.close()
