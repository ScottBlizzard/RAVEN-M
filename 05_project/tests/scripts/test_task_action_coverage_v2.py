from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_all_19_tasks_pass_v2_action_coverage() -> None:
    path = ROOT / "05_project/scripts/audit_task_action_coverage.py"
    spec = importlib.util.spec_from_file_location("coverage_v2", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.audit(ROOT)
    assert result["task_count"] == 19
    assert result["passed_task_count"] == 19
    assert result["passed"], result["rows"]


def test_v2_action_coverage_fails_closed_for_unsupported_task(
    tmp_path: Path,
) -> None:
    path = ROOT / "05_project/scripts/audit_task_action_coverage.py"
    spec = importlib.util.spec_from_file_location("coverage_v2_negative", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = json.loads(
        (ROOT / "05_project/configs/task_capabilities_v2.json").read_text(
            encoding="utf-8"
        )
    )
    matrix["tasks"][0]["required_actions"].append("unsupported_action")
    target = tmp_path / "matrix.json"
    target.write_text(json.dumps(matrix), encoding="utf-8")
    result = module.audit(ROOT, matrix_path=target)
    assert not result["passed"]
    assert "unsupported_action" in str(result["rows"][0]["errors"])
