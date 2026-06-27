"""HTTP transport: shared request building plus hand-written sync and async send classes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, assert_never, overload
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import httpx

from stonepy._core import codec
from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import EndpointSpec
from stonepy._core.logging import safe_repr

_SECRET_QUERY_KEYS = {"app_key", "appkey", "authorization", "password", "proxy", "session"}
_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _redact_url_query(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.query:
        return url
    redacted_query = urlencode(
        [
            (key, "***" if key.lower() in _SECRET_QUERY_KEYS else value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ],
        safe="*",
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, redacted_query, parsed.fragment))


def _find_key(mapping: dict[str, object], name: str) -> str | None:
    if name in mapping:
        return name
    name_lower = name.lower()
    for key in mapping:
        if key.lower() == name_lower:
            return key
    return None


def _resolve_template_value(
    name: str,
    *,
    preferred: dict[str, object],
    fallback: dict[str, object],
    missing_message: str,
    none_message: str,
) -> tuple[str, object, bool]:
    preferred_key = _find_key(preferred, name)
    if preferred_key is not None:
        value = preferred[preferred_key]
        if value is None:
            raise ValueError(f"{none_message}: {name}")
        return preferred_key, value, True

    fallback_key = _find_key(fallback, name)
    if fallback_key is not None:
        value = fallback[fallback_key]
        if value is None:
            raise ValueError(f"{none_message}: {name}")
        return fallback_key, value, False

    raise ValueError(f"{missing_message}: {name}")


def _serialize_query_value(value: object) -> str:
    if isinstance(value, (list, tuple)):
        if any(item is None for item in value):
            raise ValueError("Query sequence values cannot contain None")
        return ",".join(_serialize_query_value(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        formatted = codec.format_wcf_date(value)
        if formatted is None:
            raise ValueError("Query datetime values cannot be None")
        return formatted
    return str(value)


def _substitute_path_template(
    template: str,
    *,
    path_params: dict[str, object],
    query: dict[str, object],
    consumed_path_keys: set[str],
    consumed_query_keys: set[str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        key, value, from_path_params = _resolve_template_value(
            name,
            preferred=path_params,
            fallback=query,
            missing_message="Missing path params",
            none_message="Path params cannot be None",
        )
        if from_path_params:
            consumed_path_keys.add(key)
        else:
            consumed_query_keys.add(key)
        return quote(str(value), safe="")

    return _PLACEHOLDER_RE.sub(replace, template)


def _resolve_query_template(
    template: str,
    *,
    path_params: dict[str, object],
    query: dict[str, object],
    consumed_path_keys: set[str],
    consumed_query_keys: set[str],
) -> dict[str, str]:
    params: dict[str, str] = {}
    for key, value_template in parse_qsl(template, keep_blank_values=True):
        placeholder_match = _PLACEHOLDER_RE.fullmatch(value_template)
        if placeholder_match is None:
            params[key] = value_template
            continue

        name = placeholder_match.group(1)
        query_key = _find_key(query, name)
        if query_key is not None and query[query_key] is None:
            # A nullable query-template value (e.g. ``?TradingAccountId={TradingAccountId}``
            # where the caller omitted it) drops its whole ``key={value}`` segment rather than
            # leaving an unfilled placeholder or raising.
            consumed_query_keys.add(query_key)
            continue
        source_key, value, from_query = _resolve_template_value(
            name,
            preferred=query,
            fallback=path_params,
            missing_message="Missing template value",
            none_message="Template value cannot be None",
        )
        if from_query:
            consumed_query_keys.add(source_key)
        else:
            consumed_path_keys.add(source_key)
        params[key] = _serialize_query_value(value)
    return params


@dataclass(repr=False)
class Request:
    """A fully resolved HTTP request, ready for the transport to send.

    Attributes:
        method: The HTTP method.
        url: The absolute request URL, with path placeholders already substituted.
        headers: The request headers, including auth and user-agent.
        params: The resolved query-string parameters.
        content: The encoded request body, or ``None`` for bodyless requests.
    """

    method: str
    url: str
    headers: dict[str, str]
    params: dict[str, str]
    content: bytes | None

    def __repr__(self) -> str:
        """Return a repr with the URL query, headers, and body redacted."""
        content = "None" if self.content is None else f"<redacted {len(self.content)} bytes>"
        return (
            f"{type(self).__qualname__}(method={self.method!r}, "
            f"url={_redact_url_query(self.url)!r}, "
            f"headers={safe_repr(self.headers)}, params={safe_repr(self.params)}, "
            f"content={content})"
        )


def build_request(
    base_url: str,
    spec: EndpointSpec[Any],
    *,
    path_params: dict[str, object],
    query: dict[str, object],
    body_dict: dict[str, object] | None,
    auth_headers: dict[str, str],
    user_agent: str,
) -> Request:
    """Build a [`Request`][stonepy._core.transport.Request] from an endpoint spec and inputs.

    Substitutes path and query templates, serializes query values (dropping ``None``),
    encodes a JSON body when one is supplied, and merges auth and user-agent headers.

    Raises:
        ValueError: If a required path/template value is missing or ``None``, or if
            unexpected path parameters are supplied.
    """
    _assert_supported_param_locations(spec)
    path_template, separator, query_template = spec.path.partition("?")
    consumed_path_keys: set[str] = set()
    consumed_query_keys: set[str] = set()
    none_path_params = {key for key, value in path_params.items() if value is None}
    if none_path_params:
        raise ValueError(f"Path params cannot be None: {', '.join(sorted(none_path_params))}")

    path = _substitute_path_template(
        path_template,
        path_params=path_params,
        query=query,
        consumed_path_keys=consumed_path_keys,
        consumed_query_keys=consumed_query_keys,
    )
    if separator:
        params = _resolve_query_template(
            query_template,
            path_params=path_params,
            query=query,
            consumed_path_keys=consumed_path_keys,
            consumed_query_keys=consumed_query_keys,
        )
    else:
        params = {}

    extra_path_params = set(path_params) - consumed_path_keys
    if extra_path_params:
        raise ValueError(f"Unexpected path params: {', '.join(sorted(extra_path_params))}")

    url = base_url.rstrip("/") + path
    headers = {"User-Agent": user_agent, **auth_headers}
    params.update(
        {
            key: _serialize_query_value(value)
            for key, value in query.items()
            if key not in consumed_query_keys and value is not None
        }
    )
    content: bytes | None = None
    if body_dict is not None:
        headers["Content-Type"] = "application/json"
        content = codec.dumps(body_dict).encode("utf-8")
    return Request(spec.method, url, headers, params, content)


def _assert_supported_param_locations(spec: EndpointSpec[Any]) -> None:
    for param in spec.params:
        if param.location == "path":
            continue
        if param.location == "query":
            continue
        if param.location == "body":
            continue
        assert_never(param.location)


class SyncTransport:
    """Synchronous HTTP transport wrapping an ``httpx.Client``.

    Construct it either from a [`ClientConfig`][stonepy.ClientConfig] (which supplies the base
    URL, TLS, proxy, timeouts, and connection limits) or from explicit ``base_url``, ``verify``,
    and ``timeout`` primitives. Mixing the two forms raises ``TypeError``.
    """

    @overload
    def __init__(self, config: ClientConfig, /) -> None: ...

    @overload
    def __init__(
        self,
        base_url: str,
        verify: bool,
        timeout: float,
        proxy: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        base_url: ClientConfig | str,
        verify: bool | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> None:
        if isinstance(base_url, ClientConfig):
            if verify is not None or timeout is not None or proxy is not None:
                raise TypeError("ClientConfig transport construction does not accept overrides")
            self._client = httpx.Client(
                base_url=base_url.base_url,
                verify=base_url.verify_tls,
                proxy=base_url.proxy,
                timeout=httpx.Timeout(
                    base_url.read_timeout,
                    connect=base_url.connect_timeout,
                    read=base_url.read_timeout,
                    write=base_url.write_timeout,
                    pool=base_url.pool_timeout,
                ),
                limits=httpx.Limits(max_connections=base_url.max_connections),
            )
            return

        if verify is None or timeout is None:
            raise TypeError("verify and timeout are required when constructing from primitives")
        self._client = httpx.Client(
            base_url=base_url,
            verify=verify,
            timeout=timeout,
            proxy=proxy,
        )

    def send(self, req: Request) -> httpx.Response:
        """Send *req* and return the raw ``httpx.Response``."""
        return self._client.request(
            req.method,
            req.url,
            headers=req.headers,
            params=req.params,
            content=req.content,
        )

    def close(self) -> None:
        """Close the underlying HTTP client and its connection pool."""
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport wrapping an ``httpx.AsyncClient``.

    The awaitable twin of [`SyncTransport`][stonepy._core.transport.SyncTransport], with the
    same two construction forms.
    """

    @overload
    def __init__(self, config: ClientConfig, /) -> None: ...

    @overload
    def __init__(
        self,
        base_url: str,
        verify: bool,
        timeout: float,
        proxy: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        base_url: ClientConfig | str,
        verify: bool | None = None,
        timeout: float | None = None,
        proxy: str | None = None,
    ) -> None:
        if isinstance(base_url, ClientConfig):
            if verify is not None or timeout is not None or proxy is not None:
                raise TypeError("ClientConfig transport construction does not accept overrides")
            self._client = httpx.AsyncClient(
                base_url=base_url.base_url,
                verify=base_url.verify_tls,
                proxy=base_url.proxy,
                timeout=httpx.Timeout(
                    base_url.read_timeout,
                    connect=base_url.connect_timeout,
                    read=base_url.read_timeout,
                    write=base_url.write_timeout,
                    pool=base_url.pool_timeout,
                ),
                limits=httpx.Limits(max_connections=base_url.max_connections),
            )
            return

        if verify is None or timeout is None:
            raise TypeError("verify and timeout are required when constructing from primitives")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            verify=verify,
            timeout=timeout,
            proxy=proxy,
        )

    async def asend(self, req: Request) -> httpx.Response:
        """Send *req* and return the raw ``httpx.Response``."""
        return await self._client.request(
            req.method,
            req.url,
            headers=req.headers,
            params=req.params,
            content=req.content,
        )

    async def aclose(self) -> None:
        """Close the underlying async HTTP client and its connection pool."""
        await self._client.aclose()
