from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile import enriched_diagnostic_contract as contract


ROOT = Path(__file__).resolve().parents[3]


def _load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_manifest_is_exact_common_six_and_preserves_parent_instances() -> None:
    diagnostic = contract.load_manifest()
    parent = _load("implementation/configs/androidworld_hard_v2_instances.json")
    parent_by_key = {
        (item["task_class"], item["task_seed"]): item
        for item in parent["instances"]
    }
    assert tuple(item["task_class"] for item in diagnostic["instances"]) == contract.TASKS
    assert len(diagnostic["instances"]) == 6
    for item in diagnostic["instances"]:
        assert item == parent_by_key[(item["task_class"], item["task_seed"])]


def test_all_three_offline_sources_support_every_common_task() -> None:
    common = set(contract.TASKS)
    a10 = _load("evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json")
    a11 = _load("evidence/a11/A11_OFFLINE_REPLAY_REPORT.json")
    a12 = _load("evidence/a12/A12_REFERENCE_SEGMENTS.json")
    for report in (a10, a11):
        active = {
            item["task_name"] for item in report["episodes"]
            if item.get("role") == "a6" and int(item.get("nonempty_read_count") or 0) > 0
        }
        assert common <= active
    strict = {
        item["task_name_audit_only"] for item in a12["segments"]
        if item.get("independently_valid_for_a12") is True
    }
    assert common <= strict


def test_diagnostic_identity_is_new_but_source_mechanisms_are_unchanged() -> None:
    assert contract.ARM_ORDER == ("a10v2", "a11", "a12")
    experiment_ids = {item["experiment_id"] for item in contract.ARM_BINDINGS.values()}
    assert len(experiment_ids) == 3
    assert all("DIAG6" in value for value in experiment_ids)
    assert contract.ARM_BINDINGS["a10v2"]["source_mechanism_id"] == "a10_v2_evidence_matured_obligation_branch_frontier_v2"
    assert contract.ARM_BINDINGS["a11"]["source_mechanism_id"] == "a11_confirmed_route_contraction_ecobf_v1"
    assert contract.ARM_BINDINGS["a12"]["source_mechanism_id"] == "a12_minimal_action_divergence_memory_v1"


def _valid_preflight(commit: str) -> dict:
    return {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "pass",
        "protocol_id": contract.PROTOCOL_ID,
        "parent_commit": contract.PARENT_COMMIT,
        "implementation_commit": commit,
        "generation_calls": 0,
        "diagnostic_live_authorized": True,
        "formal_arm_status_repaired": False,
        "manifest_sha256": contract.file_sha256(contract.MANIFEST_PATH),
        "source_sha256": contract.source_hashes(),
        "evidence_sha256": contract.evidence_hashes(),
        "task_order": list(contract.TASKS),
        "arm_order": list(contract.ARM_ORDER),
        "arm_bindings": contract.ARM_BINDINGS,
        "checks": {
            "six_task_manifest_exact": True,
            "a10v2_common_six_offline_reads": True,
            "a11_common_six_offline_reads": True,
            "a12_common_six_strict_opportunities": True,
            "source_mechanisms_unchanged": True,
            "single_transport_policy": True,
            "zero_extra_model_calls": True,
            "no_guard_or_action_override": True,
            "diagnostic_not_formal_repair": True,
            "targeted_tests_passed": True,
        },
        "errors": [],
    }


def test_preflight_is_fail_closed_and_cannot_repair_formal_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "b" * 40
    monkeypatch.setattr(contract, "_git", lambda *args: "" if args[0] == "status" else commit)
    monkeypatch.setattr(
        contract.subprocess,
        "run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0})(),
    )
    path = tmp_path / "preflight.json"
    report = _valid_preflight(commit)
    path.write_text(json.dumps(report), encoding="utf-8")
    assert contract.validate_preflight_report(path) == report
    report["formal_arm_status_repaired"] = True
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(RuntimeError, match="formal_arm_status_repaired_drift"):
        contract.validate_preflight_report(path)


def test_receipt_binds_exact_preflight_and_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This unit test exercises the immutable receipt fields only. Live POSIX
    # process binding is covered by qualification and deployment validation.
    monkeypatch.setattr(contract.os, "name", "nt")
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text("{}", encoding="utf-8")
    preflight = {"implementation_commit": "c" * 40}
    monkeypatch.setattr(contract, "validate_preflight_report", lambda path: preflight)
    receipt = {
        "schema": contract.RECEIPT_SCHEMA,
        "status": "pass",
        "protocol_id": contract.PROTOCOL_ID,
        "generation_calls": 0,
        "preflight_sha256": contract.file_sha256(preflight_path),
        "implementation_commit": preflight["implementation_commit"],
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "process_pid": 12345,
        "process_cmdline": ["python", "vllm", "serve", contract.MODEL_REALPATH],
        "port": contract.PORT,
        "packages": {"vllm": "x", "torch": "x", "transformers": "x"},
        "observed_served_model_ids": [contract.MODEL_ID],
        "qualification_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    assert contract.validate_launch_receipt(path, preflight_path=preflight_path) == receipt
    receipt["generation_calls"] = 1
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(RuntimeError, match="generation_calls_drift"):
        contract.validate_launch_receipt(path, preflight_path=preflight_path)


def test_runner_has_separate_diagnostic_path_and_never_uses_formal_flags() -> None:
    runner = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "implementation/scripts/run_enriched_memory_diagnostic.py").read_text(encoding="utf-8")
    assert '"--enriched-memory-diagnostic"' in runner
    assert "formal_arm_status_repaired" in runner
    assert "_diag6_completion_errors" in runner
    assert '"--diagnostic"' in wrapper
    assert "--a10-v2-emobf" not in wrapper
    assert "--a11-crc-ecobf" not in wrapper
    assert "--a12-madm" not in wrapper


def test_source_closure_is_exact_and_excludes_generated_runtime_artifacts() -> None:
    assert contract.source_hashes()
    assert not any("PREFLIGHT.json" in name for name in contract.SOURCE_FILES)
    assert not any("RECEIPT.json" in name for name in contract.SOURCE_FILES)
    assert not any("LAUNCH_INTENT.json" in name for name in contract.SOURCE_FILES)
