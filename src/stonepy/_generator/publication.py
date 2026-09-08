"""Stage complete generator outputs before publishing them on the same filesystem.

Renames are atomic per path, but a portable filesystem cannot atomically replace multiple
directories. Keep the old paths until every rename succeeds and roll back on exceptions.
Concurrent readers may observe the short publication window; process termination or a second
filesystem failure during rollback requires recovery from the retained backups.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _Output:
    destination: Path
    workspace: Path
    original: tuple[int, int] | None

    @property
    def staged(self) -> Path:
        return self.workspace / "new"

    @property
    def backup(self) -> Path:
        return self.workspace / "previous"


class OutputTransaction:
    """A batch of disjoint generated files/directories, published only after validation."""

    def __init__(self) -> None:
        self._outputs: dict[Path, _Output] = {}
        self._keep_backups = False

    def stage(self, destination: Path, *, directory: bool = True, preserve: bool = False) -> Path:
        """Allocate a sibling staging path, optionally copying hand-written neighbors."""
        reject_symlinks(destination, recursive=preserve)
        destination = destination.resolve()
        if any(
            destination == path or destination in path.parents or path in destination.parents
            for path in self._outputs
        ):
            raise ValueError(f"overlapping generator output: {destination}")
        original = _identity(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix=".stonepy-generate-", dir=destination.parent))
        output = _Output(destination, workspace, original)
        self._outputs[destination] = output
        if preserve and destination.exists():
            shutil.copytree(destination, output.staged)
        elif directory:
            output.staged.mkdir()
        return output.staged

    def path(self, destination: Path) -> Path:
        """Read an earlier pass's staged output when composing a batch."""
        output = self._outputs.get(destination.resolve())
        return output.staged if output is not None else destination

    def publish(self) -> None:
        """Replace complete outputs, restoring all old paths if any rename fails."""
        # Set this BEFORE any rename. Interrupts can land between a successful syscall and
        # its next Python statement, so cleanup must default to retaining recovery data.
        self._keep_backups = True
        try:
            for output in self._outputs.values():
                if output.destination.exists():
                    output.destination.replace(output.backup)
                output.staged.replace(output.destination)
        except BaseException as error:
            failures = self._rollback()
            if failures:
                locations = ", ".join(str(output.workspace) for output in self._outputs.values())
                error.add_note(f"Rollback incomplete; recovery workspaces retained: {locations}")
                for failure in failures:
                    error.add_note(f"Rollback: {failure!r}")
            raise
        self._keep_backups = False

    def _rollback(self) -> list[BaseException]:
        failures: list[BaseException] = []
        for output in reversed(list(self._outputs.values())):
            try:
                _restore(output)
            except BaseException as error:
                # Continue restoring independent outputs even if this filesystem path fails.
                failures.append(error)
        # _restore verifies original inode identity (or absence), not just successful calls.
        # Keep everything if even one path cannot be proven restored.
        self._keep_backups = bool(failures)
        return failures

    def cleanup(self) -> None:
        """Remove staging and backups after success or a completed rollback."""
        if not self._keep_backups:
            for output in self._outputs.values():
                shutil.rmtree(output.workspace)


def _identity(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.lstat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino


def _restore(output: _Output) -> None:
    """Reconcile actual rename state, including syscalls interrupted before returning."""
    backup = _identity(output.backup)
    destination = _identity(output.destination)
    if backup is not None:
        if backup != output.original:
            raise OSError(f"unexpected backup at {output.backup}")
        if destination is not None:
            if _identity(output.staged) is not None:
                raise OSError(f"ambiguous publication state at {output.destination}")
            output.destination.replace(output.staged)
        output.backup.replace(output.destination)
    elif output.original is None and destination is not None:
        if _identity(output.staged) is not None:
            raise OSError(f"unexpected output at {output.destination}")
        output.destination.replace(output.staged)
    if _identity(output.destination) != output.original:
        raise OSError(f"original output not restored at {output.destination}")


def reject_symlinks(root: Path, *, recursive: bool = True) -> None:
    """Reject linked generator destinations/sources before writes can escape staging.

    Reject rather than dereference: links may point outside the checkout or be dangling, and
    silently materializing them would change the hand-written resource tree on publication.
    As with publication, callers must exclude concurrent filesystem writers.
    """
    pending = [root]
    while pending:
        path = pending.pop()
        if path.is_symlink():
            raise ValueError(f"generator paths must not be symlinks: {path}")
        if recursive and path.is_dir():
            pending.extend(sorted(path.iterdir(), reverse=True))


@contextmanager
def generation_transaction(
    existing: OutputTransaction | None = None,
) -> Iterator[OutputTransaction]:
    """Join an outer command's transaction, or publish an individual pass on success."""
    if existing is not None:
        yield existing
        return
    transaction = OutputTransaction()
    try:
        yield transaction
        transaction.publish()
    finally:
        transaction.cleanup()
