from __future__ import annotations

import importlib.util
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
BASE_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_hard_micro_gate_r56.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"
WRAPPER = (
    ROOT / "05_project/scripts/run_protocol_v2_2_r59_h01_candidate_smoke.py"
)
R58_STOPPED_CHECKPOINT = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r58_candidate_"
    "development_smoke_sequence_1/batch_01_checkpoint.json"
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


def test_r59_wrapper_freezes_exact_candidate_source() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    commit = re.search(
        r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE
    )
    tag = re.search(r'^SOURCE_TAG = "([^"]+)"$', source, re.MULTILINE)
    assert commit and tag
    assert commit.group(1) == (
        "868c1ffa39c6d1415f3b3831ed295e61672c87af"
    )
    assert tag.group(1) == "protocol-v2-2-r59-local-candidate"


def test_r59_candidate_preserves_historical_controls_and_freeze() -> None:
    wrapper = load_module(WRAPPER, "r59_h01_wrapper")
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
    for record in candidate["freeze_files"]:
        frozen = subprocess.check_output(
            [
                "git",
                "show",
                f"{wrapper.SOURCE_COMMIT}:{record['path']}",
            ],
            cwd=ROOT,
        )
        assert sha256(frozen).hexdigest() == record["sha256"]
    prerequisite = candidate["prerequisite_gate_e_report"]
    frozen_prerequisite = subprocess.check_output(
        [
            "git",
            "show",
            f"{wrapper.SOURCE_COMMIT}:{prerequisite['path']}",
        ],
        cwd=ROOT,
    )
    assert (
        sha256(frozen_prerequisite).hexdigest()
        == prerequisite["sha256"]
    )


def test_r58_development_stop_remains_byte_frozen() -> None:
    assert sha256(R58_STOPPED_CHECKPOINT.read_bytes()).hexdigest() == (
        "1e94814cc3addba8949d96699395988c9bcd9406de6028525dce0a8d1cb0a473"
    )


def test_r59_uses_only_isolated_non_scored_development_mode() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"development_smoke"] = True' in source
    assert '"formal_scoring"] = False' in source
    assert "--development-smoke-sequence" in source
    assert "runs/protocol_v2_2_development" in source
