from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
BASE_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_hard_micro_gate_r56.json"
)
OVERLAY = (
    ROOT / "05_project/configs/experiments/v2_2_hard_micro_gate_r60.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_f_r60.py"
CANDIDATE_REPORT = (
    ROOT / "reports/protocol_v2_2_r60_h01_candidate_smoke.json"
)
FORMAL_SUITE = (
    ROOT / "runs/protocol_v2_2/hard_micro_v2_2_seed20260730_r60"
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


def test_r60_formal_overlay_preserves_all_experiment_controls() -> None:
    wrapper = load_module(WRAPPER, "r60_formal_wrapper")
    generated = json.loads(
        wrapper.build_formal_manifest().read_text(encoding="utf-8")
    )
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
        assert generated[key] == base[key]
    assert generated["schema_version"] == "protocol_v2_2_gate_f_r60.v1"
    assert generated["source_commit"] == wrapper.SOURCE_COMMIT
    assert generated["source_tag"] == wrapper.SOURCE_TAG
    assert generated["suite_id"] == (
        "hard_micro_v2_2_seed20260730_r60"
    )
    assert generated["output_root"] == "runs/protocol_v2_2"
    assert generated["prerequisite_candidate_report"] == json.loads(
        OVERLAY.read_text(encoding="utf-8")
    )["prerequisite_candidate_report"]


def test_r60_formal_freeze_and_candidate_prerequisite_are_exact() -> None:
    wrapper = load_module(WRAPPER, "r60_formal_freeze_wrapper")
    manifest = json.loads(
        wrapper.build_formal_manifest().read_text(encoding="utf-8")
    )
    execution_commit = subprocess.check_output(
        [
            "git",
            "rev-list",
            "-n",
            "1",
            "protocol-v2-2-gate-f-r60-preflight",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    assert execution_commit == (
        "b63b76aa2969fc97c0696642d9c7114ee5d6ab43"
    )
    for record in manifest["freeze_files"]:
        frozen = subprocess.check_output(
            ["git", "show", f"{execution_commit}:{record['path']}"],
            cwd=ROOT,
        )
        assert sha256(frozen).hexdigest() == record["sha256"]
    candidate = manifest["prerequisite_candidate_report"]
    frozen_report = subprocess.check_output(
        ["git", "show", f"{execution_commit}:{candidate['path']}"],
        cwd=ROOT,
    )
    assert sha256(frozen_report).hexdigest() == candidate["sha256"]
    report = json.loads(frozen_report.decode("utf-8"))
    assert report["decision"] == "end_to_end_candidate_smoke_passed"
    assert report["source_commit"] == wrapper.SOURCE_COMMIT
    assert report["episode"]["success"] is True
    assert report["r60_mechanism_result"]["executed_target_count"] == 5
    assert len(report["artifact_sha256"]) == 13


def test_r60_candidate_report_and_raw_checkpoint_remain_byte_frozen() -> None:
    assert sha256(CANDIDATE_REPORT.read_bytes()).hexdigest() == (
        "ca49654a9367d4240f7e5431c0a93d246a352074f8c977a344d5d8114b1d63b6"
    )
    report = json.loads(CANDIDATE_REPORT.read_text(encoding="utf-8"))
    suite = ROOT / report["suite_path"]
    for name, expected in report["artifact_sha256"].items():
        matches = list(suite.rglob(name))
        assert len(matches) == 1
        assert sha256(matches[0].read_bytes()).hexdigest() == expected


def test_r60_formal_source_tag_and_namespace_are_frozen_after_run() -> None:
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    resolved = subprocess.check_output(
        ["git", "rev-list", "-n", "1", overlay["source_tag"]],
        cwd=ROOT,
        text=True,
    ).strip()
    assert resolved == overlay["source_commit"]
    assert FORMAL_SUITE.is_dir()
    summary = json.loads(
        (FORMAL_SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["formal_scoring"] is True
    assert summary["stopped_early"] is True
    assert summary["batch_completed"] is False
    assert summary["automatic_next_batch"] is False


def test_r60_formal_wrapper_forbids_development_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_module(RUNNER, "r60_formal_mode_runner")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_protocol_v2_2_gate_f_r60.py",
            "--adb-path",
            "adb",
            "--development-smoke-sequence",
            "1",
        ],
    )
    with pytest.raises(RuntimeError, match="forbids development-smoke"):
        runner.main(allow_development_smoke=False)


def test_r60_formal_wrapper_passes_the_fail_closed_mode() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "allow_development_smoke=False" in source
    assert "diagnostic_pause=None" in source
