# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/aaronmgn/stonepy/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.3
[0.1.2]: https://github.com/aaronmgn/stonepy/releases/tag/v0.1.2
