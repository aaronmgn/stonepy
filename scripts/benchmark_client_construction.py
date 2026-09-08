"""Compare unguarded and locked lazy clients emitted in memory, without changing generated files.

From the checkout:
    uv run --offline --no-sync python scripts/benchmark_client_construction.py
"""

from __future__ import annotations

import asyncio
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from stonepy import ClientConfig
from stonepy._generator import emit_client

_LOCKED_CLASS = emit_client._client_class
_BATCHES = 21
_SIZE = 50


def _unlocked_class(
    name: str, targets: list[emit_client._ResourceTarget], *, async_client: bool
) -> list[str]:
    """Render the preceding unguarded design as the construction baseline."""
    lines = _LOCKED_CLASS(name, targets, async_client=async_client)
    lines.remove("        self._resource_lock = Lock()\n")
    for target in targets:
        resource_type = target.async_class_name if async_client else target.class_name
        prop = target.property_name
        lines.remove("            with self._resource_lock:\n")
        lines.remove(f"                if self._{prop} is None:\n")
        old = f"                    self._{prop} = {resource_type}(self._ctx)\n"
        lines[lines.index(old)] = f"            self._{prop} = {resource_type}(self._ctx)\n"
    return lines


def _clients() -> tuple[dict[str, Any], dict[str, Any], int]:
    resources = Path(__file__).resolve().parents[1] / "src" / "stonepy" / "resources"
    targets = [
        emit_client._resource_target(path)
        for path in sorted(resources.iterdir())
        if path.is_dir() and not path.name.startswith((".", "_"))
    ]
    unlocked: dict[str, Any] = {}
    locked: dict[str, Any] = {}
    exec(compile(emit_client._render_client(targets), "locked_client.py", "exec"), locked)
    with patch.object(emit_client, "_client_class", _unlocked_class):
        exec(compile(emit_client._render_client(targets), "unlocked_client.py", "exec"), unlocked)
    return unlocked, locked, len(targets)


async def main() -> None:
    unlocked, locked, groups = _clients()
    config = ClientConfig(base_url="https://api.example")
    rng = random.Random(613)
    for name in ("StoneXClient", "AsyncStoneXClient"):
        async_mode = name.startswith("Async")
        classes = {"unlocked": unlocked[name], "locked": locked[name]}
        times: dict[str, list[float]] = {label: [] for label in classes}
        for cls in classes.values():
            for _ in range(10):
                client = cls(config)
                if async_mode:
                    await client.aclose()
                else:
                    client.close()
                del client
        for _ in range(_BATCHES):
            labels = list(classes)
            rng.shuffle(labels)
            for label in labels:
                samples = []
                for _ in range(_SIZE):
                    start = time.perf_counter_ns()
                    client = classes[label](config)
                    samples.append(time.perf_counter_ns() - start)
                    if async_mode:
                        await client.aclose()
                    else:
                        client.close()
                    del client
                times[label].append(statistics.mean(samples) / 1e6)
        deltas = [b - a for a, b in zip(times["unlocked"], times["locked"], strict=True)]
        mean = statistics.mean(deltas)
        # Two-sided 95% t interval for paired batch means, 20 degrees of freedom.
        half = 2.086 * statistics.stdev(deltas) / _BATCHES**0.5
        print(
            json.dumps(
                {
                    "client": name,
                    "batches": _BATCHES,
                    "constructions_per_batch": _SIZE,
                    "resource_groups": groups,
                    "unlocked_ms": statistics.mean(times["unlocked"]),
                    "locked_ms": statistics.mean(times["locked"]),
                    "paired_delta_ms": mean,
                    "delta_95pct_ci_ms": [mean - half, mean + half],
                    "batch_means_ms": times,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
