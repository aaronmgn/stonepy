# Release bucket: generator safety, client construction, source typing

Branch: `fix/generator-safety`, based on `b066742`. No version change.

## G14: generation safety

Each output is rendered/formatted in a staging directory on the destination filesystem.
The `models`, `endpoints`, `contract`, `client`, and `all` commands use the same transaction
helper; `all` shares one transaction across every pass. Scaffolding is excluded. The client pass
reads staged endpoint bindings. In-place
resource generation copies the existing resource tree so hand-written mixins and neighboring
files survive publication. Stale generated files are removed only when the new output succeeds.

Publication uses filesystem renames, retaining old outputs until all replacements succeed.
Rollback reconciles the actual destination, staged path and backup, verifying the original inode
identity or original absence. It does not rely on flags assigned after a rename. Recovery data
is retained before publication starts and remains retained unless success/restoration is certain.
Tests interrupt immediately after each of five successful renames, including backup and publish
renames of a preserved resource tree, and verify the original hand-written files survive.

Rollback attempts every independent output even if one restore fails. A four-output injection
restores three outputs while retaining the fourth backup; an apparent successful restore with
an unchanged filesystem also retains the originals and reports the incomplete rollback.

Symlink policy: reject symlinked resource roots, directories, files and dangling links before
copying or generating. The error names the path. Rejecting is preferable to dereferencing here:
materialization would silently change the hand-written resource tree and could read outside the
checkout. Copying validated resources creates independent files in staging. Generation assumes
no concurrent filesystem writers; this is not a defense against adversarial symlink replacement
between validation and copying.

Portable filesystems do not provide an atomic transaction spanning these separate directories.
Concurrent readers can observe the brief rename window; a process kill/power loss during
publication may require recovery from retained `.stonepy-generate-*/previous` backups. Stale
workspaces are deliberately not deleted automatically: one may hold the only surviving original.
They are ignored by Git and explicitly excluded from both distributions; release artifact checks
reject them if present. The actual offline build is probed with seeded recovery workspaces.

## C13: lazy construction with a lock

Both generated clients allocate one `threading.Lock` and double-check a missing resource while
holding it. Existing resources return directly without taking the lock. Properties have no await
point, so this covers the thread race while retaining lazy allocation and the public signatures.
Deprecated aliases still warn on every access and return their canonical resource.

Before regeneration, the new first-access test produced eight instances from eight threads on
both original clients. After regeneration, all 50 client/alias tests pass, including eight-thread
first access to every non-deprecated canonical resource on both clients. The earlier eager
proposal remains discarded; this implementation follows the cheaper design requested in review.

Reproduction (checkout-only benchmark, explicitly excluded from distributions):

```sh
export UV_CACHE_DIR=/tmp/stonepy-uv-cache
uv run --offline --no-sync python scripts/benchmark_client_construction.py
```

The script renders the current locked client and its preceding unguarded lazy variant in memory
through the generator. It warms each variant, randomizes variant order in 21 paired batches of
50 constructions per client/variant (1,050 each), and times construction only, excluding close
and destruction. All 19 resource groups remain lazy. No requests are made; benchmarking runs
without concurrent test/build commands. Final measurements on this macOS arm64 checkout:

| Client | Unguarded mean | Locked mean | Locked minus unguarded (95% paired CI) |
| --- | ---: | ---: | ---: |
| Sync | 2.943884 ms | 2.936557 ms | -0.007326 ms (-0.022894 to +0.008242 ms) |
| Async | 1.626218 µs | 1.689814 µs | +0.063596 µs (+0.010986 to +0.116206 µs) |

Sync construction has no measurable regression. Async construction costs an additional 63.6 ns,
about 3.9%, consistent with the reviewed locking proposal. This is the accepted lazy locking
design, not the previously rejected eager allocation.

## Pyright: complete source coverage

The gate is now `pyright src tests`, alongside strict mypy and model stubtest.
All 14 original diagnostics are resolved without ignores or weakened public signatures:

- `_core/config.py`: four `reportPossiblyUnboundVariable` diagnostics. Successful URL parsing
  now follows the explicit `try`/`else` path; invalid URLs retain the same sanitized error
  outside the parser's exception handler.
- `_core/pipeline.py`: seven `reportPossiblyUnboundVariable` and one `reportReturnType`
  diagnostics. Typed decode/validation helpers express the successful return paths and keep
  `ResponseT` tied to the endpoint spec. Sanitized errors still have no original exception
  context. Static assertions retain model, list, scalar and unspecified response types.
- `_core/status.py`: one `reportReturnType` diagnostic. Separate `None` and default-callback
  identity branches return the exact known object with its precise type.
- `_generator/emit_endpoints.py`: one `reportArgumentType` diagnostic. A type guard expresses
  the existing three-value location membership check consistently for both checkers.

