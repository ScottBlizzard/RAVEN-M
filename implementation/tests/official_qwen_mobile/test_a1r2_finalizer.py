from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'implementation/scripts/finalize_a1r2_cvp.py'
SPEC = importlib.util.spec_from_file_location('finalize_a1r2_cvp', SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_expected_order_has_gate_five_first_and_all_19() -> None:
    order = module.expected_order()
    assert tuple(order[:5]) == module.GATE5_TASKS
    assert len(order) == len(set(order)) == 19


def test_gate_and_content_hash_are_deterministic() -> None:
    summaries = [
        {'task_name': name, 'success': True, 'evaluator_reward': 1.0}
        for name in module.GATE5_TASKS
    ]
    assert module.gate_report(summaries, module.GATE5_TASKS)['status'] == 'pass'
    assert module.content_sha256({'schema': 'x', 'content_sha256': 'a'}) == module.content_sha256(
        {'content_sha256': 'b', 'schema': 'x'}
    )
