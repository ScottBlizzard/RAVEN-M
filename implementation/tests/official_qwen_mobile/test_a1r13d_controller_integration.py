from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"


def test_runner_has_distinct_target_first_identity_and_gates() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for text in (
        '"a1r13d": {',
        '"--a1r13d-evr"',
        '("a1r13d", args.a1r13d_evr)',
        'dual_arm_name == "a1r13d"',
        'A1-R13D Browser target gate failed',
        'target_first',
    ):
        assert text in source
