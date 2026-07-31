from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_hard_micro_gate_r56.json"
)
LEGACY_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_hard_micro_gate.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_f_r56.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("gate_f_r56_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def complete_results(value: dict) -> list[dict]:
    rows = []
    for item in value["schedule"]:
        rows.append(
            {
                **item,
                "seed": value["instance_seed"],
                "goal_sha256": f"goal-{item['task_id']}",
                "params_sha256": f"params-{item['task_id']}",
                "success": True,
                "failure_code": None,
                "termination_reason": "model_done",
                "model_call_count": 10,
                "wall_time_seconds": 10.0,
                "answer_action_count": int(item["task_id"] == "H17"),
                "answer_cache_match_count": int(item["task_id"] == "H17"),
                "completion_adjudication_count": 0,
                "action_adjudication_count": 0,
                "memory_audit_errors": [],
                "max_prompt_tokens": 1024,
                "reset_audit": {"passed": True},
                "evaluator_prompt_leak_steps": [],
                "valid_after_one_repair": True,
                "unhandled_third_identical_no_effect_action": False,
                "loop_recovery_obligation_count": 0,
                "loop_recovery_completion_count": 0,
                "loop_recovery_validation_block_count": 4,
                "readiness_observation_count": 1,
                "semantic_progress_audit": {
                    "passed": True,
                    "executed_blocked_action_steps": [],
                    "unresolved_guard_repair": False,
                },
            }
        )
    return rows


def aggregate(module, value: dict, results: list[dict], startup=None):
    return module.aggregate(
        manifest=value,
        health={
            "backend": module.EXPECTED_BACKEND,
            "revision": module.EXPECTED_REVISION,
        },
        results=results,
        infrastructure_attempts=[],
        gate_started_at="2026-07-31T00:00:00+00:00",
        active_seconds=120.0,
        batch_runs=[],
        current_batch=3,
        stopped_early=False,
        stop_reason=None,
        startup_audit=startup or {"last_status": "clean"},
    )


def test_r56_preserves_the_legacy_hard_experiment_controls() -> None:
    value = frozen_manifest()
    legacy = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    for key in (
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
    ):
        assert value[key] == legacy[key]
    for key, expected in legacy["acceptance"].items():
        assert value["acceptance"][key] == expected
    for key, expected in legacy["stop_policy"].items():
        assert value["stop_policy"][key] == expected
    assert value["protocol"] == "androidworld_protocol_v2_2_exploratory"
    assert not value["stop_policy"]["automatic_next_batch"]
    assert not value["stop_policy"]["automatic_gate_g_transition"]


def test_r56_wrapper_manifest_and_gate_e_prerequisite_are_exact() -> None:
    value = frozen_manifest()
    source = WRAPPER.read_text(encoding="utf-8")
    tag = re.search(r'^SOURCE_TAG = "([^"]+)"$', source, re.MULTILINE)
    commit = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert tag and commit
    assert tag.group(1) == value["source_tag"]
    assert commit.group(1) == value["source_commit"]
    prerequisite = value["prerequisite_gate_e_report"]
    report = json.loads(
        (ROOT / prerequisite["path"]).read_text(encoding="utf-8")
    )
    assert report["decision"]["gate_e"] == "pass"
    assert report["suite"]["gate_passed"] is True
    assert report["suite"]["source_commit"] == value["source_commit"]


def test_r56_manifest_validates_exact_source_and_freeze() -> None:
    module = load_runner()
    value = frozen_manifest()
    audit = module.validate_manifest(
        value,
        expected_source_tag=value["source_tag"],
        expected_source_commit=value["source_commit"],
    )
    assert audit["schedule_cell_count"] == 12
    assert audit["task_pair_count"] == 6
    assert all(row["passed"] for row in audit["freeze_file_checks"])
    assert all(row["passed"] for row in audit["prerequisite_checks"])

    value["source_commit"] = "0" * 40
    try:
        module.validate_manifest(
            value,
            expected_source_tag="protocol-v2-2-gate-e-r56",
            expected_source_commit=(
                "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"
            ),
        )
    except RuntimeError as exc:
        assert "source commit" in str(exc)
    else:
        raise AssertionError("source drift must be rejected")


def test_r56_aggregate_uses_semantic_not_raw_validation_counts() -> None:
    module = load_runner()
    value = frozen_manifest()
    results = complete_results(value)
    summary = aggregate(module, value, results)
    assert summary["gate_passed"]
    assert summary["criteria"]["loop_recovery"]
    assert summary["criteria"]["semantic_progress_audit"]
    assert summary["criteria"]["startup_environment_accounting"]
    assert summary["criteria"]["readiness_accounting"]
    assert summary["criteria"][
        "consequential_action_adjudication_accounting"
    ]
    assert all(summary["criteria"].values())


def test_r56_aggregate_fails_closed_on_each_versioned_audit() -> None:
    module = load_runner()
    value = frozen_manifest()

    semantic = complete_results(value)
    semantic[0]["semantic_progress_audit"]["passed"] = False
    assert not aggregate(module, value, semantic)["criteria"][
        "semantic_progress_audit"
    ]

    readiness = complete_results(value)
    readiness[0]["readiness_observation_count"] = 0
    assert not aggregate(module, value, readiness)["criteria"][
        "readiness_accounting"
    ]

    startup = aggregate(
        module,
        value,
        complete_results(value),
        startup={"last_status": "failed"},
    )
    assert not startup["criteria"]["startup_environment_accounting"]
    assert not startup["gate_passed"]


def test_r56_preflight_is_zero_call_and_does_not_create_suite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_runner()
    value = frozen_manifest()
    value["output_root"] = str(tmp_path)
    value["suite_id"] = "absent_scored_suite"

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="List of devices attached\nemulator-5554\tdevice\n",
            returncode=0,
        ),
    )

    class FakeClient:
        def __init__(self, url: str):
            self.url = url

        def health(self):
            return {
                "backend": module.EXPECTED_BACKEND,
                "revision": module.EXPECTED_REVISION,
            }

    monkeypatch.setattr(module, "TransformersClient", FakeClient)
    output = tmp_path / "preflight.json"
    result = module.run_preflight(
        manifest=value,
        manifest_audit={"passed": True},
        url="http://127.0.0.1:18000",
        adb_path="adb",
        output=output,
    )
    assert result == 0
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["passed"]
    assert evidence["model_calls"] == 0
    assert evidence["gpu_experiment_cells"] == 0
    assert evidence["protocol_v1_seal"]["passed"]
    assert evidence["protocol_v1_seal"]["file_count"] == 197
    assert evidence["automatic_batch_1_launch"] is False
    assert not (tmp_path / value["suite_id"]).exists()
