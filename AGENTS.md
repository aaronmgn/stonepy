# Agent Guide

Guidance for AI agents and contributors implementing StoneX resource methods in `stonepy`.
For general setup and the checks CI enforces, see [CONTRIBUTING.md](CONTRIBUTING.md).

## File Ownership

Work on one resource target at a time. A resource implementation owns exactly one file:
`src/stonepy/resources/<target>/<method>.py`. Do not edit generated endpoint modules,
generated models, generated `_sync` files, or generated resource `__init__.py` files by hand.

## Resource Shape

Each resource file must define exactly one private mixin class named `_*Mixin` that subclasses
`BaseResource`. The mixin must expose exactly one public method, and that method name must match
the file stem in snake_case.

```python
class _LogOnMixin(BaseResource):
    async def log_on(self, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:
        return await _ep.alog_on(self._ctx, request)
```

Run `uv run python scripts/consistency_lint.py` before committing resource changes. The
scaffold command refuses to overwrite existing resource/test files unless `--force` is used.

## Binding Overrides

Prefer generated endpoint bindings from `stonepy._endpoints`. If a catalog binding is wrong,
add the smallest local workaround in the resource method and leave a short comment explaining
the catalog mismatch. Do not patch generated files directly; fix the generator or catalog when
the mismatch is systematic.

## Blocked Work

If a resource cannot be implemented because the catalog is ambiguous, the response model is
unresolved, or the API contract is unknown, stop and record the blocker in the task notes with
the endpoint name, target, catalog fields involved, and the smallest reproduction.

## Naming

Resource target directories use generator target names such as `session`, `order`, and
`user_account`. Resource files and public methods use snake_case endpoint names. Mixin class
names use private PascalCase form, for example `_ChangePasswordMixin`.

## Before You Finish

Run the same checks CI enforces:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/consistency_lint.py
uv run pytest
```

The upstream [StoneX CIAPI v2 documentation](https://docs.labs.gaincapital.com/) is the
authoritative contract for endpoint semantics, request bodies, and response bodies.
