from __future__ import annotations

import importlib.util
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
BASE_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_hard_micro_gate_r56.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"
WRAPPER = (
    ROOT / "05_project/scripts/run_protocol_v2_2_r57_h01_candidate_smoke.py"
)
STOPPED_CHECKPOINT = (
    ROOT
    / "runs/protocol_v2_2/hard_micro_v2_2_seed20260730_r56/"
    "batch_01_checkpoint.json"
)


def load_module(path: Path, name: str):
    scripts = str(ROOT / "05_project/scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r57_wrapper_freezes_exact_candidate_source() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    commit = re.search(
        r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE
    )
    tag = re.search(r'^SOURCE_TAG = "([^"]+)"$', source, re.MULTILINE)
    assert commit and tag
    assert commit.group(1) == "4667166b60710f32348ace47243e41bcc041cd13"
    assert tag.group(1) == "protocol-v2-2-r57-local-candidate"


def test_r57_candidate_preserves_r56_hard_controls_and_validates() -> None:
    wrapper = load_module(WRAPPER, "r57_h01_wrapper")
    runner = load_module(RUNNER, "r57_gate_f_runner")
    candidate_path = wrapper.build_candidate_manifest()
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    for key in (
        "protocol",
        "instance_seed",
        "blocked_order_seed",
        "blocked_order_algorithm",
        "blocked_order_candidate_index",
        "variants",
        "task_families",
        "schedule",
        "prompts",
        "schemas",
        "limits",
        "acceptance",
        "stop_policy",
        "prerequisite_gate_e_report",
    ):
        assert candidate[key] == base[key]
    assert candidate["source_commit"] == wrapper.SOURCE_COMMIT
    assert candidate["source_tag"] == wrapper.SOURCE_TAG
    audit = runner.validate_manifest(
        candidate,
        expected_source_tag=wrapper.SOURCE_TAG,
        expected_source_commit=wrapper.SOURCE_COMMIT,
        expected_prerequisite_commit=wrapper.PARENT_GATE_E_COMMIT,
    )
    assert all(row["passed"] for row in audit["freeze_file_checks"])
    assert all(row["passed"] for row in audit["prerequisite_checks"])


def test_r56_stopped_checkpoint_remains_byte_frozen() -> None:
    assert sha256(STOPPED_CHECKPOINT.read_bytes()).hexdigest() == (
        "c095b69e550c66c01fa5e75c5cc1aa29cce1d26868001716590868611297cda6"
    )


def test_gate_f_runner_marks_development_smokes_non_scored() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"development_smoke"] = True' in source
    assert '"formal_scoring"] = False' in source
    assert "--development-smoke-sequence" in source
    assert "runs/protocol_v2_2_development" in source
