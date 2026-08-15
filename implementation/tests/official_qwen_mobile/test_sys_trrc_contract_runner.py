from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from raven_m.official_qwen_mobile import sys_trrc_contract as contract
from raven_m.official_qwen_mobile import sys_trrc_token_budget

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/scripts"))
from replay_sys_trrc_detector import collect_projection_inputs
from qualify_sys_trrc_server import verify_model_manifest


def _summary(task: str, *, trigger: int = 0, aux: int = 0, injection: int = 0) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    normal_call = {
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        "raven_meta": {"transport_attempts": 1, "latency_seconds": 0.2},
    }
    ticket_id = "inject_test_ticket"
    auxiliary = [{
        "model_call": {
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            "raven_meta": {"transport_attempts": 1, "latency_seconds": 0.1},
        },
        "commit": {"valid_output": True, "injection_text": "bounded advice",
                   "injection_ticket_id": ticket_id},
    }] if aux else []
    normal_injection = ({
        "ticket_id": ticket_id,
        "injection_commit": {"event": "normal_injection_committed",
                             "ticket_id": ticket_id, "transport_attempts": 1},
    } if injection else None)
    return {
        "task_name": task, "seed": contract.TASK_SEED, "success": True,
        "evaluator_reward": 1.0, "started_at": now, "finished_at": now,
        "normal_decision_call_count": 1, "aux_recovery_call_count": aux,
        "model_call_count": 1 + aux, "steps": [{"model_call": normal_call, "executed": True,
            "decision": {"canonical_action": {"type": "tap", "x": 0.5, "y": 0.5}},
            "recovery": {"normal_injection": normal_injection} if injection else None}],
        "auxiliary_model_call_attempts": auxiliary,
        "recovery_detector_cpu_seconds": 0.001,
        "recovery_projection_cpu_seconds": 0.002,
        "recovery_mechanism": {"state": {}, "counters": {"trigger_count": trigger,
            "aux_committed_count": aux, "injection_committed_count": injection},
            "post_injection_watches": [{"observed_actions": 1, "visible_change_seen": True,
                "anchor_relapse_seen": False}] if injection else []},
    }


def test_independent_bindings_and_frozen_gate_order() -> None:
    assert [contract.binding(x)["arm_id"] for x in ("base", "detector", "generic", "full")] == [
        "SYS-TRRC-R2-BASE", "SYS-TRRC-R2-DETECTOR",
        "SYS-TRRC-R2-GENERIC", "SYS-TRRC-R2-FULL"
    ]
    assert contract.FULL_TASK_ORDER[:7] == contract.CAPABILITY_GATE_TASKS
    assert len(contract.FULL_TASK_ORDER) == 19
    assert contract.CONTROL_TASK_ORDER == ("ExpenseDeleteMultiple2", "BrowserMultiply")
    assert [len(contract.STAGE_TASKS[x]) for x in ("l1", "l2", "l3", "l4")] == [1, 6, 7, 19]
    assert contract.CAMPAIGN_INVOCATION_ORDER == (
        ("base", "l1"), ("detector", "l1"), ("generic", "l1"), ("full", "l1"),
        ("generic", "l2"), ("full", "l2"),
        ("base", "l3"), ("detector", "l3"), ("generic", "l3"), ("full", "l3"),
        ("generic", "l4"), ("full", "l4"),
    )


def test_model_manifest_closes_exact_supplemental_files(tmp_path: Path) -> None:
    model = tmp_path / "model"
    model.mkdir()
    payload = b"model-config"
    (model / "config.json").write_bytes(payload)
    for name in (".gitattributes", "README.md", "merges.txt"):
        (model / name).write_text(name, encoding="utf-8")
    manifest = tmp_path / "model.sha256"
    manifest.write_text(
        f"{sha256(payload).hexdigest()}  config.json\n", encoding="utf-8"
    )
    report = verify_model_manifest(model, manifest)
    assert report["status"] == "PASS"
    assert report["supplemental_file_count"] == 3
    assert [row["path"] for row in report["supplemental_files"]] == [
        ".gitattributes", "README.md", "merges.txt",
    ]
    (model / "unlisted.json").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="directory closure"):
        verify_model_manifest(model, manifest)


