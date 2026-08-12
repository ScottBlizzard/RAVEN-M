from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile import a12_contract as contract


ROOT = Path(__file__).resolve().parents[3]


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _valid_summaries() -> list[dict[str, object]]:
    return [
        {
            "task_name": task,
            "task_seed": contract.TASK_SEED,
            "episode_id": f"valid_{index:02d}",
            "evaluator_reward": 1.0 if index < 4 else 0.0,
            "transport_attempt_max": 1,
            "error": None,
            "lifecycle_errors": [],
        }
        for index, task in enumerate(contract.TASK_ORDER)
    ]


def test_config_exact_identity_boundary_and_frozen_costs() -> None:
    config = json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["schema"] == contract.CONFIG_SCHEMA
    assert config["mechanism_id"] == contract.MECHANISM_ID
    assert config["experiment_id"] == contract.EXPERIMENT_ID
    assert config["review_commit"] == contract.REVIEW_COMMIT
    assert config["parent_evidence_commit"] == contract.PARENT_EVIDENCE_COMMIT
    assert config["model"] == {
        "id": contract.MODEL_ID,
        "revision": contract.MODEL_REVISION,
        "backend": "vLLM BF16",
        "generation_seed": 3407,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.5,
        "repetition_penalty": 1.0,
        "max_tokens": 32768,
        "transport_attempts_per_model_step": 1,
    }
    intervention = config["intervention"]
    assert intervention["trigger_kind"] == "REPEATED_NO_PROGRESS_ACTION"
    assert intervention["trigger_class_count"] == 1
    assert intervention["required_no_progress_supports"] == 2
    assert intervention["first_support_max_gap_actions"] == 12
    assert intervention["global_cooldown_executed_actions"] == 4
    assert intervention["max_failure_records"] == 8
    assert intervention["max_nonempty_reads_per_episode"] == 5
    assert intervention["max_visible_chars_per_read"] == 240
    assert intervention["max_utf8_bytes_per_read"] == 480
    assert intervention["max_rendered_tokens_per_read"] == 100
    assert intervention["model_calls_added"] == 0
    assert intervention["guard_enabled"] is False
    assert intervention["action_override_count"] == intervention["forced_termination_count"] == 0


def test_source_closure_exact_and_no_generated_self_reference() -> None:
    assert len(contract.SOURCE_FILES) == len(set(contract.SOURCE_FILES))
    generated = {
        "evidence/a12/A12_STATIC_SOURCE_FREEZE.json",
        "evidence/a12/A12_OFFLINE_REPLAY_REPORT.json",
        "evidence/a12/A12_OFFLINE_ABLATION_REPORT.json",
        "evidence/a12/A12_ZERO_GENERATION_PREFLIGHT.json",
        "evidence/a12/A12_LIVE_SERVER_RECEIPT.json",
        "evidence/a12/A12_FINAL_RESULT.json",
    }
    assert generated.isdisjoint(contract.SOURCE_FILES)
    assert all("all A12" not in name and "etc." not in name for name in contract.SOURCE_FILES)


