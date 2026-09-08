"""Generation and publication failures must preserve the last complete output."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from stonepy._generator import (
    emit_client,
    emit_contract,
    emit_endpoints,
    emit_models,
    publication,
    render,
)
from stonepy._generator.__main__ import main
from stonepy._generator.catalog import load_catalog
from stonepy._generator.publication import OutputTransaction, generation_transaction
from tests.generator._fixtures import resolved_catalog

FIX = Path(__file__).parent / "fixtures"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _old_tree(root: Path) -> tuple[Path, Path]:
    package = root / "src" / "stonepy"
    for name in (
        "src/stonepy/models/old.py",
        "src/stonepy/models/old.pyi",
        "src/stonepy/_endpoints/old.py",
        "tests/contract/test_old.py",
        "src/stonepy/client.py",
        "src/stonepy/resources/__init__.py",
        "src/stonepy/resources/session/__init__.py",
        "src/stonepy/resources/session/_sync/log_on.py",
        "src/stonepy/resources/session/_sync/stale.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# original {name}\n")
    resource = package / "resources" / "session" / "log_on.py"
    resource.write_bytes((FIX / "resources" / "session" / "log_on.py").read_bytes())
    (resource.parent / "notes.txt").write_text("hand-written neighbor\n")
    return package, resource


def _inject_failure(monkeypatch: pytest.MonkeyPatch, failure: str) -> Callable[[], int]:
    calls = 0
    module, name, after = {
        "models-stub": (emit_models, "render_model", 2),
        "models-ruff": (render, "_format_with_ruff", 3),
        "endpoints-format": (emit_endpoints, "format_python", 2),
        "contract-render": (emit_contract, "_render_endpoint_specs", 1),
        "client-unasync": (emit_client, "unasync_files", 1),
        "client-render": (emit_client, "_render_client", 1),
    }[failure]
    original = getattr(module, name)

    def fail(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        result = original(*args, **kwargs)
        if calls == after:
            raise RuntimeError(f"injected {failure}")
        return result

    monkeypatch.setattr(module, name, fail)
    return lambda: calls


@pytest.mark.parametrize("invocation", ["direct", "cli", "all"])
@pytest.mark.parametrize(
    "failure",
    [
        "models-stub",
        "models-ruff",
        "endpoints-format",
        "contract-render",
        "client-unasync",
        "client-render",
    ],
)
def test_failed_generation_preserves_entire_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invocation: str, failure: str
) -> None:
    project = tmp_path / "project"
    package, resource = _old_tree(project)
    catalog_root = resolved_catalog(tmp_path / "catalog")
    catalog = load_catalog(catalog_root)
    before = _snapshot(project)
    calls = _inject_failure(monkeypatch, failure)
    command = failure.split("-")[0]

    with pytest.raises(RuntimeError, match=f"injected {failure}"):
        if invocation == "direct":
            passes = {
                "models": lambda: emit_models.emit_all(catalog, package),
                "endpoints": lambda: emit_endpoints.emit_all(catalog, package),
                "contract": lambda: emit_contract.emit_contract_tests(catalog, project),
                "client": lambda: emit_client.emit_client(package / "resources", package),
            }
            passes[command]()
        else:
            main(
                [
                    "all" if invocation == "all" else command,
                    "--catalog-root",
                    str(catalog_root),
                    "--package-dir",
                    str(package),
                    "--project-root",
                    str(project),
                    "--allow-unresolved",
                    "--allow-unfrozen-catalog",
                    "--skip-override-validation",
                ]
            )

    assert calls() > 0
    assert _snapshot(project) == before
    assert resource.read_bytes() == before[str(resource.relative_to(project))]
    assert not list(project.rglob(".stonepy-generate-*"))


def test_sync_mixin_failure_preserves_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, resource = _old_tree(tmp_path)
    before = _snapshot(tmp_path)
    _inject_failure(monkeypatch, "client-unasync")
    with pytest.raises(RuntimeError, match="injected client-unasync"):
        emit_client._emit_sync_mixins(emit_client._resource_target(resource.parent), {})
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("fail_at", [1, 2, 3, 4, 5])
def test_publication_failure_rolls_back_all_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_at: int
) -> None:
    old = tmp_path / "old"
    old.mkdir()
    (old / "old.py").write_text("old directory\n")
    old_file = tmp_path / "client.py"
    old_file.write_text("old file\n")
    new = tmp_path / "new"
    before = _snapshot(tmp_path)
    replace = Path.replace
    calls = 0

    def fail(self: Path, target: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == fail_at:
            raise OSError("injected publication failure")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fail)
    with (
        pytest.raises(OSError, match="injected publication failure"),
        generation_transaction() as transaction,
    ):
        (transaction.stage(old) / "new.py").write_text("new directory\n")
        (transaction.stage(new) / "new.py").write_text("new output\n")
        transaction.stage(old_file, directory=False).write_text("new client\n")
    assert _snapshot(tmp_path) == before
    assert not new.exists()
    assert not list(tmp_path.glob(".stonepy-generate-*"))


def test_success_removes_stale_generated_files_and_preserves_resource_sources(
    tmp_path: Path,
) -> None:
    package, resource = _old_tree(tmp_path)
    source = resource.read_bytes()
    emit_client.emit_client(package / "resources", package)
    assert resource.read_bytes() == source
    assert (resource.parent / "notes.txt").read_text() == "hand-written neighbor\n"
    assert not (resource.parent / "_sync" / "stale.py").exists()
    assert "class StoneXClient" in (package / "client.py").read_text()


def test_overlapping_outputs_are_rejected_before_publication(tmp_path: Path) -> None:
    before = _snapshot(tmp_path)
    with (
        pytest.raises(ValueError, match="overlapping generator output"),
        generation_transaction() as transaction,
    ):
        transaction.stage(tmp_path / "models")
        transaction.stage(tmp_path / "models" / "child")
    assert _snapshot(tmp_path) == before


def test_all_rolls_back_earlier_passes_when_client_publication_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    package, _ = _old_tree(project)
    catalog_root = resolved_catalog(tmp_path / "catalog")
    before = _snapshot(project)
    replace = Path.replace
    failed = False

    def fail(self: Path, target: Path) -> Path:
        nonlocal failed
        if target == package / "client.py" and not failed:
            failed = True
            # Earlier passes were published, so this exercises actual cross-pass rollback.
            assert not (package / "models" / "old.py").exists()
            assert not (project / "tests" / "contract" / "test_old.py").exists()
            raise OSError("injected client publication failure")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="injected client publication failure"):
        main(
            [
                "all",
                "--catalog-root",
                str(catalog_root),
                "--package-dir",
                str(package),
                "--project-root",
                str(project),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
                "--skip-override-validation",
            ]
        )
    assert failed
    assert _snapshot(project) == before


def test_failed_rollback_retains_originals_for_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "models"
    destination.mkdir()
    (destination / "old.py").write_text("original\n")
    replace = Path.replace

    def fail(self: Path, target: Path) -> Path:
        if target == destination:
            raise OSError("filesystem unavailable")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fail)
    with (
        pytest.raises(OSError, match="filesystem unavailable"),
        generation_transaction() as transaction,
    ):
        (transaction.stage(destination) / "new.py").write_text("new\n")
    backups = list(tmp_path.glob(".stonepy-generate-*/previous/old.py"))
    assert len(backups) == 1
    assert backups[0].read_text() == "original\n"


@pytest.mark.parametrize("fail_at", range(1, 6))
def test_interrupt_after_completed_rename_restores_original_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_at: int
) -> None:
    package, resource = _old_tree(tmp_path)
    before = _snapshot(tmp_path)
    replace = Path.replace
    calls = 0

    def interrupt(self: Path, target: Path) -> Path:
        nonlocal calls
        calls += 1
        result = replace(self, target)
        if calls == fail_at:
            # The syscall completed, but no Python bookkeeping after it has run.
            raise KeyboardInterrupt("after rename")
        return result

    monkeypatch.setattr(Path, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt, match="after rename"), generation_transaction() as tx:
        staged = tx.stage(package / "resources", preserve=True)
        (staged / "session" / "log_on.py").write_text("new resource\n")
        tx.stage(package / "client.py", directory=False).write_text("new client\n")
        (tx.stage(package / "new") / "new.py").write_text("new output\n")
    assert _snapshot(tmp_path) == before
    assert resource.read_bytes() == before[str(resource.relative_to(tmp_path))]
    assert not (package / "new").exists()
    assert not list(tmp_path.rglob(".stonepy-generate-*"))


def _stage_preserved_outputs(root: Path, tx: OutputTransaction) -> dict[Path, Path]:
    workspaces: dict[Path, Path] = {}
    for name in ("first", "second", "third"):
        destination = root / name
        destination.mkdir()
        (destination / "hand_written.py").write_text(f"# original {name}\n")
        (destination / "generated.py").write_text("# old\n")
        staged = tx.stage(destination, preserve=True)
        (staged / "generated.py").write_text("# new\n")
        workspaces[destination] = staged.parent
    return workspaces


def _assert_all_workspaces_retained(root: Path, workspaces: dict[Path, Path]) -> None:
    assert set(root.glob(".stonepy-generate-*")) == set(workspaces.values())
    for destination, workspace in workspaces.items():
        original = {
            "hand_written.py": f"# original {destination.name}\n".encode(),
            "generated.py": b"# old\n",
        }
        assert any(_snapshot(path) == original for path in (destination, workspace / "previous")), (
            f"original files missing for {destination}"
        )


@pytest.mark.parametrize("restore_step", ["move_new", "restore_old"])
@pytest.mark.parametrize("after_rename", [False, True], ids=["before", "after"])
def test_second_interrupt_inside_restore_retains_every_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_step: str, after_rename: bool
) -> None:
    replace = Path.replace
    interrupts: list[str] = []
    workspaces: dict[Path, Path] = {}

    def interrupt(self: Path, target: Path) -> Path:
        if self.name == "new" and target == tmp_path / "third":
            replace(self, target)
            interrupts.append("publication")
            raise KeyboardInterrupt("publication interrupt")
        second = tmp_path / "second"
        source, destination = (
            (second, workspaces[second] / "new")
            if restore_step == "move_new"
            else (workspaces[second] / "previous", second)
        )
        if self == source and target == destination:
            if after_rename:
                replace(self, target)
            interrupts.append("restore")
            raise KeyboardInterrupt("restore interrupt")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt)
    with (
        pytest.raises(KeyboardInterrupt, match="publication interrupt") as caught,
        generation_transaction() as tx,
    ):
        workspaces = _stage_preserved_outputs(tmp_path, tx)
    assert interrupts == ["publication", "restore"]
    assert "restore interrupt" in " ".join(caught.value.__notes__)
    _assert_all_workspaces_retained(tmp_path, workspaces)
    # Successfully restored neighbors retain their entire workspaces too, and rollback
    # continues past the second interrupt to restore the first output.
    for name in ("first", "third"):
        destination = tmp_path / name
        assert (destination / "generated.py").read_bytes() == b"# old\n"
        assert (workspaces[destination] / "new" / "generated.py").read_bytes() == b"# new\n"


def test_second_interrupt_between_rollback_iterations_retains_every_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replace = Path.replace
    interrupts: list[str] = []
    workspaces: dict[Path, Path] = {}

    def interrupt_publication(self: Path, target: Path) -> Path:
        result = replace(self, target)
        if self.name == "new" and target == tmp_path / "third":
            interrupts.append("publication")
            raise KeyboardInterrupt("publication interrupt")
        return result

    def interrupt_iteration(outputs: list[publication._Output]) -> Iterator[publication._Output]:
        assert len(outputs) == 3
        yield outputs[-1]
        # Raise from FOR_ITER, outside the per-output try/except in _rollback.
        interrupts.append("between iterations")
        raise KeyboardInterrupt("between rollback iterations")

    monkeypatch.setattr(Path, "replace", interrupt_publication)
    monkeypatch.setattr(publication, "reversed", interrupt_iteration, raising=False)
    with (
        pytest.raises(KeyboardInterrupt, match="between rollback iterations"),
        generation_transaction() as tx,
    ):
        workspaces = _stage_preserved_outputs(tmp_path, tx)
    assert interrupts == ["publication", "between iterations"]
    _assert_all_workspaces_retained(tmp_path, workspaces)
    assert (tmp_path / "third" / "generated.py").read_bytes() == b"# old\n"
    assert (workspaces[tmp_path / "third"] / "new" / "generated.py").read_bytes() == b"# new\n"
    for name in ("first", "second"):
        assert (tmp_path / name / "generated.py").read_bytes() == b"# new\n"
        assert (
            workspaces[tmp_path / name] / "previous" / "generated.py"
        ).read_bytes() == b"# old\n"


@pytest.mark.parametrize("rollback", [False, True], ids=["committed", "rolled-back"])
@pytest.mark.parametrize("cleanup_step", ["before", "partial", "after"])
def test_cleanup_interrupt_preserves_complete_destination_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rollback: bool, cleanup_step: str
) -> None:
    replace = Path.replace
    rmtree = shutil.rmtree
    interrupts: list[str] = []
    workspaces: dict[Path, Path] = {}

    def interrupt_publication(self: Path, target: Path) -> Path:
        result = replace(self, target)
        if rollback and self.name == "new" and target == tmp_path / "third":
            interrupts.append("publication")
            raise KeyboardInterrupt("publication interrupt")
        return result

    def interrupt_cleanup(path: Path) -> None:
        if path == workspaces[tmp_path / "second"]:
            if cleanup_step == "partial":
                disposable = "new" if rollback else "previous"
                (path / disposable / "generated.py").unlink()
            elif cleanup_step == "after":
                rmtree(path)
            interrupts.append("cleanup")
            raise KeyboardInterrupt("cleanup interrupt")
        rmtree(path)

    monkeypatch.setattr(Path, "replace", interrupt_publication)
    with (
        pytest.raises(KeyboardInterrupt, match="cleanup interrupt"),
        monkeypatch.context() as patch,
        generation_transaction() as tx,
    ):
        workspaces = _stage_preserved_outputs(tmp_path, tx)
        patch.setattr(shutil, "rmtree", interrupt_cleanup)
    assert interrupts == (["publication", "cleanup"] if rollback else ["cleanup"])
    for destination in workspaces:
        assert _snapshot(destination) == {
            "hand_written.py": f"# original {destination.name}\n".encode(),
            "generated.py": b"# old\n" if rollback else b"# new\n",
        }
    assert not workspaces[tmp_path / "first"].exists()
    assert workspaces[tmp_path / "second"].exists() is (cleanup_step != "after")
    assert workspaces[tmp_path / "third"].is_dir()


def test_rollback_continues_after_one_restore_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destinations = [tmp_path / name for name in ("first", "second", "third", "fourth")]
    for destination in destinations:
        destination.mkdir()
        (destination / "original.py").write_text(destination.name)
    replace = Path.replace

    def fail(self: Path, target: Path) -> Path:
        if target == destinations[-1] and self.name == "new":
            raise OSError("publication failure")
        if target == destinations[-2] and self.name == "previous":
            raise OSError("restore failure")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fail)
    with (
        pytest.raises(OSError, match="publication failure") as caught,
        generation_transaction() as tx,
    ):
        for destination in destinations:
            (tx.stage(destination) / "new.py").write_text("new\n")
    for destination in (destinations[0], destinations[1], destinations[3]):
        assert (destination / "original.py").read_text() == destination.name
    backups = list(tmp_path.glob(".stonepy-generate-*/previous/original.py"))
    assert [p.read_text() for p in backups] == ["third"]
    assert "recovery workspaces retained" in " ".join(caught.value.__notes__)


def test_uncertain_restoration_retains_backups_without_a_rename_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "models"
    destination.mkdir()
    (destination / "original.py").write_text("original\n")
    replace = Path.replace

    def fail(self: Path, target: Path) -> Path:
        if target == destination and self.name == "new":
            raise OSError("publication failure")
        if self.name == "previous":
            return target  # Simulate a restore that reports success without restoring anything.
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fail)
    with (
        pytest.raises(OSError, match="publication failure") as caught,
        generation_transaction() as tx,
    ):
        (tx.stage(destination) / "new.py").write_text("new\n")
    backups = list(tmp_path.glob(".stonepy-generate-*/previous/original.py"))
    assert len(backups) == 1 and backups[0].read_text() == "original\n"
    assert "original output not restored" in " ".join(caught.value.__notes__)


@pytest.mark.parametrize(
    "linked", [".", "session", "session/__init__.py", "session/_sync", "session/log_on.py"]
)
def test_client_rejects_symlinks_before_staging(tmp_path: Path, linked: str) -> None:
    project = tmp_path / "project"
    package, _ = _old_tree(project)
    link = package / "resources" / linked
    target = tmp_path / "external"
    link.rename(target)
    link.symlink_to(target, target_is_directory=target.is_dir())
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="must not be symlinks") as caught:
        emit_client.emit_client(package / "resources", package)
    assert str(link) in str(caught.value)
    assert _snapshot(tmp_path) == before
    assert not list(tmp_path.rglob(".stonepy-generate-*"))


@pytest.mark.parametrize("preserve", [False, True])
def test_stage_rejects_linked_destination(tmp_path: Path, preserve: bool) -> None:
    target = tmp_path / "external"
    target.mkdir()
    (target / "original.py").write_text("original\n")
    link = tmp_path / "models"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match=str(link)), generation_transaction() as tx:
        tx.stage(link, preserve=preserve)
    assert (target / "original.py").read_text() == "original\n"
    assert not list(tmp_path.glob(".stonepy-generate-*"))


def test_preserved_tree_rejects_dangling_symlinks(tmp_path: Path) -> None:
    destination = tmp_path / "resources"
    destination.mkdir()
    link = destination / "dangling.py"
    link.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match=str(link)), generation_transaction() as tx:
        tx.stage(destination, preserve=True)
    assert link.is_symlink()
    assert not list(tmp_path.glob(".stonepy-generate-*"))


def test_sync_generation_rejects_linked_output(tmp_path: Path) -> None:
    _, resource = _old_tree(tmp_path / "project")
    link = resource.parent / "_sync"
    target = tmp_path / "external"
    shutil.move(link, target)
    link.symlink_to(target, target_is_directory=True)
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match=str(link)):
        emit_client._emit_sync_mixins(emit_client._resource_target(resource.parent), {})
    assert _snapshot(tmp_path) == before
