# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-07-13

### Changed

- **BREAKING:** The proactive client-side rate limit now applies one aggregate
  `rate_limit_max` / `rate_limit_window_seconds` window across all endpoint resource groups,
  matching CIAPI's documented server-wide 500-request/5-second budget. Resource groups no longer
  receive independent windows that can multiply aggregate traffic.
- **BREAKING:** An undocumented instruction status, unknown `save_order` text status, or numeric
  `save_order` status now raises the new `OrderStatusUnknownError` instead of warning and returning
  an indeterminate response. The exception is not an `OrderRejectedError`: the order may or may
  not have been placed, and callers must verify order state before resubmitting.
- **BREAKING:** Business-status rejection checking now runs only on endpoints with an explicit
  placement/simulation acknowledgement domain. Read endpoints no longer raise
  `OrderRejectedError` merely because returned current or historical data contains a rejected
  stored order status.

### Fixed

- Trade/order placement responses now decode top-level `ApiTradeOrderResponseDTO.Status` and
  `StatusReason` as `InstructionStatus`/`InstructionStatusReason`; only nested `Orders[]` uses
  `OrderStatus`/`OrderStatusReason`. This prevents instruction `RedCard` (2) from being mistaken
  for an accepted order lifecycle value, and instruction `Pending` (5) from raising a false
  `OrderRejectedError` (which could prompt a resubmit and a doubled order).
- `save_order` no longer crashes with `ValueError` when the API returns its documented text
  `Status`; `Success` returns and `Failure` raises `OrderRejectedError` with the response reason.
- The client-side rate limiter is now thread-safe.
- A throttled (HTTP 429) retry without a `Retry-After` header now waits at least the one
  second the CIAPI basics guide requires before resending.
- The generator no longer silently falls back to a developer-specific catalog path;
  catalog-consuming commands now require `--catalog-root` or `STONEPY_CATALOG`.
- `get_client_preferences_list` no longer requires a meaningless `string` argument and no
  longer sends the keys filter twice (a breaking signature fix).
- Logging out via `delete_session` now clears the locally stored session token, but only
  when the deleted session is the one currently stored.
- A logon response without a session token (or with an empty or whitespace-only one) now
  raises `AuthenticationError` instead of
  silently storing an empty token; a failed manual `log_on` no longer disables automatic
  session refresh; calling an authenticated endpoint on an unconfigured client raises the
  new `ConfigurationError` instead of a bare `RuntimeError`.
- Credential and token fields on generated models are excluded from `repr()`.
- Docs: fixed the broken testing-guide example (renamed DTO, pre-0.2.2 URL) and the
  watchlist recipe (single `ApiClientAccountWatchlistDTO`, not a list); corrected endpoint
  and resource-group counts; removed the pipx instructions and the stale SECURITY table.

## [0.2.6] - 2026-06-29

### Fixed

