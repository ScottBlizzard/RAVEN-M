from __future__ import annotations

from pathlib import Path

from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (
    EvidenceCalibratedObligationBranchFrontierMemory,
)
from raven_m.official_qwen_mobile.working_memory import append_working_memory


ROOT = Path(__file__).resolve().parents[3]


def test_controller_interface_keeps_a10_prompt_only_and_observes_executed_action() -> None:
    source = (ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py").read_text(encoding="utf-8")
    assert 'context={"before": before, "goal": effective_goal}' in source
    assert "canonical_action=canonical_action" in source
    assert "before=before" in source and "after=after" in source
    assert 'memory_read["exact_injected_text"] = rendered_memory' in source
    assert 'hasattr(\n                    self.working_memory, "history_summary"\n                )' in source
    assert not hasattr(EvidenceCalibratedObligationBranchFrontierMemory(), "history_summary")
    assert not hasattr(EvidenceCalibratedObligationBranchFrontierMemory(), "record_protocol")


def test_empty_memory_does_not_change_a0_prompt() -> None:
    baseline = "The user query: delete two items.\nTask progress: .\n"
    assert append_working_memory(baseline, "") == baseline


def test_runner_constructs_a10_without_guard_or_override() -> None:
    source = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    assert "EvidenceCalibratedObligationBranchFrontierMemory(" in source
    assert '"--a10-ecobf"' in source
    assert "or a10_scored_arm" in source
    assert "if args.a2_verified_progress_memory\n                    else None" in source
    assert '"causal_read_analysis": causal_read_analysis' in source
    assert 'f"{result_prefix} PERFORMANCE PASS / MECHANISM EVIDENCE FAIL"' in source
    assert 'f"{result_prefix} OVERALL PASS"' in source


def test_launcher_receipt_binds_exact_launch_intent_command() -> None:
    launcher = (ROOT / "implementation/scripts/start_a10_server.sh").read_text(
        encoding="utf-8"
    )
    qualifier = (
        ROOT / "implementation/scripts/qualify_a10_live_server.py"
    ).read_text(encoding="utf-8")
    contract = (
        ROOT
        / "implementation/src/raven_m/official_qwen_mobile/a10_contract.py"
    ).read_text(encoding="utf-8")
    assert 'exec "${ENV_DIR}/bin/python" "${ENV_DIR}/bin/vllm"' in launcher
    assert 'cmdline != [str(item) for item in intent.get("command") or []]' in qualifier
    assert '"launch_intent_path": str(args.launch_intent.resolve())' in qualifier
    assert 'receipt.get("launch_intent_sha256") != file_sha256(launch_intent_path)' in contract