def test_all_twelve_stage_invocations_have_exact_closure() -> None:
    expected = {
        ("base", "l1"): (1, None, "stage_l1_complete"),
        ("detector", "l1"): (1, None, "stage_l1_complete"),
        ("generic", "l1"): (1, None, "stage_l1_complete"),
        ("full", "l1"): (1, None, "stage_l1_complete"),
        ("generic", "l2"): (6, "stage_l1_complete", "stage_l2_complete"),
        ("full", "l2"): (6, "stage_l1_complete", "stage_l2_complete"),
        ("base", "l3"): (2, "stage_l1_complete", "control_complete"),
        ("detector", "l3"): (2, "stage_l1_complete", "control_complete"),
        ("generic", "l3"): (7, "stage_l2_complete", "stage_l3_complete"),
        ("full", "l3"): (7, "stage_l2_complete", "stage_l3_complete"),
        ("generic", "l4"): (19, "stage_l3_complete", "complete"),
        ("full", "l4"): (19, "stage_l3_complete", "complete"),
    }
    for invocation in contract.CAMPAIGN_INVOCATION_ORDER:
        closure = contract.stage_contract(*invocation)
        count, prior, completion = expected[invocation]
        assert len(closure["tasks"]) == count
        assert closure["required_prior_status"] == prior
        assert closure["completion_status"] == completion
    for mode, forbidden in (("base", "l2"), ("base", "l4"),
                            ("detector", "l2"), ("detector", "l4")):
        with pytest.raises(RuntimeError):
            contract.stage_contract(mode, forbidden)


