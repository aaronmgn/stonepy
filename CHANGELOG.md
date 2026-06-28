# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/aaronmgn/stonepy/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/aaronmgn/stonepy/releases/tag/v0.2.0
[0.1.3]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.3
[0.1.2]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.2
