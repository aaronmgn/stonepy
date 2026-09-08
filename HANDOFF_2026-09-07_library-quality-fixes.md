# Handoff: fix the 2026-09-07 stonepy library-quality audit findings

You are taking over `stonepy` (`/Users/aaron/Projects/stonepy`, GitHub `aaronmgn/stonepy`), a typed Python client for the StoneX CIAPI v2 trading API. A completed two-agent audit (Codex gpt-6-astra + Claude) of v0.4.1 at `d928023` produced a signed-off backlog. Your job is to work that backlog to completion and ship it as release 0.5.0.

## Read first (in this order)

1. `AUDIT_2026-09-07_stonepy-library-quality_FINAL.md` in the repo root (gitignored copy; canonical at `/Users/aaron/.claude/plugin-data/codex/workflows/2026-09-07_stonepy-library-quality/`). It holds the ranked findings, the full claim table keyed by row IDs (A12, S03, R32, ...), evidence as `path:line`, and the agreed correction for every row. Row IDs below refer to that table. Treat the table's corrections as the spec; where a correction says "design option", decide and record why.
2. `AGENTS.md` and `CONTRIBUTING.md` (repo conventions, generated-file rules, the exact gate commands).
3. `AUDIT_2026-09-07_stonepy-library-quality_CLAUDE.md` for the probes that reproduced each blocking finding; reuse them as regression tests.

## Working rules (non-negotiable)

