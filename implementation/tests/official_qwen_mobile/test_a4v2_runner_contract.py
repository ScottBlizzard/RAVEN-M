from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_runner_exposes_distinct_a4v2_identity_and_fixed_seven() -> None:
    source = (REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(
        encoding="utf-8"
    )
    assert 'choices=("a3", "a4", "a4v2", "a5")' in source
    assert "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1" in source
    assert '"BrowserMultiply"' in source
    assert '"OsmAndMarker"' in source
    assert '"scientific_fail_fast": False' in source
    assert 'args.a345_arm != "a4v2" and task_name in A345_REQUIRED_GATE_TASKS' in source
    assert 'and len(summaries) != len(expected_keys)' in source
    assert 'A4-v2 remaining12 is locked until the seven-task parent is 7/7' in source
    assert 'A4V2_WORKFLOW_SYSTEM_PROMPT if args.a345_arm == "a4v2"' in source
    assert '"schema": "a4v2.scored_checkpoint.v1"' in source
    assert 'A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1' in source


def test_runner_loads_only_validated_frozen_bank() -> None:
    source = (REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(
        encoding="utf-8"
    )
    assert "validate_a4v2_bank(payload)" in source
    assert "FaithfulOfflineWorkflowMemory(" in source
    assert "_validate_a4v2_preflight(" in source
    assert "_validate_a4v2_receipt(" in source
