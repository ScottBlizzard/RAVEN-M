from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_protocol_v1_seal_still_reproduces() -> None:
    path = ROOT / "05_project/scripts/seal_protocol_v1_breadth.py"
    spec = importlib.util.spec_from_file_location("seal_v1", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verify_existing_seal()
    assert result["file_count"] == 197
    assert result["failure_count"] == 0
    assert result["passed"]
