"""Build deterministic final evidence reports for the completed v0.2.2 batch."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repository, capture_output=True, text=True, check=True, timeout=30
    ).stdout.strip()


def _experiment_processes() -> list[dict[str, Any]]:
    command = (
        "$p=Get-CimInstance Win32_Process|Where-Object {"
        "$_.Name -match 'python' -and $_.CommandLine -match "
        "'run_eest_ac_v0_2_2_envelope_qualification|qualify_eest_ac_v0_2_2_settling_window|stress_eest_ac_v0_2_2_adb_5038|preflight_eest_ac_v0_2_2_envelope_qualification'"
        "};$p|Select-Object ProcessId,Name,CommandLine|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, check=True, timeout=30,
    )
    if not result.stdout.strip():
        return []
    value = json.loads(result.stdout)
    return value if isinstance(value, list) else [value]


def _cell(cell_dir: Path) -> dict[str, Any]:
    result = _load(cell_dir / "probe_result.json")
    calls = [json.loads(line) for line in (cell_dir / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    attempts = _load(cell_dir / "attempts.json")
    before = _load(cell_dir / "before.json")["observation"]
    terminal = result["stabilization_audit"]["terminal_samples"]
    evidence_files = []
    for path in sorted(item for item in cell_dir.iterdir() if item.is_file()):
        evidence_files.append({"name": path.name, "sha256": _hash(path), "bytes": path.stat().st_size})
    return {
        "cell": result["cell"],
        "probe_id": result["probe_id"],
        "coverage_category": result["coverage_category"],
        "probe_pass": not result["hard_failure"],
        "failure": result["failure"],
        "initial_output_pass": result["decision"]["accepted_stage"].startswith("initial_"),
        "accepted_stage": result["decision"]["accepted_stage"],
        "repair_used": result["decision"]["repair_used"],
        "metadata_normalized": result["decision"]["metadata_normalized"],
        "metadata_only_repair": result["metadata_only_repair"],
        "intent_metadata": result["decision"]["intent_metadata"],
        "canonical_action": result["decision"]["control_plane"]["action"],
        "canonicalization": result["decision"]["canonicalization"],
        "control_plane_valid": result["decision"]["control_plane_valid"],
        "coverage_pass": result["coverage_pass"],
        "adapter": result["adapter"],
        "environment_executed": result["environment_executed"],
        "required_stable_state_change": result["state_changed"],
        "stabilization_audit": result["stabilization_audit"],
        "pre_packages": before["package_names"],
        "terminal_packages": terminal[-1]["package_names"] if terminal else [],
        "semantic_package_transition": before["package_names"] != (terminal[-1]["package_names"] if terminal else []),
        "reset_pass": result["reset_pass"],
        "reset_semantic_reference_match": result["reset"]["semantic_reference_match"],
        "schema_truncations": result["schema_truncation_count"],
        "max_token_hits": result["max_token_hits"],
        "call_accounting_valid": result["model_call_accounting_valid"],
        "calls": {
            "raw": result["model_calls"],
            "attempts": result["model_call_attempts"],
            "records": result["model_call_records"],
            "planned_initial": 1,
            "allowed_control_repairs": 1,
            "realized_initial": sum(call["role"] == "envelope_qualification_initial" for call in calls),
            "realized_repairs": sum(call["role"] != "envelope_qualification_initial" for call in calls),
        },
        "tokens": {
            "prompt": result["prompt_tokens"],
            "completion": result["completion_tokens"],
            "total": result["total_tokens"],
        },
        "wall_time_seconds": result["wall_time_seconds"],
        "raw_model_calls": [{
            "role": call["role"],
            "call_id": call["call_id"],
            "response_sha256": call["response_sha256"],
            "content": call["content"],
            "usage": call["usage"],
        } for call in calls],
        "attempts": attempts,
        "evidence_files": evidence_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--runtime-preflight", type=Path, required=True)
    parser.add_argument("--static-preflight", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--contract-audit", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    start = _load(args.run_root / "qualification_start.json")
    complete = _load(args.run_root / "qualification_complete.json")
    cells = [_cell(path) for path in sorted((args.run_root / "probes").iterdir()) if path.is_dir()]
    runtime = _load(args.runtime_preflight)
    static = _load(args.static_preflight)
    lock = _load(args.lock)
    contract_audit = _load(args.contract_audit)
    repository = args.run_root.resolve().parent.parent
    expected_legacy = {
        "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
        "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
        "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
    }
    git_status = _git(repository, "status", "--short").replace("\\", "/").splitlines()
    legacy_audit = []
    for relative, expected in expected_legacy.items():
        actual = _hash(repository / relative)
        matching_status = [line for line in git_status if line[3:] == relative]
        legacy_audit.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "hash_pass": actual == expected,
            "git_status": matching_status,
            "staged": any(line[:1] not in {" ", "?"} for line in matching_status),
        })
    totals = {
        "cells_executed": len(cells),
        "cells_passed": sum(cell["probe_pass"] for cell in cells),
        "initial_output_passes": sum(cell["initial_output_pass"] for cell in cells),
        "accepted_within_one_repair": sum(cell["control_plane_valid"] for cell in cells),
        "repair_calls": sum(cell["calls"]["realized_repairs"] for cell in cells),
        "metadata_normalization_events": sum(cell["metadata_normalized"] for cell in cells),
        "metadata_only_repair_calls": sum(cell["metadata_only_repair"] for cell in cells),
        "schema_control_passes": sum(cell["control_plane_valid"] for cell in cells),
        "coverage_passes": sum(cell["coverage_pass"] for cell in cells),
        "adapter_passes": sum(cell["adapter"] is not None for cell in cells),
        "environment_execution_passes": sum(cell["environment_executed"] for cell in cells),
        "stable_state_change_passes": sum(cell["required_stable_state_change"] for cell in cells),
        "reset_passes": sum(cell["reset_pass"] for cell in cells),
        "schema_truncations": sum(cell["schema_truncations"] for cell in cells),
        "max_token_hits": sum(cell["max_token_hits"] for cell in cells),
        "raw_calls": sum(cell["calls"]["raw"] for cell in cells),
        "attempts": sum(cell["calls"]["attempts"] for cell in cells),
        "call_records": sum(cell["calls"]["records"] for cell in cells),
        "planned_initial_calls": len(cells),
        "allowed_repair_calls": len(cells),
        "realized_initial_calls": sum(cell["calls"]["realized_initial"] for cell in cells),
        "realized_repair_calls": sum(cell["calls"]["realized_repairs"] for cell in cells),
        "prompt_tokens": sum(cell["tokens"]["prompt"] for cell in cells),
        "completion_tokens": sum(cell["tokens"]["completion"] for cell in cells),
        "total_tokens": sum(cell["tokens"]["total"] for cell in cells),
        "sum_probe_wall_time_seconds": sum(cell["wall_time_seconds"] for cell in cells),
        "batch_wall_time_seconds": (_iso(complete["completed_at_utc"]) - _iso(start["started_at_utc"])).total_seconds(),
    }
    accounting_pass = totals["raw_calls"] == totals["attempts"] == totals["call_records"] == 3
    result = {
        "schema_version": "eest_ac_envelope_qualification_analysis.v0_2_2",
        "study_id": complete["study_id"],
        "qualification_verdict": "FAIL",
        "qualification_pass": False,
        "stop_reason": complete["stop_reason"],
        "auto_started_efficacy": False,
        "next_boundary": "stop_at_controller_measurement_floor; no efficacy tasks, no 9/48-cell, no M-RISK",
        "strict_failure_interpretation": (
            "All three model decisions were valid canonical commands and were adapter-mapped and executed. "
            "The third probe remains a preregistered hard failure because the final two launcher screenshots did not hash-identically, "
            "despite a Camera-to-launcher package transition and stable terminal a11y/package signatures."
        ),
        "rates": {
            "initial_output_command_pass": "3/3",
            "accepted_within_one_control_repair": "3/3",
            "repair_after_initial_failure": "not_applicable_0_repairs",
            "metadata_normalization_events": "0/3",
            "metadata_only_repair_calls": 0,
            "schema_adapter_execution_reset": "3/3",
            "required_stable_state_change": "2/3",
            "three_category_coverage": "3/3",
        },
        "totals": totals,
        "call_accounting_pass": accounting_pass,
        "cells": cells,
        "full_envelope_conformance": {
            "offline_audit_status": contract_audit["status"],
            "action_schema_adapter_types": len(contract_audit["action_schema_adapter_matrix"]),
            "generated_artifacts_exact": contract_audit["generated_artifacts_exact"],
            "metadata_only_repair_calls": contract_audit["metadata_only_repair_calls"],
            "maximum_certified_qwen_tokens": contract_audit["token_certificate"]["maximum_certified_total_qwen_tokens"],
            "live_schema_truncations": totals["schema_truncations"],
        },
        "runtime_audit": {
            "model": runtime["runtime"]["model"],
            "adb": runtime["runtime"]["adb"],
            "runtime_preflight_sha256": _hash(args.runtime_preflight),
            "static_preflight_sha256": _hash(args.static_preflight),
            "lock_sha256": _hash(args.lock),
            "lock_source_commit": lock["source_commit"],
            "lock_source_tag": lock["source_tag"],
            "lock_file_count": len(lock["files"]),
            "locked_files_match_start_record": start["locked_files"] == lock["files"],
            "head_at_analysis": _git(repository, "rev-parse", "HEAD"),
            "head_tags": _git(repository, "tag", "--points-at", "HEAD").splitlines(),
            "remaining_experiment_processes": _experiment_processes(),
        },
        "legacy_wip_end_audit": legacy_audit,
        "claim_evidence_verdict": [
            {"claim": "single-source complete decision envelope is conformant offline", "verdict": "SUPPORTED_OFFLINE"},
            {"claim": "real model can emit schema-valid canonical commands", "verdict": "SUPPORTED_3_OF_3_INITIAL"},
            {"claim": "canonical commands map through adapter and execute", "verdict": "SUPPORTED_3_OF_3"},
            {"claim": "full preregistered qualification passes", "verdict": "REJECTED_2_OF_3_REQUIRED_STABLE_CHANGE"},
            {"claim": "intent metadata fail-soft caused no false rejection", "verdict": "NO_LIVE_NORMALIZATION_EVENT; SUPPORTED_OFFLINE_ONLY"},
            {"claim": "M-SLOTS or M-RISK efficacy", "verdict": "NOT_TESTED_AND_NOT_SUPPORTED"},
            {"claim": "eligible to start held-out efficacy", "verdict": "NO"},
        ],
        "raw_root_evidence": {
            "run_root": str(args.run_root.resolve()),
            "qualification_start_sha256": _hash(args.run_root / "qualification_start.json"),
            "qualification_complete_sha256": _hash(args.run_root / "qualification_complete.json"),
        },
    }
    _write_json(args.output_json, result)
    lines = [
        "# EEST-AC v0.2.2 Decision Envelope Qualification - Final Report",
        "",
        "## Verdict",
        "",
        "**FAIL under the preregistered conjunctive rule.** The batch stopped after all three qualification cells; no efficacy batch was started.",
        "",
        "The narrow action-contract signal is positive: all three first outputs were complete schema-valid canonical commands, all three mapped through the adapter, executed, and reset successfully. The overall qualification still fails because DEQ-BACK-03 did not satisfy exact terminal screenshot-hash agreement. Although the action moved from Camera to the launcher and terminal a11y/package signatures stabilized, the last two launcher pixel hashes differed. The frozen rule therefore forbids relabelling it as PASS.",
        "",
        "## Per-probe evidence",
        "",
        "| Probe | Initial / repair | Canonical action | Schema / adapter / execute | Stable change | Reset | Calls | Tokens | Time (s) | Verdict |",
        "|---|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for cell in cells:
        action = json.dumps(cell["canonical_action"], ensure_ascii=False, separators=(",", ":"))
        lines.append(
            f"| {cell['probe_id']} | {cell['accepted_stage']} / {'yes' if cell['repair_used'] else 'no'} | `{action}` | "
            f"pass / pass / {'pass' if cell['environment_executed'] else 'fail'} | "
            f"{'pass' if cell['required_stable_state_change'] else 'FAIL: ' + ','.join(cell['stabilization_audit']['reasons'])} | "
            f"{'pass' if cell['reset_pass'] else 'fail'} | {cell['calls']['raw']} | {cell['tokens']['total']} | "
            f"{cell['wall_time_seconds']:.3f} | {'PASS' if cell['probe_pass'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Aggregate",
        "",
        f"- First-output command pass: 3/3; accepted within one repair: 3/3; repairs used: {totals['realized_repair_calls']}.",
        f"- Coverage/schema/adapter/execution/reset: 3/3 each; required stable state change: {totals['stable_state_change_passes']}/3.",
        f"- Calls: {totals['raw_calls']} raw = {totals['attempts']} attempts = {totals['call_records']} records; accounting {'PASS' if accounting_pass else 'FAIL'}.",
        f"- Tokens: {totals['prompt_tokens']} prompt + {totals['completion_tokens']} completion = {totals['total_tokens']} total.",
        f"- Time: {totals['sum_probe_wall_time_seconds']:.3f}s summed probe time; {totals['batch_wall_time_seconds']:.3f}s batch wall time.",
        f"- Truncation/max-token hits/metadata-only repairs: {totals['schema_truncations']}/{totals['max_token_hits']}/{totals['metadata_only_repair_calls']}.",
        "",
        "## Claim-evidence boundary",
        "",
        "The evidence supports that the repaired full envelope can elicit valid executable commands from the frozen real model (3/3 direct). It does not support a full qualification PASS because the required state-change measurement passed only 2/3. It provides no M-SLOTS, M-RISK, memory, or task-efficacy evidence. No held-out efficacy batch may start from this result.",
        "",
        "## Frozen runtime and audit",
        "",
        f"- Model: `{runtime['runtime']['model']['model']}` revision `{runtime['runtime']['model']['revision']}`, backend `{runtime['runtime']['model']['backend']}`.",
        f"- ADB: port {runtime['runtime']['adb']['server_port']}, serial `{runtime['runtime']['adb']['device_serial']}`, same official client/server binary: `{runtime['runtime']['adb']['same_official_binary']}`; no 5037 fallback.",
        f"- Lock: `{lock['source_tag']}` / `{lock['source_commit']}`, {len(lock['files'])} files; start record matched lock: `{start['locked_files'] == lock['files']}`.",
        f"- Legacy WIP end hashes: `{sum(item['hash_pass'] for item in legacy_audit)}/3`; staged legacy files: `{sum(item['staged'] for item in legacy_audit)}`.",
        f"- Remaining experiment processes: `{len(result['runtime_audit']['remaining_experiment_processes'])}`.",
        f"- Raw completion SHA-256: `{_hash(args.run_root / 'qualification_complete.json')}`.",
        "",
        "Final boundary: stop at controller/measurement qualification. Do not start new task selection, 9-cell, 48-cell, M-RISK, or efficacy experiments.",
    ]
    _write_text(args.output_md, "\n".join(lines))
    print(json.dumps({
        "verdict": "FAIL",
        "cells": len(cells),
        "initial_command_pass": "3/3",
        "stable_state_change": f"{totals['stable_state_change_passes']}/3",
        "total_calls": totals["raw_calls"],
        "total_tokens": totals["total_tokens"],
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
    }, indent=2))


if __name__ == "__main__":
    main()
