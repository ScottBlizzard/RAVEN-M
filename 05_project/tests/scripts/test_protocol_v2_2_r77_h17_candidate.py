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
    ROOT / "05_project/configs/experiments/v2_2_h17_candidate_r77.json"
)
WRAPPER = (
    ROOT / "05_project/scripts/"
    "run_protocol_v2_2_r77_h17_candidate_smoke.py"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"
R76_STOP_REPORT = (
    ROOT / "reports/protocol_v2_2_r76_h17_candidate_stopped.json"
)
R77_LOCAL_REPORT = (
    ROOT / "reports/protocol_v2_2_r77_local_validation.json"
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


def load_wrapper(name: str):
    return load_module(WRAPPER, name)


def test_r77_candidate_preserves_frozen_experiment_controls() -> None:
    wrapper = load_wrapper("r77_candidate_controls")
    generated = json.loads(
        wrapper.build_candidate_manifest().read_text(encoding="utf-8")
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
    assert generated["source_commit"] == wrapper.SOURCE_COMMIT
    assert generated["source_tag"] == wrapper.SOURCE_TAG
    assert generated["candidate_scope"] == {
        "formal_scoring": False,
        "authorized_development_sequence": 2,
        "authorized_task_id": "H17",
        "authorized_variant": "M0",
    }


def test_r77_candidate_freeze_hashes_match_exact_source_commit() -> None:
    wrapper = load_wrapper("r77_candidate_freeze")
    manifest = json.loads(
        wrapper.build_candidate_manifest().read_text(encoding="utf-8")
    )
    resolved = subprocess.check_output(
        ["git", "rev-list", "-n", "1", wrapper.SOURCE_TAG],
        cwd=ROOT,
        text=True,
    ).strip()
    assert resolved == wrapper.SOURCE_COMMIT
    assert len(manifest["freeze_files"]) == 28
    for record in manifest["freeze_files"]:
        frozen = subprocess.check_output(
            ["git", "show", f"{resolved}:{record['path']}"],
            cwd=ROOT,
        )
        assert sha256(frozen).hexdigest() == record["sha256"]


def test_r77_historical_static_validation_rejects_future_head_drift() -> None:
    wrapper = load_wrapper("r77_candidate_static_wrapper")
    runner = load_module(RUNNER, "r77_candidate_static_runner")
    manifest = json.loads(
        wrapper.build_candidate_manifest().read_text(encoding="utf-8")
    )
    with pytest.raises(
        RuntimeError,
        match="Versioned Gate-F freeze file hash mismatch",
    ):
        runner.validate_manifest(
            manifest,
            expected_source_tag=wrapper.SOURCE_TAG,
            expected_source_commit=wrapper.SOURCE_COMMIT,
            expected_prerequisite_commit=wrapper.PARENT_GATE_E_COMMIT,
        )


def test_r77_candidate_prerequisites_are_byte_exact() -> None:
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    assert sha256(R76_STOP_REPORT.read_bytes()).hexdigest() == (
        overlay["prerequisite_r76_stop_report"]["sha256"]
    )
    stopped = json.loads(R76_STOP_REPORT.read_text(encoding="utf-8"))
    assert stopped["decision"] == (
        "r76_completed_distinct_identity_bound_field_capture_but_"
        "executor_provenance_and_visual_critic_contracts_rejected_same_"
        "episode_routed_detail_evidence"
    )
    assert stopped["immutability"]["suite_may_be_resumed"] is False
    assert sha256(R77_LOCAL_REPORT.read_bytes()).hexdigest() == (
        overlay["prerequisite_r77_local_validation"]["sha256"]
    )
    local = json.loads(R77_LOCAL_REPORT.read_text(encoding="utf-8"))
    assert local["source_commit"] == (
        "0fd13aa540f811b7ede347b7736e7aa081393532"
    )
    assert local["formal_gate_f_authorized"] is False
    assert local["live_development_smoke_authorized"] is False


@pytest.mark.parametrize(
    "argv",
    [
        ["--adb-path", "adb", "--batch", "1"],
        ["--adb-path", "adb", "--development-smoke-sequence", "1"],
        ["--adb-path", "adb", "--development-smoke-sequence=8"],
        ["--adb-path", "adb"],
        [
            "--adb-path",
            "adb",
            "--preflight-only",
            "--development-smoke-sequence",
            "2",
        ],
    ],
)
def test_r77_candidate_wrapper_rejects_every_other_live_scope(
    argv: list[str],
) -> None:
    wrapper = load_wrapper("r77_candidate_invalid_invocation")
    with pytest.raises(RuntimeError):
        wrapper.validate_invocation(argv)


def test_r77_candidate_wrapper_allows_only_preflight_or_h17_m0() -> None:
    wrapper = load_wrapper("r77_candidate_valid_invocation")
    wrapper.validate_invocation(["--adb-path", "adb", "--preflight-only"])
    wrapper.validate_invocation(
        ["--adb-path", "adb", "--development-smoke-sequence", "2"]
    )


def test_r77_candidate_wrapper_uses_non_formal_mode() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "allow_development_smoke=True" in source
    assert "diagnostic_pause=None" in source
    assert "AUTHORIZED_SEQUENCE = 2" in source


def test_r77_mechanism_is_bounded_answer_free_and_audited() -> None:
    controller = (
        ROOT / "05_project/src/raven_m/controller/episode_controller.py"
    ).read_text(encoding="utf-8")
    guard = (
        ROOT / "05_project/src/raven_m/controller/protocol_v2_guard.py"
    ).read_text(encoding="utf-8")
    assert "target_row_detail_evidence_manifest" in controller
    assert "same_episode_routed_visual_evidence_contract" in controller
    assert "DATED_TARGET_ROUTED_ANSWER_PROVENANCE" in controller
    assert (
        '"requested_field_values_must_also_appear_on_current_list": False'
        in controller
    )
    assert "target_row_detail_evidence_manifest" in guard
    assert '"answer_values_in_manifest": False' in guard
    assert "identity-unconfirmed row" in guard
    assert "crop_sha256" in guard


def test_r77_mechanism_leaves_shared_frozen_sources_unchanged() -> None:
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    for path in (
        "05_project/src/raven_m/env/androidworld_adapter.py",
        "05_project/src/raven_m/history/policies.py",
        "05_project/src/raven_m/roles/orchestrator.py",
        "05_project/src/raven_m/memory/manager.py",
        "05_project/prompts/executor_raven_v2.md",
        "05_project/prompts/planner_v1.md",
        "05_project/prompts/critic_v1.md",
    ):
        assert sha256((ROOT / path).read_bytes()).hexdigest() == (
            overlay["updated_freeze_hashes"][path]
        )


def test_r77_mechanism_sources_are_task_and_answer_agnostic() -> None:
    paths = [
        ROOT / "05_project/src/raven_m/controller/episode_controller.py",
        ROOT / "05_project/src/raven_m/controller/protocol_v2_guard.py",
        ROOT / "05_project/src/raven_m/env/androidworld_adapter.py",
        ROOT / "05_project/src/raven_m/history/policies.py",
        ROOT / "05_project/prompts/executor_raven_v2.md",
        ROOT / "05_project/prompts/planner_v1.md",
        ROOT / "05_project/prompts/critic_v1.md",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for forbidden in (
        "SportsTrackerActivitiesOnDate",
        "de.dennisguse.opentracks",
        "September 24 2023",
        "September 24, 2023",
        "Skill work",
        "Recovery day",
        "cycling",
        "inline skating",
        "H17",
    ):
        assert forbidden not in source
