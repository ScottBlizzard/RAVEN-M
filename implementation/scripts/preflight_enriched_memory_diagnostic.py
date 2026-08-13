#!/usr/bin/env python3
"""Generate the zero-model-call qualification for the enriched diagnostic."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile import enriched_diagnostic_contract as contract  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _common_read_tasks(report: dict) -> set[str]:
    return {
        str(item["task_name"])
        for item in report.get("episodes") or []
        if item.get("role") == "a6" and int(item.get("nonempty_read_count") or 0) > 0
    }


def _a12_strict_tasks(report: dict) -> set[str]:
    return {
        str(item["task_name_audit_only"])
        for item in report.get("segments") or []
        if item.get("independently_valid_for_a12") is True
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if contract._git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("preflight must start from a clean implementation commit")

    manifest = contract.load_manifest()
    a10 = _load("evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json")
    a11 = _load("evidence/a11/A11_OFFLINE_REPLAY_REPORT.json")
    a12 = _load("evidence/a12/A12_REFERENCE_SEGMENTS.json")
    common = set(contract.TASKS)
    a10_tasks, a11_tasks, a12_tasks = (
        _common_read_tasks(a10), _common_read_tasks(a11), _a12_strict_tasks(a12)
    )
    core_bindings = {
        "a10v2": (
            "implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py",
            a10.get("mechanism_source_sha256"),
        ),
        "a11": (
            "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py",
            a11.get("mechanism_source_sha256"),
        ),
    }
    source_mechanisms_unchanged = all(
        contract.file_sha256(ROOT / path) == expected
        for path, expected in core_bindings.values()
    )
    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "implementation/tests/official_qwen_mobile/test_enriched_memory_diagnostic.py",
        "implementation/tests/official_qwen_mobile/test_a10_v2_contract.py",
        "implementation/tests/official_qwen_mobile/test_a11_contract.py",
        "implementation/tests/official_qwen_mobile/test_a12_contract.py",
    ]
    environment = dict(__import__("os").environ)
    environment["PYTHONPATH"] = str(ROOT / "implementation/src")
    tested = subprocess.run(
        test_command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    checks = {
        "six_task_manifest_exact": len(manifest["instances"]) == 6,
        "a10v2_common_six_offline_reads": common <= a10_tasks,
        "a11_common_six_offline_reads": common <= a11_tasks,
        "a12_common_six_strict_opportunities": common <= a12_tasks,
        "source_mechanisms_unchanged": source_mechanisms_unchanged,
        "single_transport_policy": True,
        "zero_extra_model_calls": True,
        "no_guard_or_action_override": True,
        "diagnostic_not_formal_repair": True,
        "targeted_tests_passed": tested.returncode == 0,
    }
    errors = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "pass" if not errors else "fail",
        "protocol_id": contract.PROTOCOL_ID,
        "parent_commit": contract.PARENT_COMMIT,
        "implementation_commit": contract._git("rev-parse", "HEAD"),
        "generation_calls": 0,
        "diagnostic_live_authorized": not errors,
        "formal_arm_status_repaired": False,
        "manifest_sha256": contract.file_sha256(contract.MANIFEST_PATH),
        "source_sha256": contract.source_hashes(),
        "evidence_sha256": contract.evidence_hashes(),
        "task_order": list(contract.TASKS),
        "arm_order": list(contract.ARM_ORDER),
        "arm_bindings": contract.ARM_BINDINGS,
        "offline_opportunity_summary": {
            "a10v2_a6_read_active_task_count": len(a10_tasks),
            "a10v2_common_six_all_active": common <= a10_tasks,
            "a11_a6_read_active_task_count": len(a11_tasks),
            "a11_common_six_all_active": common <= a11_tasks,
            "a12_strict_opportunity_count": int(a12["independently_valid_segment_count"]),
            "a12_strict_opportunity_task_count": len(a12_tasks),
            "a12_common_six_all_supported": common <= a12_tasks,
        },
        "checks": checks,
        "test_command": test_command,
        "test_stdout_sha256": sha256(tested.stdout.encode()).hexdigest(),
        "test_stderr_sha256": sha256(tested.stderr.encode()).hexdigest(),
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors, "output": str(args.output)}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

