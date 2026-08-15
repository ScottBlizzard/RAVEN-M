from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def test_controller_transport_confirms_before_commit_and_sanitizes_v3_observation() -> None:
    source = CONTROLLER.read_text(encoding="utf-8")
    ast.parse(source)
    read = source.index("rendered_memory, memory_read = self.working_memory.read(")
    append = source.index("user_prompt = append_working_memory(", read)
    generate = source.index("call = self.client.generate(", append)
    commit = source.index("self.working_memory.commit_injection(", generate)
    assert read < append < generate < commit
    assert '"model_transport_failure:' in source
    marker = source.index('== "a1r3v3_one_shot_controller_nonprogress_receipt_v1"')
    branch_end = source.index("else:", marker)
    branch = source[marker:branch_end]
    assert '"same_shape"' in branch
    assert '"changed_pixel_fraction_gt_5"' in branch
    assert "before=before" not in branch and "after=after" not in branch


def test_runner_has_distinct_identity_prompt_gate_checkpoint_and_result() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"a1r3v3": {',
        '"--a1r3v3-oscnr"',
        '("a1r3v3", args.a1r3v3_oscnr)',
        'dual_arm_name == "a1r3v3"',
        'A1-R3-v3 six-task capability gate failed',
        '_append_a1r3v3_checkpoint',
        '_load_a1r3v3_checkpoint_pointer',
        '_a1r3v3_causal_analysis',
        '"PENDING_MATCHED_NEUTRALIZED_ABLATION"',
        '"calls_not_above_a1r2": calls <= 603',
    ):
        assert required in source
    assert 'if dual_arm_name in {"a1r2", "a1r3v3", "a1r3"' in source


def test_wrapper_binds_only_v3_artifacts() -> None:
    source = (ROOT / "implementation/scripts/run_a1r3v3_oscnr.py").read_text(encoding="utf-8")
    assert "--a1r3v3-oscnr" in source
    assert "A1R3V3_OSCNR_ZERO_GENERATION_PREFLIGHT.json" in source
    assert "--a1r3-srpl" not in source