- **Codex implements, Claude reviews. Never the same agent for both.** Use the `codex:codex` skill's plan-and-build loop (`references/dual-agent-workflow.md`). Every workspace edit, including one-liners, config, docs, and fixes found during testing, goes through the executor session and gets an independent review. If you edit anything yourself, freeze it and get it reviewed before it ships.
- Session settings are recorded in `.codex-session.json` (gpt-6-astra / xhigh / Standard / High). Pass `--model --effort --service-tier` explicitly on every dispatch. On macOS use `nohup ... & disown`, not `setsid`. Codex's sandbox cannot reach `~/.cache/uv`: have it `export UV_CACHE_DIR=/tmp/stonepy-uv-cache` before any `uv run`. Codex must not `git add`/`commit`; the host commits.
- **Generated files are never hand-edited**: `src/stonepy/models/**`, `src/stonepy/_endpoints/**`, `src/stonepy/client.py`, `src/stonepy/resources/*/__init__.py`, `src/stonepy/resources/*/_sync/**`, `tests/contract/**`. Change the generator or its override tables, then regenerate. Models/endpoints/contract passes need the private catalog: `STONEPY_CATALOG=/path/to/stonex_api_docs/Docs/catalog uv run python -m stonepy._generator all`. The `client` pass needs no catalog. Regeneration must stay byte-stable (`git status` clean after a second run).
- After any version bump run `uv sync --extra dev --reinstall-package stonepy`, otherwise four User-Agent tests fail on stale editable metadata.
- Gates before every stage is accepted (from `AGENTS.md`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run python scripts/consistency_lint.py`, `uv run pytest --cov=... --cov-fail-under=90` (use the flags in AGENTS.md until stage 0 moves them into pyproject), `uv build`, `uv run twine check dist/*`, `uv run mkdocs build --strict`. Run the broad gate once per stage on the host; Codex runs only the narrow checks for its diff.
- Work on a branch off `main`, one PR per stage (Conventional Commits, no attribution trailers). `main` is protected; squash-merge is the repo convention. Do not commit `AUDIT_*`, `PLAN_*`, `REVIEW_*`, or `.codex-session.json` (already gitignored).
- **Verification split.** Codex can run ruff, mypy, pytest, `uv build`. Codex cannot: reach the network, run live tests, call `gh`, change GitHub settings, push, or release. The host does those and relays results.

## Settled decisions. Do not re-litigate.

- The one-time auth-refresh replay on HTTP 401 / ErrorCode 4011 applies to every endpoint including non-idempotent order calls (decided 2026-08-29). Add the missing test (T10); do not change the behaviour.
- Manual `log_on()` installs a replay refresh callable (CR-M1 was a false finding). Client-preference save sends a single object, not a list (MD-m8 was false).
- One resource file per method with a `_*Mixin` class (Z02) is a deliberate authoring contract. Do not consolidate.
- `clientpreference` and `client_preference` are different APIs (different routes, request types, idempotency). Alias names for consistency (N13); do not merge them.
- Explicit `Retry-After` is authoritative and uncapped; computed backoff caps at 30 s; 1 s throttle floor is unconditional.

## Stages, scope fences, and acceptance criteria

Finish each stage fully, get it reviewed, gate it, merge it, then open the next. Every stage adds CHANGELOG `[Unreleased]` entries under Keep a Changelog headings, marking `**BREAKING:**` where public behaviour changes.

### Stage 0. Hygiene and pure deletions (one PR)
Rows: N03, N06, N08, N10, N11, N12, Z01, Z03, Z04, Z08, Z10, N07, P04.
- `.gitignore` gains `.uv-cache/` and `.superpowers/`; sdist root includes anchored (`/LICENSE` ...). Local `uv build` sdist contains no `.uv-cache` entries.
- Delete the `py.typed` force-include and its test line; the built wheel still contains exactly one `stonepy/py.typed`.
- Coverage scope moves into `[tool.coverage.run] source` (the five paths) and `fail_under` into `[tool.coverage.report]`; CI, CONTRIBUTING.md, AGENTS.md all run plain `uv run pytest --cov`. Coverage number unchanged (about 94%).
- `ci.yml` provisions the interpreter once.
- `_is_rate_limited` loses its dead parameter; HTTP-date `Retry-After` uses an injectable UTC source with a `FakeClock`-driven test.
- `BucketedSlidingWindowLimiter` deleted; `CallContext.limiter` is a `SlidingWindowLimiter`; `rate_limit_bucket` may stay on `EndpointSpec` as an ignored label this release. Behaviour identical (existing limiter tests pass unchanged).
- `emit_client.py` emits one module-level frozenset of built-in resource names used by both clients.
- `ClientConfig.from_env` builds kwargs from env plus non-`None` overrides and lets the dataclass supply defaults; the documented `status_decoder=None` special case is preserved by test.
- `PassthroughResponseModel` removed from `_core/models.py`; generator fails loudly on an unresolved response type instead of emitting a passthrough alias.
- One `SECRET_KEYS` frozenset in `_core/logging.py` (union of the four sets plus the generator's credential names) imported by errors, pipeline, transport, render; a test asserts the old keys are still redacted in every context.
- `ClientConfig` secret fields use `dataclasses.field(repr=False)`; `safe_repr` for dataclasses deleted (keep the mapping helper if `Request.__repr__` still needs it).
- `plugins.py` fallback `0.1.0` removed (fully resolved in stage 3).
- README quickstart prints a real call result, not the resource object.

### Stage 1. Blocking: secret hygiene in error text (one PR)
Rows: S03, S04, S05, S07, S12, S14, T06.
- `StoneXModel.model_config` sets `hide_input_in_errors=True`. `ListResponse`/`ScalarResponse` (RootModel, not StoneXModel) get the same protection.
- `ResponseParseError` no longer copies `str(ValidationError)` verbatim; message carries error locations and types only. `StoneXAPIError` fallback `error_message` is a generic string (reason phrase plus body length); the body stays only in `raw_body`.
- Tests: construct `ApiLogOnRequestDTO` with a missing field and assert the app key and password appear nowhere in `str(exc)`, `repr(exc)`, or `traceback.format_exception(...)` including `__cause__`; same for a logon response whose `Session` field fails validation; same for a non-JSON error body. Both sync and async clients.
- `base_url` with userinfo is rejected at construction (fold into stage 3's validation if simpler, but the test lands here).

### Stage 2. Blocking: strict nested request DTOs (one PR, needs catalog)
Row: A12 (correction as agreed: request-side variants of shared DTOs).
- Generator discovers every DTO reachable from a request root, emits a request-side variant with `extra="forbid"` and recursively rewritten annotations, and points request roots and request-typed endpoint params at the variants. Response classes, aliases, defaults, and tolerance are untouched. Already-constructed tolerant instances passed into strict positions are rejected with a clear `ValidationError`.
- Regenerate models/endpoints/contract; drift check byte-stable; contract tests updated by the generator, not by hand.
- Regression test: `NewTradeOrderRequestDTO(..., IfDone=[{"Stpo": {...}}])` raises; the equivalent response payload with an unknown key still parses.
- Document the request/response class split in `docs/api/models.md` and CHANGELOG (BREAKING: request DTO class names may change; state the mapping).

### Stage 3. Money-moving and runtime correctness (one PR)
Rows: R32, R33, R34, C10, A09, A10, A19, G16, Y04, C05, C06, C13, T07, T10, Y07, Y08, A21, C04.
- `parse_response`/`_parse_success` fail closed with `OrderStatusUnknownError` when an `INSTRUCTION`/`ORDER`/`EXECUTION_TEXT` acknowledgement has an empty body, a `null` status, a boolean status, or a non-integer/non-string status, checked on the raw decoded payload before `model_validate`.
- `SessionManager`/`AsyncSessionManager` expose one locked snapshot returning `(generation, auth_headers)`; the pipeline reads both from it. Test: Codex's C10 interleaving (peer refresh between the reads, then 401) now triggers a refresh and exactly one logon.
- `ClientConfig.__post_init__` validates: non-empty `base_url` with scheme and host and no userinfo; finite positive timeouts, `max_connections`, `rate_limit_max`, `rate_limit_window_seconds`, `proactive_refresh_seconds`; `max_retries >= 0`; finite `retry_budget_seconds >= 0`. Raises `ValueError`/`TypeError` (document that these are builtin exceptions, as README already says).
- `status_decoder` receives the domain: introduce a keyword-capable signature `(status, status_reason, *, domain)` with a compatibility shim for two-argument callables (inspect signature once at config time), and document it.
- The three endpoints bound to the bare `ResponseModel` get an explicit documented result (a generated `NoContentResponse`-style model or the correct catalog DTO); decide per endpoint from the catalog and record it in the override table.
- `AsyncTransport` tracks closed state and rejects `asend` after `aclose`.
- Manual `log_on` snapshots a validated copy of the request for the replay closure and commits token + callable together.
- Tests: SaveOrder and Trade with missing/null/`true`/fractional status, sync and async; non-idempotent POST gets exactly one 401 replay with identical body bytes; `ainvoke` no longer falls back to blocking `invoke` (raise `TypeError`); async paths require an `AsyncClock`-capable clock; pickle round-trip of every public exception.

### Stage 4. Single-sourced version (one PR)
Rows: N04, N14, P04, P03.
- `src/stonepy/_version.py` holds `__version__`; `__init__` re-exports; `[tool.hatch.version] path` points at it; `config.py` and `plugins.py` import it; both `_FALLBACK_*` constants and both `importlib.metadata` lookups are deleted; `tests/test_project_metadata.py` updated; docs prose no longer hard-codes the current version except the illustrative `pip install stonepy==X` pin.

### Stage 5. CI and release gating (one PR plus host-side settings)
Rows: I03, I17, I05, I06, I09, I04, I10, I24, P15, P18, T16, T17, T03, I12, I13, I21, N02, I08.
- `ci.yml`: `uv sync --locked`; pin the uv version input on `setup-uv`; run `python -m stonepy._generator client` and fail on any diff; add a `lowest-direct` resolution job (`uv sync --resolution lowest-direct`) on the oldest and newest Python; add a job that installs the built wheel into a clean venv outside the checkout and runs an import plus a `respx`-mocked client call; enable branch coverage (`[tool.coverage.run] branch = true`), adjusting `fail_under` only if it drops below 90 and record why.
- `release.yml`: triggered by tag but gated on the `ci` workflow succeeding for the same commit (`workflow_run` or a reusable workflow), verifies the normalized tag equals `stonepy.__version__` and the built artifact version, builds once, uploads as an artifact, publishes that artifact; `contents: read` explicit at job level; `twine` from the locked dev environment.
- `docs.yml`: `mike deploy` runs a strict build; a manually supplied version must match the checked-out tag.
- Live tests: require `STONEX_LIVE=1` in addition to credentials; refuse to run unless `STONEX_BASE_URL` matches an allowlisted demo host; `live.yml` sets the flag.
- Pre-commit hooks invoke the locked tools (`uv run ...`) and CONTRIBUTING says the hooks are a fast subset.
- Host (not Codex): update branch protection to require `test (3.11)` through `test (3.14)`, `docs`, and the new jobs (or one aggregate job); enable enforce-admins if the owner agrees; confirm the PyPI `pypi` environment has required reviewers or tag protection. Record what was set in the PR body.

### Stage 6. Nightly live workflow (host-driven, needs credentials)
Row: N01, T19.
- Promote `test_get_pa_query_binding_candidate`: create a price alert, query GetPA with non-null `alertId` and `ClientAccountId` on the query binding, assert the filter is honoured, then run the same against the current body binding and record which one the demo API honours. Only then change `GET_PA_SPEC` via the generator's param-location override, regenerate, delete the xfail. Every remaining strict xfail gains a `raises=` restriction.
- Acceptance: the `live` workflow is green on two consecutive nightly runs.

### Stage 7. Public API polish before 1.0 (one PR)
Rows: A15/N13, A16, A17, A18, A05, Z05, Z06, Z07, A04, N05, N09 (optional).
- Snake_case aliases `client_application`, `fixed_margin`, `trading_advisor` with `DeprecationWarning` on the old names (tests must pass with `filterwarnings=error`, so assert the warning explicitly); `order.get_order_including_closed` alias.
- Plugin subsystem: ask the owner whether any downstream plugin exists. If none: delete entry-point discovery, `allow_overrides`, `requires_stonepy`, `ABI_VERSION`, and `client.plugin()` (BREAKING, documented), and replace `docs/guide/extensibility.md` with a short "subclass `BaseResource` and pass a `CallContext`" section that imports from a new public `stonepy.extensions` module re-exporting `BaseResource`, `CallContext`, `EndpointSpec`, `Param`, `AuthPolicy`, `StatusDomain`. If a plugin exists: keep discovery, move the ABI to that public module, enforce `ABI_VERSION`, use `packaging.specifiers` (add `packaging` as a runtime dependency) instead of the hand-rolled parser, and give `plugin()` a typed overload.
- `from_env` gets a `TypedDict` + `Unpack` signature; add a pyright run over `tests/` to CI as a non-blocking job first.
- Decide on shipping `_generator` in the wheel (N05); if excluding, move it to a top-level `tools/` package and repoint `scripts/consistency_lint.py`, tests, and docs.

### Stage 8. Docs, changelog, release 0.5.0
Rows: D02, D04, D05, D06, D10, P07, P11, G07, G08, G10, G13, G14, T02, T14, T18, T21, T22, I13, D01.
- Apply the minor docs corrections from the table; `gen_ref_pages.py` categorises `*ResponseDTOv2`/`*RequestDTOv2`; the generator appends the status-domain note to `ApiTradeOrderResponseDTO.Status`; README qualifies "128 endpoints" as frozen-catalog coverage.
- Generator: pass the absolute config path to both Ruff subprocesses; `consistency_lint` calls `assert_override_consumption` and errors on a missing resources dir; `--allow-unfrozen-catalog` no longer silently skips override validation.
- Tests: contract round-trip compares the first dump with expected values; endpoint contract tests assert the exact response model; session concurrency tests use bounded joins.
- Release: bump to 0.5.0 (all BREAKING rows collected), tag, verify PyPI attestation and Pages, GitHub Release from the CHANGELOG section. Follow the recipe in the project memory note `audit-fix-run-2026-08` (HTTPS tag push via `gh auth git-credential`).

## Reporting

At the end of each stage report: rows closed (by ID), rows deferred with reason, gate results with counts, the Codex executor and reviewer session IDs, and the PR number. At the end of the whole run, update the FINAL document's rows with a `status` note (fixed in PR #n / deferred: why) and write a project memory note. Anything you cannot settle between the two agents goes to the owner as an "Unresolved" block, not a silent default.