- POST endpoints whose request DTO was mislabeled as a query parameter now send it as the JSON
  body. As shipped they serialized the DTO into the query string with no body and the API rejected
  them (HTTP 415 / 400 "content-type not supported"). Affects `order.list_active_orders`,
  `news.list_news_headlines`, and `client_preference.save_client_preference_overridden_settings`
  ([#33](https://github.com/aaronmgn/stonepy/issues/33)).
- `preference.delete_user_preference` now sends its `Preferences` argument as a query parameter
  (the live API rejects the body form), matching the earlier `watchlist.delete_watchlist` fix
  ([#33](https://github.com/aaronmgn/stonepy/issues/33)).
- `price_alert.delete_pa` now returns `bool`. The endpoint returns a bare scalar (`true`) but was
  typed as `ResponseModel`, so it raised a response-parse error even though the delete succeeded
  ([#33](https://github.com/aaronmgn/stonepy/issues/33)).
- `ListNewsHeadlinesRequestDTO` filter fields are now optional, so the request can be constructed
  with a single filter as the endpoint documents (previously all fields were required, making it
  impossible to build) ([#33](https://github.com/aaronmgn/stonepy/issues/33)).

## [0.2.5] - 2026-06-29

### Added

- Support for endpoints whose success body is a bare top-level JSON scalar, via a `ScalarResponse[T]`
  response wrapper (the generated wrapper returns the plain value).

### Fixed

- `user_account.get_charting_enabled` now returns `bool`. The endpoint returns a bare scalar
  (`true`), but it was typed as a `ResponseModel`, so every call raised a response-parse error (a
  return-type change) ([#24](https://github.com/aaronmgn/stonepy/issues/24)).

## [0.2.4] - 2026-06-29

### Added

- First-class support for endpoints whose success body is a bare top-level JSON array, via a
  `ListResponse[Item]` response wrapper. The pipeline validates each element and the wrapper returns
  a plain `list[Item]`.
- Live write round-trips (`save` + read-back + delete) for client preferences and watchlists, now
  that their request models are correct.

### Fixed

- `order.get_orders` and `order.get_order_history` now return `list[EnrichedOrderDTO]` /
  `list[OrderHistoryDTO]`. The API returns a bare JSON array, but they were typed as single objects,
  so every call raised a response-parse error (a return-type change)
  ([#24](https://github.com/aaronmgn/stonepy/issues/24)).
- `client_preference.save_client_preference` and `watchlist.save_watchlist` now succeed. Their
  request bodies wrap a single object (`ClientPreference`, `Watchlist`), but the models typed them
  as lists, so the API rejected every call with HTTP 400
  ([#24](https://github.com/aaronmgn/stonepy/issues/24)).
- `watchlist.delete_watchlist` now sends its `ClientAccountId` / `WatchlistId` as query parameters
  rather than in the body, which the live API requires (a body request 400s)
  ([#24](https://github.com/aaronmgn/stonepy/issues/24)).

## [0.2.3] - 2026-06-28

### Added

- A live contract-test suite (`tests/live/`) that exercises the generated client against the real
  CIAPI demo account, run nightly and on demand by a new `live` GitHub Actions workflow. It is
  skipped unless `STONEX_*` credentials are configured, so the normal test run is unaffected. It
  caught the two response-parsing fixes below and a set of model mismatches tracked in
  [#24](https://github.com/aaronmgn/stonepy/issues/24).

### Fixed

- Response models now parse CIAPI's v2 camelCase JSON. The generated models alias fields with the
  catalog's PascalCase, but the v2 endpoints return camelCase, so with `extra="ignore"` the typed
  client silently dropped the body to all-`None` (for example `watchlist.get_watchlists` and the
  `client_preference` lookups returned empty). `ResponseModel` now matches response keys to field
  aliases case-insensitively, at every nesting level.
- Datetime fields now parse the ISO 8601 values v2 endpoints return (for example
  `2026-06-29T21:05:00Z`), in addition to the v1 WCF `/Date(ms)/` format.
- Correct four response field types the frozen catalog mistypes, verified against the live API, so
  the affected endpoints parse instead of raising: news story ids are strings (Reuters URNs), a
  news payload is a list of stories, a market carries a list of spreads, and market state is a
  single enum. This fixes `news.get_news`, `news.get_news_headlines`,
  `news.get_market_report_headlines`, `market.get_market_information`, and
  `market.list_market_information_search`
  ([#24](https://github.com/aaronmgn/stonepy/issues/24)).
- `user_account.get_client_and_trading_account()` now returns the populated account data. The
  endpoint returns the `AccountResult` fields flat at the top level, but the declared response
  model wrapped them under an `account_result` key, so the typed client always parsed an all-`None`
  result. The method now returns `AccountResult` directly (a return-type change)
  ([#24](https://github.com/aaronmgn/stonepy/issues/24)).

## [0.2.2] - 2026-06-28

### Fixed

- Correct the request path for the v2 endpoints across the `market`, `message`,
  `client_preference`, `order`, `preference`, `watchlist`, `session`, `price_alert`, and
  `user_account` resource groups. The frozen catalog composed each path as `/{target}{uri_template}`,
  doubling the resource segment the v2 `uri_template` already carries (for example
  `/market/v2/market/...`), so every one returned `404`. The generator now emits the documented
  `/v2/...` template for v2 endpoints, served under the existing `/TradingAPI` base. Routes were
  verified against the live CIAPI demo
  ([#15](https://github.com/aaronmgn/stonepy/issues/15),
  [#16](https://github.com/aaronmgn/stonepy/issues/16),
  [#17](https://github.com/aaronmgn/stonepy/issues/17),
  [#18](https://github.com/aaronmgn/stonepy/issues/18),
  [#19](https://github.com/aaronmgn/stonepy/issues/19),
  [#20](https://github.com/aaronmgn/stonepy/issues/20),
  [#21](https://github.com/aaronmgn/stonepy/issues/21)).
- Correct three v2 order/preference routes whose upstream `uri_template` is itself wrong:
  `order.get_active_stop_limit_order` now calls the v1-style
  `/order/{orderId}/activeStopLimitOrder` (the 0.2.0 `/order/v2/...` override also 404s),
  `order.get_open_position` calls `/v2/order/{orderId}/openPosition`, `order.save_order` posts to
  `/v2/order`, and `user_preference.get_user_preference` calls the singular `/v2/Preference`
  (the catalog pluralised it to `/v2/Preferences`)
  ([#18](https://github.com/aaronmgn/stonepy/issues/18),
  [#19](https://github.com/aaronmgn/stonepy/issues/19)).

## [0.2.1] - 2026-06-28

### Fixed

- `session.log_on` now calls the host-root `/v2/session` endpoint that CIAPI actually serves,
  instead of the unreachable `/session/v2/Session` that returned `401` against the documented
  base URL ([#8](https://github.com/aaronmgn/stonepy/issues/8)).
- `user_account.get_client_and_trading_account` now calls the host-root
  `/v2/UserAccount/ClientAndTradingAccount` endpoint instead of the doubled
  `/userAccount/v2/userAccount/ClientAndTradingAccount` path
  ([#9](https://github.com/aaronmgn/stonepy/issues/9)).
- `margin.get_client_account_margin` now calls the v1 `/margin/ClientAccountMargin` endpoint
  (under the `/TradingAPI` base) that CIAPI serves, instead of the `/margin/v2/margin/...` path
  that 404s ([#10](https://github.com/aaronmgn/stonepy/issues/10)).

### Added

- `EndpointSpec.host_rooted`: endpoints flagged host-rooted resolve their path against the server
  host root (scheme and host of `base_url`) rather than the configured base path, so CIAPI's
  `/v2` session and account endpoints can be reached from the same `base_url` as the `/TradingAPI`
  resources.

## [0.2.0] - 2026-06-27

### Added

- Docstrings throughout the public API, sourced from the upstream StoneX catalog: every generated
  model now has a class summary and a per-field description, and every endpoint binding has a
  summary. Field descriptions flow into each model's JSON schema via Pydantic's
  `use_attribute_docstrings`, so the same prose powers the docs site, editor tooltips, and
  `model_json_schema()`.
- Full docstring coverage across the hand-written core (configuration, errors, transport, request
  pipeline, session management, retry and rate-limit policies, codecs, and plugins), including
  `Attributes`/`Raises` sections on the public exception types.
- A `tests/test_self_documentation.py` suite that guards the documentation contract: every model,
  enum, resource group, and exported symbol stays documented, and field descriptions keep reaching
  the JSON schema.
- 56 new resource methods covering the full v2 endpoint surface, exposed on the synchronous and
  asynchronous clients. New resource groups `pm`, `fixedmargin`, `tradingadvisor`,
  `client_preference`, and `order_including_closed`, plus new methods on `order` (simulate,
  update, trade, historical/changed/by-reference queries, trades wall), `market`, `news`,
  `message`, `margin`, `session` (`validate_session`), and `user_account` (social actions,
  multi-user lookups, followers, top holders, trader search). Each method has sync and async
  tests.
- 30 new DTO models for the v2 responses and requests, each with auto-generated reference pages.

### Changed

- Model reference pages now render each model class directly instead of wrapping it in a module
  heading, and the API overview links to the full per-model reference rather than duplicating a
  handful of examples inline.
- Deploy the documentation site with GitHub Actions (`upload-pages-artifact` + `deploy-pages`,
  both on Node 24) instead of the legacy branch builder, eliminating the Node.js 20 deprecation
  warning from Pages builds.
- Regenerated the model and endpoint layer against StoneX catalog `afa936e` (128 endpoints and
  267 data types, up from 72 and 240). Several models gained correct request/response
  classification, resolved type references, and required-ness. Three DTOs adopted their v2 names
  (`GetMarketInformationResponseDTO`, `ApiClientCommunicationUpdateRequestDTO`, and
  `ApiSaveWatchlistRequestDTO` became `…v2`), and `get_order`, `get_open_position`, and
  `get_active_stop_limit_order` now take the v2 `client_account_id` parameter.

### Fixed

- Generator robustness against the larger catalog: alias the lowercase `bool` type to the
  catalog's `boolean`, omit the unused `Param` import from parameter-free endpoint modules,
  annotate unwrappable long generated lines with `# noqa: E501`, and restore the dropped array
  marker on the News headline list fields so they deserialize as lists.
- Correct the `GetActiveStopLimitOrder v2` endpoint path. The upstream StoneX doc page has a typo
  in its URI template (`/v2{orderId}/…`, missing the slash every sibling v2 order endpoint has),
  which would have made the client request a non-existent path; a curated generator override now
  emits the correct `/order/v2/{orderId}/activeStopLimitOrder`.

## [0.1.3] - 2026-06-27

### Added

- Documentation guides: a configuration reference, resilience (timeouts, retries, and rate
  limiting), logging and secret redaction, extensibility and plugins, testing, and a recipes
  cookbook.
- A dedicated installation page covering pip, uv, and pipx, the optional extras, and the typing
  guarantee.
- Auto-generated API reference pages for every DTO and enum in `stonepy.models`.
- Community health files: `CODE_OF_CONDUCT.md`, issue templates, a pull request template, and
  `CODEOWNERS`.

### Changed

- Expanded the README with a feature overview, a project status notice, install options, and a
  support section.
- mkdocstrings now renders inherited members, so the resource-group reference pages list their
  methods.

### Fixed

- Corrected the `list_market_search_paginated` call in the quickstart, and made the README and
  error-handling examples self-contained and runnable.

## [0.1.2] - 2026-06-27

### Changed

- Harden the Dependabot configuration so published runtime version caps are preserved, and fix a
  setup-uv cache race in CI.
- Bump dev tooling (pytest, ruff).

## 0.1.1 - 2026-06-27

### Added

- `Documentation` and `Changelog` project URLs.
- A security policy (`SECURITY.md`) and Dependabot configuration.
- `Operating System :: OS Independent` and `Programming Language :: Python :: 3 :: Only`
  classifiers.

### Changed

- Pin all GitHub Actions to commit SHAs and bump them to Node 24 releases.

### Removed

- The redundant `License :: OSI Approved :: MIT License` classifier, in favour of the PEP 639
  SPDX license expression.

## 0.1.0 - 2026-06-18

### Added

- Initial StoneX CIAPI v2 client release.
- Generated endpoint bindings, DTO models, synchronous and asynchronous clients, retry handling,
  rate-limit handling, and typed resource groups.

[Unreleased]: https://github.com/aaronmgn/stonepy/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/aaronmgn/stonepy/releases/tag/v0.3.0
[0.2.6]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.6
[0.2.5]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.5
[0.2.4]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.4
[0.2.3]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.3
[0.2.2]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.2
[0.2.1]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.1
[0.2.0]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.0
[0.1.3]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.3
[0.1.2]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.2