def test_campaign_pending_infrastructure_attempt_does_not_consume_ordinal(
    tmp_path: Path,
) -> None:
    payload = {
        "schema": "sys_trrc_campaign_ledger_v1",
        "protocol_id": contract.PROTOCOL_ID,
        "campaign_id": "campaign-test",
        "planned_order": [list(item) for item in contract.CAMPAIGN_INVOCATION_ORDER],
        "entries": [],
        "pending_attempt": {
            "ordinal": 1, "mode": "base", "stage": "l1",
            "suite_dir": None, "started_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    ledger = {**payload, "content_sha256": contract.content_sha256(payload)}
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    assert contract.validate_campaign_ledger(path)["entries"] == []
    ledger["pending_attempt"]["stage"] = "l3"
    ledger["content_sha256"] = contract.content_sha256(ledger)
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(RuntimeError, match="pending invocation"):
        contract.validate_campaign_ledger(path)


def test_campaign_same_arm_later_stage_keeps_earlier_snapshot_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    preflight = tmp_path / "preflight.json"
    preflight.write_text('{"content_sha256":"test"}\n', encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    entries = []
    previous = None
    invocations = (("generic", "l1"), ("generic", "l2"))
    monkeypatch.setattr(contract, "CAMPAIGN_INVOCATION_ORDER", invocations)
    for ordinal, (mode, stage) in enumerate(invocations, start=1):
        status = contract.stage_contract(mode, stage)["completion_status"]
        checkpoint_payload = {
            "schema": contract.CHECKPOINT_SCHEMA,
            "prospective_arm": f"sys_trrc_{mode}",
            "experiment_id": contract.binding(mode)["experiment_id"],
            "mechanism_id": contract.MECHANISM_ID,
            "sys_trrc_stage": stage,
            "status": status,
            "run_signature_sha256": f"{ordinal}" * 64,
        }
        checkpoint = {**checkpoint_payload,
                      "content_sha256": contract.content_sha256(checkpoint_payload)}
        formal_status = status.upper()
        result_payload = {"status": formal_status}
        result = {**result_payload, "content_sha256": contract.content_sha256(result_payload)}
        checkpoint_path = artifacts / f"{ordinal}_checkpoint.json"
        result_path = artifacts / f"{ordinal}_result.json"
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        result_path.write_text(json.dumps(result), encoding="utf-8")
        entry_payload = {
            "ordinal": ordinal, "mode": mode, "stage": stage,
            "suite_dir": str(suite), "checkpoint_status": status,
            "result_status": formal_status,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_path_sha256": contract.file_sha256(checkpoint_path),
            "result_path": str(result_path),
            "result_path_sha256": contract.file_sha256(result_path),
            "preflight_path": str(preflight),
            "preflight_path_sha256": contract.file_sha256(preflight),
            "run_signature_sha256": checkpoint["run_signature_sha256"],
            "return_code": 0, "advancement_authorized": True,
            "previous_entry_sha256": previous,
        }
        entry = {**entry_payload,
                 "entry_sha256": contract.canonical_sha256(entry_payload)}
        entries.append(entry)
        previous = entry["entry_sha256"]
    # Simulate the later stage overwriting the suite's live top-level files.
    (suite / "checkpoint.json").write_text("later live checkpoint", encoding="utf-8")
    (suite / "sys_trrc_result.json").write_text("later live result", encoding="utf-8")
    payload = {
        "schema": "sys_trrc_campaign_ledger_v1",
        "protocol_id": contract.PROTOCOL_ID, "campaign_id": "campaign-test",
        "planned_order": [list(item) for item in contract.CAMPAIGN_INVOCATION_ORDER],
        "entries": entries, "pending_attempt": None,
    }
    ledger = {**payload, "content_sha256": contract.content_sha256(payload)}
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    monkeypatch.setattr(contract, "validate_result_payload", lambda *args, **kwargs: None)
    assert len(contract.validate_campaign_ledger(path)["entries"]) == 2


def test_partial_result_marks_protocol_not_run_and_separates_aux_cost() -> None:
    summaries = [_summary(name) for name in contract.PRESERVATION_TASKS]
    summaries.append(_summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1))
    preflight = {"implementation_commit": "a" * 40, "content_sha256": "b" * 64,
                 "source_freeze_content_sha256": "c" * 64}
    result = contract.result_payload(
        mode="full", status="TERMINAL_SCIENTIFIC_FAILURE_TEST", summaries=summaries,
        invalid_attempts=[], lifecycle_errors=[], run_signature_sha256="d" * 64,
        preflight=preflight, preflight_file_sha256="e" * 64,
        receipt_file_sha256s=["f" * 64], checkpoint_sha256="1" * 64,
    )
    assert len(result["closure"]["not_run_by_protocol"]) == 12
    assert result["performance"]["model_calls"] == {"normal": 7, "aux": 1, "combined": 8}
    assert result["performance"]["token_usage"]["aux"]["total_tokens"] == 7
    assert result["performance"]["transport"]["all_single_attempt"] is True
    assert result["gates"]["activation"]["status"] == "pass"
    assert result["content_sha256"] == contract.content_sha256(result)


def test_full_partial_and_terminal_accuracy_are_not_control_labels() -> None:
    preflight = {"implementation_commit": "a" * 40, "content_sha256": "b" * 64,
                 "source_freeze_content_sha256": "c" * 64}
    common = dict(
        mode="full", summaries=[_summary(contract.PRESERVATION_TASKS[0])],
        invalid_attempts=[], lifecycle_errors=[], run_signature_sha256="d" * 64,
        preflight=preflight, preflight_file_sha256="e" * 64,
        receipt_file_sha256s=["f" * 64], checkpoint_sha256="1" * 64,
        campaign_stage="l1",
    )
    partial = contract.result_payload(status="STAGE_L1_COMPLETE", **common)
    assert partial["verdicts"]["accuracy"] == "NOT_YET_ADJUDICATED"
    terminal = contract.result_payload(
        status="TERMINAL_SCIENTIFIC_FAILURE_STOPPED_PRESERVATION_GATE_FAILURE",
        **common,
    )
    assert terminal["verdicts"]["accuracy"] == "TERMINAL_FAIL"


def test_cost_closure_rejects_missing_or_invalid_measured_costs() -> None:
    summary = _summary(contract.PRESERVATION_TASKS[0])
    assert contract.cost_accounting_errors([summary], "generic") == []
    summary["steps"][0]["model_call"]["usage"]["total_tokens"] = 99
    summary["steps"][0]["model_call"]["raven_meta"]["latency_seconds"] = -1
    del summary["recovery_projection_cpu_seconds"]
    errors = contract.cost_accounting_errors([summary], "generic")
    assert "model_cost_boundary" in errors
    assert "recovery_projection_cpu_seconds_missing" in errors


def test_base_legacy_no_policy_call_count_has_explicit_fallback() -> None:
    summary = _summary(contract.PRESERVATION_TASKS[0])
    summary.pop("normal_decision_call_count")
    summary.pop("aux_recovery_call_count")
    assert "call_accounting" not in contract.cost_accounting_errors([summary], "base")


def test_result_validator_fails_closed_on_checkpoint_tamper(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    run_signature = {"test": "sys-trrc"}
    run_signature_sha = contract.canonical_sha256(run_signature)
    (tmp_path / "run_signature.json").write_text(
        json.dumps(run_signature) + "\n", encoding="utf-8"
    )
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text('{"test":"preflight"}\n', encoding="utf-8")
    checkpoint_payload = {
        "schema": contract.CHECKPOINT_SCHEMA,
        "run_signature_sha256": run_signature_sha,
        "prospective_arm": "sys_trrc_detector",
        "experiment_id": contract.binding("detector")["experiment_id"],
        "mechanism_id": contract.MECHANISM_ID,
        "sys_trrc_stage": None,
        "valid_summaries": [],
        "invalid_attempts": [],
        "lifecycle_errors": [],
        "sys_trrc_valid_entries": [],
        "live_server_receipt_sha256s": ["f" * 64],
    }
    checkpoint_payload["content_sha256"] = contract.content_sha256(checkpoint_payload)
    checkpoint.write_text(json.dumps(checkpoint_payload) + "\n", encoding="utf-8")
    preflight = {"content_sha256": "b" * 64, "source_freeze_content_sha256": "c" * 64}
    result = contract.result_payload(
        mode="detector", status="RUNNING_PARTIAL", summaries=[], invalid_attempts=[],
        lifecycle_errors=[], run_signature_sha256=run_signature_sha, preflight=preflight,
        preflight_file_sha256=contract.file_sha256(preflight_path),
        receipt_file_sha256s=["f" * 64],
        checkpoint_sha256=contract.file_sha256(checkpoint),
    )
    contract.validate_result_payload(result, mode="detector", checkpoint_path=checkpoint,
                                     run_signature_sha256=run_signature_sha, preflight=preflight,
                                     preflight_path=preflight_path)
    checkpoint.write_text('{"tampered":true}\n', encoding="utf-8")
    try:
        contract.validate_result_payload(result, mode="detector", checkpoint_path=checkpoint,
                                         run_signature_sha256=run_signature_sha, preflight=preflight,
                                         preflight_path=preflight_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("tampered checkpoint was accepted")


def test_result_validator_accepts_artifactless_suite_lifecycle_attempt(
    tmp_path: Path,
) -> None:
    run_signature = {"test": "lifecycle"}
    run_signature_sha = contract.canonical_sha256(run_signature)
    (tmp_path / "run_signature.json").write_text(json.dumps(run_signature), encoding="utf-8")
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text('{"test":"preflight"}\n', encoding="utf-8")
    lifecycle_error = {"stage": "env.close", "type": "RuntimeError", "message": "x"}
    invalid = {"reason": "suite_lifecycle_error", "error": lifecycle_error}
    checkpoint_payload = {
        "schema": contract.CHECKPOINT_SCHEMA, "status": "stopped_invalid_episode",
        "run_signature_sha256": run_signature_sha,
        "prospective_arm": "sys_trrc_detector",
        "experiment_id": contract.binding("detector")["experiment_id"],
        "mechanism_id": contract.MECHANISM_ID, "sys_trrc_stage": "l1",
        "valid_summaries": [], "invalid_attempts": [invalid],
        "lifecycle_errors": [lifecycle_error], "sys_trrc_valid_entries": [],
        "live_server_receipt_sha256s": ["f" * 64],
    }
    checkpoint = {**checkpoint_payload,
                  "content_sha256": contract.content_sha256(checkpoint_payload)}
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    preflight = {"content_sha256": "b" * 64, "source_freeze_content_sha256": "c" * 64}
    result = contract.result_payload(
        mode="detector", status="INFRASTRUCTURE_STOPPED_INVALID_EPISODE",
        summaries=[], invalid_attempts=[invalid], lifecycle_errors=[lifecycle_error],
        run_signature_sha256=run_signature_sha, preflight=preflight,
        preflight_file_sha256=contract.file_sha256(preflight_path),
        receipt_file_sha256s=["f" * 64],
        checkpoint_sha256=contract.file_sha256(checkpoint_path), campaign_stage="l1",
    )
    contract.validate_result_payload(
        result, mode="detector", checkpoint_path=checkpoint_path,
        run_signature_sha256=run_signature_sha, preflight=preflight,
        preflight_path=preflight_path,
    )


def test_mode_specific_activation_qualification() -> None:
    assert contract.activation_report([_summary(contract.ACTIVATION_TASK)], "base")["qualification"] == "VALID_SEALED_BROWSER_EPISODE"
    assert contract.activation_report([_summary(contract.ACTIVATION_TASK, trigger=1)], "detector")["qualification"] == "DETECTOR_ACTIVATED"
    delivered = _summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1)
    assert contract.activation_report([delivered], "generic")["qualification"] == "DELIVERED"
    assert contract.activation_report([delivered], "full")["qualification"] == "QUALIFYING_RECOVERY_SUCCESS"
    delivered["recovery_mechanism"]["post_injection_watches"][0]["anchor_relapse_seen"] = True
    assert contract.activation_report([delivered], "full")["status"] == "fail"


def test_activation_requires_real_aux_injection_chain_and_full_success() -> None:
    malformed = _summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1)
    malformed["auxiliary_model_call_attempts"][0]["commit"]["valid_output"] = False
    assert contract.activation_report([malformed], "generic")["status"] == "fail"

    wrong_ticket = _summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1)
    wrong_ticket["steps"][0]["recovery"]["normal_injection"]["ticket_id"] = "wrong"
    assert contract.activation_report([wrong_ticket], "generic")["status"] == "fail"

    no_execution = _summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1)
    no_execution["steps"][0]["executed"] = False
    assert contract.activation_report([no_execution], "generic")["qualification"] == "DELIVERED"
    assert contract.activation_report([no_execution], "full")["status"] == "fail"

    failed_task = _summary(contract.ACTIVATION_TASK, trigger=1, aux=1, injection=1)
    failed_task["success"] = False
    failed_task["evaluator_reward"] = 0.0
    assert contract.activation_report([failed_task], "generic")["qualification"] == "DELIVERED"
    assert contract.activation_report([failed_task], "full")["status"] == "fail"