Remaining pyright diagnostics: none.

## Verification

All tool runs used `UV_CACHE_DIR=/tmp/stonepy-uv-cache`; `uv run` commands also used
`--offline --no-sync`. Catalog commands used
`STONEPY_CATALOG=/Users/aaron/Projects/stonex_api_docs/Docs/catalog`.

| Round-2 check | Exit code | Evidence |
| --- | ---: | --- |
| `ruff check .` | 0 | All checks passed. |
| `ruff format --check .` | 0 | 1,136 files already formatted. |
| `mypy` | 0 | 818 source files, no issues. |
| `pyright src tests` | 0 | 0 errors, 0 warnings, 0 informations. |
| `python -m mypy.stubtest stonepy.models` | 0 | 288 modules, no issues. |
| `python scripts/consistency_lint.py` with catalog | 0 | No diagnostics. |
| `pytest -q -p no:cacheprovider --cov` | 0 | 2,271 tests: 2,226 passed, 45 skipped; coverage 93.88%. JUnit report written under `/tmp`. |
| `mkdocs build --strict` | 0 | Strict build succeeded. |
| `python -m stonepy._generator all`, pass 1 | 0 | Only generated `client.py` changed from round 1. |
| `python -m stonepy._generator all`, pass 2 | 0 | All 879 output/resource source files match pass 1. |
| Exact filename and byte comparison | 0 | Models, stubs, endpoints, resources and contracts retain their old bytes; no staging leftovers. |
| `uv build --offline` | 0 | Built 0.5.0 wheel and sdist with three seeded recovery workspaces present. |
| Archive exclusion probe and release artifact validation | 0 | Wheel and sdist exclude all three root/nested recovery probes and the benchmark; sdist includes the core response fixture. |
| `twine check dist/*` | 0 | New 0.5.0 artifacts and pre-existing 0.4.1 artifacts pass. |
| Construction benchmark | 0 | Measurements above; 1,050 constructions per variant/client. |

The archive probe used recovery workspaces beneath `src/stonepy`, a resource target and `tests`;
only these three owned probes were removed afterward. No stale recovery data was deleted.
The publication helper's statement/branch coverage is 96%; its unexecuted branches are the
three defensive rejection paths for an unexpected backup or ambiguous destination state.

The core response typing fixture is now registered in the consumer tests (positive and negative
checks under both mypy and pyright) and in the sdist's required-file manifest. The changelog uses
standard consumer-facing headings and contains no reference to these checkout-only task notes.
Nothing was staged, committed, stashed or pushed. The version remains 0.5.0.

## Round 3: final interruption coverage and wording

Added 11 regression cases without changing publication logic:

- A second interrupt immediately before/after either rollback rename inside `_restore`.
  Rollback continues with the other outputs. Every workspace, including those for successfully
  restored neighbors, remains intact when any restoration is unproven.
- A second interrupt from the rollback iterator between outputs, outside the per-output
  exception handler. All workspaces and all originals remain available for recovery.
- Interrupts before, partway through, and immediately after removing a cleanup workspace,
  following either a successful commit or a completed rollback. Destination trees remain
  complete and hand-written files survive, even when cleanup has removed only some workspaces.

The changelog now explicitly names the five transactional commands, excluding `scaffold` from
the claim. Final full-gate exit codes and the two regeneration comparisons are recorded below.

The environment and offline command flags are the same as above.

| Round-3 check | Exit code | Evidence |
| --- | ---: | --- |
| `ruff check .` | 0 | All checks passed. |
| `ruff format --check .` | 0 | 1,136 files already formatted. |
| `mypy` | 0 | 818 source files, no issues. |
| `pyright src tests` | 0 | No diagnostics. |
| `python -m mypy.stubtest stonepy.models` | 0 | 288 modules, no issues. |
| `python scripts/consistency_lint.py` with catalog | 0 | No diagnostics. |
| `pytest -q -p no:cacheprovider --cov` | 0 | 2,237 passed, 45 skipped; coverage 93.87%. JUnit report written under `/tmp`. |
| `mkdocs build --strict` | 0 | Strict build succeeded. |
| `python -m stonepy._generator all`, pass 1 | 0 | All output/resource source files match the pre-run baseline. |
| `python -m stonepy._generator all`, pass 2 | 0 | All output/resource source files match pass 1 and the baseline. |
| Exact filename and byte comparison | 0 | 879 output/resource `.py`/`.pyi` files are byte-identical; no staging leftovers. |
| `uv build --offline` | 0 | Built the 0.5.0 wheel and sdist after the final test changes. |
| `twine check dist/*` | 0 | All artifacts pass. |

No production code changed in this round. Nothing was staged, committed, stashed or pushed;
the version remains 0.5.0.