def test_source_freeze_payload_has_no_hash_cycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    for name in ("design.md", "core.py"):
        (root / name).write_text(name, encoding="utf-8")
    monkeypatch.setattr(contract, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(contract, "SOURCE_FILES", ("design.md", "core.py"))
    commit = "1" * 40
    payload = contract.source_freeze_payload(commit)
    unhashed = {"implementation_commit": commit, "files": payload["files"]}
    assert payload == {**unhashed, "payload_sha256": _canonical_sha(unhashed)}
    assert "whole_file_sha256" not in payload
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(contract, "REVIEW_COMMIT", commit)
    monkeypatch.setattr(
        contract.subprocess,
        "check_output",
        lambda command, **kwargs: commit if "rev-parse" in command else "",
    )
    monkeypatch.setattr(
        contract.subprocess,
        "run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0})(),
    )
    assert contract.validate_source_freeze(freeze_path) == payload


def test_preflight_and_receipt_use_identical_binding_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "source.py").write_text("source", encoding="utf-8")
    monkeypatch.setattr(contract, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(contract, "SOURCE_FILES", ("source.py",))
    commit = "2" * 40
    freeze = contract.source_freeze_payload(commit)
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    monkeypatch.setattr(contract, "REVIEW_COMMIT", commit)
    monkeypatch.setattr(
        contract.subprocess,
        "check_output",
        lambda command, **kwargs: commit if "rev-parse" in command else "",
    )
    monkeypatch.setattr(
        contract.subprocess,
        "run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0})(),
    )
    replay_path = tmp_path / "replay.json"
    replay_path.write_text(
        json.dumps(
            {
                "schema": contract.OFFLINE_REPLAY_SCHEMA,
                "status": "pass",
                "verdict": "A12_OFFLINE_REPLAY_PASS",
                "mechanism_id": contract.MECHANISM_ID,
                "experiment_id": contract.EXPERIMENT_ID,
                "formal_replay_executed": True,
                "generation_calls": 0,
                "errors": [],
                "live_generation_authorized": True,
                "formal_replay_gates": {
                    key: True for key in contract.FORMAL_REPLAY_GATE_NAMES
                },
                "episode_count": 27,
                "file_count": 1668,
                "total_bytes": 442138413,
                "reference_segment_count": 23,
                "a6_qualified_segment_count": 20,
            }
        ),
        encoding="utf-8",
    )
    preflight = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": commit,
        "source_freeze_payload_sha256": freeze["payload_sha256"],
        "offline_replay_sha256": contract.file_sha256(replay_path),
        "generation_calls": 0,
        "live_generation_authorized": True,
        "formal_replay_executed": True,
        "verdict": "A12_ZERO_GENERATION_PREFLIGHT_PASS",
        "errors": [],
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    command = ["python", "-m", "vllm.entrypoints.cli.main", "serve", contract.MODEL_REALPATH, "--served-model-name", contract.MODEL_ID]
    intent = {
        **{key: preflight[key] for key in ("implementation_commit", "source_freeze_payload_sha256", "offline_replay_sha256")},
        "preflight_sha256": contract.file_sha256(preflight_path),
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "process_cmdline": command,
    }
    intent_path = tmp_path / "intent.json"
    intent_path.write_text(json.dumps(intent), encoding="utf-8")
    receipt = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        **{key: intent[key] for key in contract.LIVE_BINDING_FIELDS if key in intent},
        "launch_intent_sha256": contract.file_sha256(intent_path),
        "process_pid": 12345,
        "process_cmdline": command,
        "host": "test-host",
        "port": contract.PORT,
        "vllm_version": "x",
        "torch_version": "x",
        "transformers_version": "x",
        "observed_served_model_ids": [contract.MODEL_ID],
        "qualification_timestamp": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    # The fixture has no actual vLLM process. Formal POSIX qualification keeps
    # the /proc check; this unit test exercises artifact/field binding only.
    monkeypatch.setattr(contract.os, "name", "nt")
    assert contract.validate_preflight_report(preflight_path, source_freeze_path=freeze_path, offline_replay_path=replay_path) == preflight
    validated = contract.validate_launch_receipt(receipt_path, preflight_path=preflight_path, source_freeze_path=freeze_path, offline_replay_path=replay_path, launch_intent_path=intent_path)
    assert validated == receipt
    drifted = dict(receipt)
    drifted["a12_preflight_hash"] = drifted.pop("preflight_sha256")
    receipt_path.write_text(json.dumps(drifted), encoding="utf-8")
    with pytest.raises(RuntimeError, match="preflight_sha256_drift"):
        contract.validate_launch_receipt(receipt_path, preflight_path=preflight_path, source_freeze_path=freeze_path, offline_replay_path=replay_path, launch_intent_path=intent_path)


def test_protocol_invalid_preflight_can_never_validate_as_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "source.py").write_text("source", encoding="utf-8")
    monkeypatch.setattr(contract, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(contract, "SOURCE_FILES", ("source.py",))
    commit = "a" * 40
    freeze = contract.source_freeze_payload(commit)
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    monkeypatch.setattr(contract, "REVIEW_COMMIT", commit)
    monkeypatch.setattr(
        contract.subprocess,
        "check_output",
        lambda command, **kwargs: commit if "rev-parse" in command else "",
    )
    monkeypatch.setattr(
        contract.subprocess,
        "run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0})(),
    )
    replay_path = tmp_path / "replay.json"
    replay_path.write_text(
        json.dumps(
            {
                "schema": contract.OFFLINE_REPLAY_SCHEMA,
                "status": "protocol_invalid",
                "generation_calls": 0,
                "errors": ["a12_theoretical_max_qualifiable_segments_below_20"],
                "live_generation_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    preflight = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PROTOCOL_INVALID",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": commit,
        "source_freeze_payload_sha256": freeze["payload_sha256"],
        "offline_replay_sha256": contract.file_sha256(replay_path),
        "generation_calls": 0,
        "live_generation_authorized": False,
        "formal_replay_executed": False,
        "errors": ["a12_theoretical_max_qualifiable_segments_below_20"],
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    with pytest.raises(RuntimeError, match="status_drift|preflight_errors_nonempty"):
        contract.validate_preflight_report(
            preflight_path,
            source_freeze_path=freeze_path,
            offline_replay_path=replay_path,
        )


def test_minimal_self_asserted_replay_cannot_authorize_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "source.py").write_text("source", encoding="utf-8")
    monkeypatch.setattr(contract, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(contract, "SOURCE_FILES", ("source.py",))
    commit = "b" * 40
    freeze = contract.source_freeze_payload(commit)
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    monkeypatch.setattr(contract, "REVIEW_COMMIT", commit)
    monkeypatch.setattr(
        contract.subprocess,
        "check_output",
        lambda command, **kwargs: commit if "rev-parse" in command else "",
    )
    monkeypatch.setattr(
        contract.subprocess,
        "run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0})(),
    )
    replay_path = tmp_path / "replay.json"
    replay_path.write_text(
        json.dumps({
            "schema": contract.OFFLINE_REPLAY_SCHEMA,
            "status": "pass",
            "verdict": "A12_PROTOCOL_INVALID",
            "generation_calls": 0,
            "errors": [],
            "live_generation_authorized": True,
        }),
        encoding="utf-8",
    )
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps({
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "verdict": "A12_PROTOCOL_INVALID",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": commit,
        "source_freeze_payload_sha256": freeze["payload_sha256"],
        "offline_replay_sha256": contract.file_sha256(replay_path),
        "generation_calls": 0,
        "live_generation_authorized": True,
        "formal_replay_executed": True,
        "errors": [],
    }), encoding="utf-8")
    with pytest.raises(RuntimeError, match="verdict|gate_vector|episode_count"):
        contract.validate_preflight_report(
            preflight_path,
            source_freeze_path=freeze_path,
            offline_replay_path=replay_path,
        )


def test_capability_gate_checks_reward_transport_and_boundaries() -> None:
    summaries = _valid_summaries()[:4]
    for summary in summaries:
        summary.update({"memory_added_model_calls": 0, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0})
    assert contract.preservation_report(summaries)["status"] == "pass"
    summaries[0]["transport_attempt_max"] = 2
    assert contract.preservation_report(summaries)["status"] == "fail"


def test_exact_19_accepts_bidirectionally_resolved_infrastructure_attempts() -> None:
    summaries = _valid_summaries()
    summaries[0]["resolves_invalid_episode_ids"] = ["invalid_0", "invalid_1"]
    invalid = [
        {"episode_id": "invalid_0", "task_name": contract.TASK_ORDER[0], "resolved_by_episode_id": "valid_00"},
        {"episode_id": "invalid_1", "task_name": contract.TASK_ORDER[0], "resolved_by_episode_id": "valid_00"},
    ]
    assert contract.exact_completion_errors(summaries, invalid, []) == []


def test_exact_19_rejects_one_way_links_wrong_task_and_third_invalid() -> None:
    summaries = _valid_summaries()
    summaries[0]["resolves_invalid_episode_ids"] = ["invalid_0", "invalid_1", "invalid_2"]
    invalid = [
        {"episode_id": f"invalid_{index}", "task_name": (contract.TASK_ORDER[1] if index == 0 else contract.TASK_ORDER[0]), "resolved_by_episode_id": "valid_00"}
        for index in range(3)
    ]
    errors = contract.exact_completion_errors(summaries, invalid, [])
    assert "infrastructure_invalid_attempt_limit_exceeded" in errors
    assert "invalid_replacement_task_mismatch" in errors
    invalid[0]["resolved_by_episode_id"] = "valid_01"
    errors = contract.exact_completion_errors(summaries, invalid, [])
    assert "invalid_replacement_bidirectional_link_mismatch" in errors


def test_exact_19_rejects_order_seed_reward_and_transport_drift() -> None:
    summaries = _valid_summaries()
    assert contract.exact_completion_errors(summaries, [], []) == []
    reversed_summaries = list(reversed(summaries))
    assert "exact_19_ordered_task_closure_failed" in contract.exact_completion_errors(reversed_summaries, [], [])
    summaries[0]["task_seed"] = -1
    summaries[1]["evaluator_reward"] = float("nan")
    summaries[2]["transport_attempt_max"] = 2
    errors = contract.exact_completion_errors(summaries, [], [])
    assert "task_seed_drift" in errors
    assert "invalid_valid_episode_summary" in errors
    assert "transport_attempt_max_not_one" in errors