def test_materialized_projection_package_is_self_bound() -> None:
    package = ROOT / "evidence/sys_trrc/token_projection_inputs"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS" and manifest["generation_calls"] == 0
    assert manifest["content_sha256"] == contract.content_sha256(manifest)
    assert len(manifest["opportunities"]) == 8
    for row in manifest["opportunities"]:
        assert sha256((package / row["png_file"]).read_bytes()).hexdigest() == row["png_sha256"]
        for mode in ("generic", "full"):
            item = row["modes"][mode]
            assert sha256((item["system_prompt"] + "\n\0\n" + item["user_prompt"]).encode()).hexdigest() == item["request_text_sha256"]


def test_projection_closure_replays_every_manifest_row_and_fails_on_receipt_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_evidence = ROOT / "evidence/sys_trrc"
    target_evidence = tmp_path / "evidence/sys_trrc"
    target_evidence.mkdir(parents=True)
    shutil.copy2(source_evidence / "SYS_TRRC_R2_DETECTOR_REPLAY.json", target_evidence)
    shutil.copytree(source_evidence / "token_projection_inputs",
                    target_evidence / "token_projection_inputs")

    class FakeProjector:
        def __init__(self, model_path: Path, *, expected_revision: str) -> None:
            self.processor_files_sha256 = {
                "chat_template.json": "1" * 64,
                "tokenizer.json": "2" * 64,
                "preprocessor_config.json": "3" * 64,
            }

        def __call__(self, system_prompt: str, user_prompt: str,
                     screenshot_path: str) -> dict:
            screenshot_sha = sha256(Path(screenshot_path).read_bytes()).hexdigest()
            return {
                "schema": sys_trrc_token_budget.PROJECTION_SCHEMA,
                "model_revision": contract.MODEL_REVISION,
                "processor_files_sha256": dict(self.processor_files_sha256),
                "messages_sha256": sha256((system_prompt + user_prompt).encode()).hexdigest(),
                "current_screenshot_sha256": screenshot_sha,
                "current_image_size": [1080, 2400],
                "content_order": ["system:text", "user:text", "user:image"],
                "add_generation_prompt": True,
                "image_grid_thw": [[1, 120, 54]],
                "exact_multimodal_input_tokens": 1000,
            }

    monkeypatch.setattr(contract, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(sys_trrc_token_budget, "ExactQwenMultimodalTokenProjector", FakeProjector)
    evidence = contract._recomputed_projection_evidence()
    assert len(evidence["opportunities"]) == 8
    assert all(set(row["modes"]) == {"generic", "full"} for row in evidence["opportunities"])
    assert evidence["maximum_projected_total_tokens"] == 1192

    manifest_path = target_evidence / "token_projection_inputs/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["opportunities"][0]["modes"]["full"]["receipt_id"] = "tampered"
    manifest["content_sha256"] = contract.content_sha256(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="projection_receipt_binding"):
        contract._recomputed_projection_evidence()


def test_preflight_validator_rejects_any_nested_projection_row_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_config = contract.expected_config("generic")
    config_path = tmp_path / contract.MODE_BINDINGS["generic"]["config"]
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(expected_config) + "\n", encoding="utf-8")
    replay_path = tmp_path / "evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json"
    replay_path.parent.mkdir(parents=True)
    replay = {"content_sha256": "4" * 64}
    replay_path.write_text(json.dumps(replay), encoding="utf-8")
    projection = {
        "schema": "sys_trrc_eight_opportunity_token_projection_v1",
        "source_suite": "frozen",
        "opportunity_count": 8,
        "processor_files_sha256": {"tokenizer.json": "5" * 64},
        "maximum_projected_total_tokens": 100,
        "opportunities": [{"episode_id": f"ep{i}", "eligible_request_step": i,
                           "modes": {"generic": {"exact_multimodal_input_tokens": 1},
                                     "full": {"exact_multimodal_input_tokens": 2}}}
                          for i in range(8)],
    }
    commit = "a" * 40
    freeze_payload = {"schema": "sys_trrc_source_freeze_v1",
                      "implementation_commit": commit, "files": {}}
    freeze = {**freeze_payload, "content_sha256": contract.content_sha256(freeze_payload)}
    freeze_path = tmp_path / "evidence/sys_trrc/SYS_TRRC_GENERIC_SOURCE_FREEZE.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    arm = contract.MODE_BINDINGS["generic"]
    payload = {
        "schema": contract.PREFLIGHT_SCHEMA, "status": "PASS", "errors": [],
        "generation_calls": 0, "live_generation_authorized": True,
        "protocol_id": contract.PROTOCOL_ID, "system_id": contract.SYSTEM_ID,
        "mode": "generic", "arm_id": arm["arm_id"],
        "experiment_id": arm["experiment_id"], "implementation_commit": commit,
        "source_freeze_content_sha256": contract.content_sha256(freeze_payload),
        "config_content_sha256": contract.canonical_sha256(expected_config),
        "checks": {"source_files": {},
                   "detector_replay_content_sha256": replay["content_sha256"],
                   "exact_protocol_prompt_sha256s": {
                       key: sha256(value.encode()).hexdigest()
                       for key, value in {
                           "common": contract.EXPECTED_COMMON_AUX_SYSTEM_TEMPLATE,
                           "generic": contract.EXPECTED_GENERIC_ROLE,
                           "full": contract.EXPECTED_FULL_ROLE,
                           "wrapper": contract.EXPECTED_ADVICE_TEMPLATE,
                       }.items()
                   },
                   "required_recovery_config": dict(expected_config["recovery"]),
                   "focused_tests": {"returncode": 0},
                   "eight_opportunity_token_projection": json.loads(json.dumps(projection))},
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    report_path = tmp_path / "preflight.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(contract, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(contract, "SOURCE_FILES", ())
    monkeypatch.setattr(contract, "_recomputed_projection_evidence", lambda: projection)
    monkeypatch.setattr(contract.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    contract.validate_preflight_report(report_path, expected_mode="generic")

    report["checks"]["eight_opportunity_token_projection"]["opportunities"][3]["modes"]["full"]["exact_multimodal_input_tokens"] = 3
    report["content_sha256"] = contract.content_sha256(report)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(RuntimeError, match="exact_closure"):
        contract.validate_preflight_report(report_path, expected_mode="generic")


def test_runner_contains_aux_timeout_policy_and_recovery_hook() -> None:
    root = Path(__file__).resolve().parents[2]
    runner = (root / "scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    controller = (root / "src/raven_m/official_qwen_mobile/controller.py").read_text(encoding="utf-8")
    assert 'recovery_policy=recovery_policy' in runner
    assert 'request_timeout_seconds=60.0' in controller
    assert 'remaining_native_decision_slots' in controller
    assert 'sys_trrc_result.json' in runner
    assert '--sys-trrc-stage' in runner
    assert 'stage skipping is forbidden' in runner


@pytest.mark.skipif(
    not (ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981").is_dir(),
    reason="frozen A1-R2 development suite unavailable",
)
def test_collects_exact_eight_generic_full_projection_inputs() -> None:
    suite = ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
    generic = collect_projection_inputs(suite, "generic")
    full = collect_projection_inputs(suite, "full")
    assert len(generic) == len(full) == 8
    assert [x["episode_id"] for x in generic] == [x["episode_id"] for x in full]
    for g, f in zip(generic, full, strict=True):
        assert Path(g["screenshot_path"]).is_file()
        assert g["screenshot_sha256"] == f["screenshot_sha256"]
        assert g["eligible_request_step"] == f["eligible_request_step"]
        assert g["system_prompt"] != f["system_prompt"]
        assert g["request_text_sha256"] != f["request_text_sha256"]
