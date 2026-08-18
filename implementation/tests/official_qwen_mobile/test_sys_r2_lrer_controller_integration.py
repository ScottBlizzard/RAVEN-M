from __future__ import annotations

import inspect
from pathlib import Path

from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py"


def test_controller_defers_before_memory_write_mapping_and_execution() -> None:
    source = inspect.getsource(OfficialQwenMobileController.run)
    parse_at = source.index("decision = parse_official_response")
    review_at = source.index("review_result_action", parse_at)
    defer_at = source.index("deferred_response_not_committed", review_at)
    protocol_at = source.index("record_protocol", review_at)
    mapping_at = source.index("canonical_action = decision.canonical_action", review_at)
    assert parse_at < review_at < defer_at < protocol_at < mapping_at
    block = source[review_at:protocol_at]
    assert '"executed": False' not in block  # the step record is already initialized false
    assert '"committed_history_summary": None' in block
    assert '"deferred_response_not_committed": True' in block
    assert "continue" in block


def test_controller_uses_only_prior_executed_responses_for_direct_injection() -> None:
    source = inspect.getsource(OfficialQwenMobileController.run)
    prepare_at = source.index("prepare_direct_injection")
    prepare_block = source[prepare_at : source.index("prepare_aux", prepare_at)]
    assert 'if bool(prior.get("executed"))' in prepare_block
    assert '"thought"' in prepare_block
    assert '"action_summary"' in prepare_block
    assert '"response_sha256"' in prepare_block


def test_runner_binds_new_identity_and_non_fail_fast_seven() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"sys_lrer": {' in source
    assert '"--sys-r2-lrer"' in source
    assert 'dual_arm_name == "sys_lrer"' in source
    assert 'task_name not in dual_arm["contract"].SEVEN_TASK_ORDER' in source
    assert 'complete_seven_task_diagnostic_no_release' in source
    assert 'sys_r2_lrer_result.json' in source
    # SYS-LRER is explicitly excluded from the generic fail-fast prospective gate.
    assert 'dual_arm_name != "sys_lrer"' in source


def test_runner_uses_exact_r2_parent_and_fresh_policy_per_episode() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    arm_at = source.index('if dual_arm_name == "sys_lrer":', source.index("elif dual_memory_arm"))
    block = source[arm_at : source.index("elif dual_arm_name and dual_arm_name.startswith", arm_at)]
    assert 'ttl_requests=8, max_render_chars=1100' in block
    assert "LateRawEvidenceRehydrationPolicy" in block
    assert "sys_trrc_text_delta_counter" in block

