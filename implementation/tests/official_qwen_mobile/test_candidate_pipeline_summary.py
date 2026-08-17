from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/build_candidate_pipeline_summary.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_candidate_pipeline_summary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipeline_summary_closes_all_four_directions() -> None:
    module = load_module()
    report = module.build(ROOT)
    assert report["status"] == "COMPLETE"
    assert len(report["candidate_directions"]) == 4
    assert report["pipeline_closure"]["scientifically_valid_new_live_candidates"] == 0
    assert report["pipeline_closure"]["seven_task_runs_required"] == 0
    assert report["systems"][0]["success_count"] == 6
    assert report["systems"][1]["success_count"] == 6
    assert report["content_sha256"] == module.content_sha(report)


def test_committed_pipeline_summary_matches_when_present() -> None:
    module = load_module()
    output = ROOT / module.OUTPUT
    if output.exists():
        assert json.loads(output.read_text(encoding="utf-8")) == module.build(ROOT)
