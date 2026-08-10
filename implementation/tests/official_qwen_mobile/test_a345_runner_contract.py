from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile.a345_contract import (
    A345_GATE_TASKS,
    A345_TERMINAL_CHECKPOINT_STATUSES,
    MODEL_ID,
    MODEL_MANIFEST_SHA256,
    MODEL_REALPATH,
    REPOSITORY_ROOT,
    activation_valid,
    validate_launch_receipt,
)
from raven_m.official_qwen_mobile.protocol import (
    A3_CONACT_SYSTEM_PROMPT,
    A4_WORKFLOW_SYSTEM_PROMPT,
    A5_VISUAL_GRAPH_SYSTEM_PROMPT,
    OFFICIAL_SYSTEM_PROMPT,
)


def test_three_prompts_preserve_the_frozen_official_protocol() -> None:
    assert sha256(OFFICIAL_SYSTEM_PROMPT.encode()).hexdigest() == (
        "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
    )
    assert A3_CONACT_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT)
    assert A4_WORKFLOW_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT)
    assert A5_VISUAL_GRAPH_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT)


def test_gate_is_exactly_five_a1_successes_and_manifest_seed_is_fixed() -> None:
    ledger = json.loads(
        (REPOSITORY_ROOT / "evidence/a345/A0_A1_A2_FROZEN_REFERENCE_LEDGER.json").read_text(
            encoding="utf-8"
        )
    )
    assert tuple(ledger["gate_tasks"]) == A345_GATE_TASKS
    assert ledger["seed"] == 20260806
    assert ledger["summaries"]["A1"]["success_count"] == 5
    successes = {
        row["task_name"] for row in ledger["tasks"] if bool(row["A1"]["success"])
    }
    assert successes == set(A345_GATE_TASKS)


def test_activation_gate_requires_a_later_read_for_online_memories() -> None:
    assert not activation_valid({"steps": [{"memory_write": {"written": True}}]}, "a3")
    assert activation_valid(
        {
            "steps": [
                {"memory_write": {"written": True}, "memory_read": {"nonempty": False}},
                {"memory_read": {"nonempty": True}},
            ]
        },
        "a5",
    )
    assert not activation_valid({"steps": [{"memory_read": {"nonempty": False}}]}, "a4")
    assert activation_valid({"steps": [{"memory_read": {"nonempty": True}}]}, "a4")


def test_both_scientific_and_activation_failures_are_terminal() -> None:
    assert A345_TERMINAL_CHECKPOINT_STATUSES == {
        "stopped_capability_gate_failure",
        "stopped_memory_activation_failure",
    }


def _write_receipt(path: Path, preflight: Path, **updates: object) -> None:
    payload = {
        "status": "pass",
        "generation_calls": 0,
        "served_model_id": MODEL_ID,
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": 18000,
        "process_cmdline": ["vllm", "serve", MODEL_REALPATH, "--served-model-name", MODEL_ID],
        "packages": {"vllm": "0.10", "torch": "2.7", "transformers": "4.55"},
        "a345_preflight_sha256": sha256(preflight.read_bytes()).hexdigest(),
    }
    payload.update(updates)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_launch_receipt_binds_model_weights_runtime_and_preflight(tmp_path: Path) -> None:
    preflight = tmp_path / "preflight.json"
    preflight.write_text('{"status":"pass"}', encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    _write_receipt(receipt, preflight)
    assert validate_launch_receipt(receipt, preflight_path=preflight)["status"] == "pass"
    _write_receipt(receipt, preflight, a345_preflight_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="preflight_receipt_binding_drift"):
        validate_launch_receipt(receipt, preflight_path=preflight)


def test_runner_contains_fail_fast_gate_and_exact_validity_closure() -> None:
    source = (REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(
        encoding="utf-8"
    )
    assert "A345_TERMINAL_CHECKPOINT_STATUSES" in source
    assert "A4_WORKFLOW_BANK" in source
    assert "_load_a4_workflows" in source
    assert "A4 workflow bank drifted after zero-generation preflight" in source
    assert 'checkpoint("stopped_capability_gate_failure")' in source
    assert 'checkpoint("stopped_memory_activation_failure")' in source
    assert "len(summaries) != 19" in source
    assert "any(not item.get(\"resolved_by_episode_id\") for item in invalid_attempts)" in source
