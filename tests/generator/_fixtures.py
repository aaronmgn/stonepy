"""Catalog fixtures for passes that require resolved response contracts."""

import json
from pathlib import Path


def resolved_catalog(root: Path) -> Path:
    """Copy the partial catalog and supply its two missing response DTOs."""
    source = Path(__file__).parent / "fixtures"
    root.mkdir(parents=True, exist_ok=True)
    for name in ("endpoints.json", "data-types.json", "lookup-codes.json"):
        (root / name).write_text((source / name).read_text())
    path = root / "data-types.json"
    types = json.loads(path.read_text())
    types.extend(
        {"name": name, "properties": []}
        for name in ("ApiTradeOrderResponseDTO", "GetActiveStopLimitOrderResponseDTOv2")
    )
    path.write_text(json.dumps(types))
    return root
