# Changelog

## 0.1.2 - 2026-06-27

- Harden the Dependabot configuration so published runtime version caps are preserved, and
  fix a setup-uv cache race in CI.
- Bump dev tooling (pytest, ruff).

## 0.1.1 - 2026-06-27

- Drop the redundant `License :: OSI Approved :: MIT License` classifier in favour of the
  PEP 639 SPDX license expression; add `Operating System :: OS Independent` and
  `Programming Language :: Python :: 3 :: Only` classifiers.
- Add `Documentation` and `Changelog` project URLs.
- Pin all GitHub Actions to commit SHAs and bump them to Node 24 releases.
- Add a security policy (`SECURITY.md`) and Dependabot configuration.

## 0.1.0 - 2026-06-18

- Initial StoneX CIAPI v2 client release.
- Includes generated endpoint bindings, DTO models, sync and async clients, retry handling,
  rate-limit handling, and typed resource groups.
