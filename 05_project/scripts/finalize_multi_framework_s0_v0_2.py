"""Mechanically qualify the four-arm S0 minimum set and freeze S1 calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from jsonschema import validate as validate_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.multi_framework_benchmark.arm_registry import ARM_REGISTRY  # noqa: E402
from raven_m.multi_framework_benchmark.capability_manifest import (  # noqa: E402
    S0_GATES,
    minimum_launch_set,
    sha256_file,
    validate_capability,
    verify_protected,
)


ARMS = ("CB-PX-B3", "CB-PX-M0", "NS-PX-GO15", "NS-PX-UIV4")
CHECKPOINT_FILES = {
    "CB-PX-B3": "common_qwen.checkpoint_manifest.json",
    "CB-PX-M0": "common_qwen.checkpoint_manifest.json",
    "NS-PX-GO15": "gui_owl.checkpoint_manifest.json",
    "NS-PX-UIV4": "ui_voyager.checkpoint_manifest.json",
}
LOAD_KEYS = {
    "CB-PX-B3": "common_qwen",
    "CB-PX-M0": "common_qwen",
    "NS-PX-GO15": "gui_owl",
    "NS-PX-UIV4": "ui_voyager",
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Required S0 evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def lock_hash(paths: list[Path]) -> str:
    payload = []
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"Runtime-lock component missing: {path}")
        payload.append((str(path.resolve()), sha256_file(path)))
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def tests_pass(path: Path) -> bool:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(item.attrib.get("tests", 0)) for item in suites)
    failures = sum(int(item.attrib.get("failures", 0)) for item in suites)
    errors = sum(int(item.attrib.get("errors", 0)) for item in suites)
    return tests >= 23 and failures == 0 and errors == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-root", type=Path, default=PROJECT_ROOT / "metadata/multi_framework_s0_v0_2")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/final")
    args = parser.parse_args()
    metadata = args.metadata_root.resolve()
    output = args.output_root.resolve()
    if output.exists():
        raise RuntimeError("S0 final output root must not pre-exist")

    protocol = load_json(PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json")
    protected = verify_protected(REPO_ROOT, protocol["protected_paths"])
    fixture_ok = tests_pass(metadata / "protocol_fixture_tests.junit.xml")
    answer = load_json(metadata / "answer_fixtures.json")
    answer_ok = answer.get("passed") is True and len(answer.get("tasks", [])) == 3
    source_audit = load_json(metadata / "source_contract_audit_local.json")
    raven_audit = load_json(metadata / "controller_runtime_raven.json")
    mobile_audit = load_json(metadata / "controller_runtime_mobileagent.json")
    ui_audit = load_json(metadata / "controller_runtime_uivoyager.json")
    runtime_audits = {
        "CB-PX-B3": raven_audit["arms"]["CB-PX-B3"],
        "CB-PX-M0": raven_audit["arms"]["CB-PX-M0"],
        "NS-PX-GO15": mobile_audit,
        "NS-PX-UIV4": ui_audit,
    }

    server_meta = metadata / "server" / "metadata"
    server_load = metadata / "server" / "model_load_checks"
    env_meta = metadata / "controller_environments"
    runtime_parts = {
        "CB-PX-B3": [server_meta / "environments/common_qwen/environment_manifest.sha256", server_meta / "environments/common_qwen/runtime_versions.txt"],
        "CB-PX-M0": [server_meta / "environments/common_qwen/environment_manifest.sha256", server_meta / "environments/common_qwen/runtime_versions.txt"],
        "NS-PX-GO15": [server_meta / "environments/mf_mobileagent_py311/environment.sha256", env_meta / "mobileagent/environment.manifest.sha256"],
        "NS-PX-UIV4": [server_meta / "environments/mf_uivoyager_py311/environment.sha256", env_meta / "uivoyager/environment.manifest.sha256"],
    }
    source_rows = {
        "CB-PX-B3": {"source_pin": raven_audit["source_pin"], "code_license": True},
        "CB-PX-M0": {"source_pin": raven_audit["source_pin"], "code_license": True},
        "NS-PX-GO15": source_audit["sources"]["MobileAgent"],
        "NS-PX-UIV4": source_audit["sources"]["UI-Voyager"],
    }

    schema = load_json(PROJECT_ROOT / "configs/schemas/multi_framework_capability_v0_2.schema.json")
    output.mkdir(parents=True)
    capability_dir = output / "capabilities"
    capability_dir.mkdir()
    capabilities = {}
    capability_summaries = {}
    for arm_id in ARMS:
        spec = ARM_REGISTRY[arm_id]
        checkpoint_path = server_meta / CHECKPOINT_FILES[arm_id]
        checkpoint = load_json(checkpoint_path)
        load_qualification = server_load / f"{LOAD_KEYS[arm_id]}.qualification.txt"
        load_text = load_qualification.read_text(encoding="utf-8")
        runtime_audit = runtime_audits[arm_id]
        source = source_rows[arm_id]
        external_answer_ok = True
        if arm_id in {"NS-PX-GO15", "NS-PX-UIV4"}:
            external_answer_ok = runtime_audit.get("answer_fixture", {}).get("passed") is True
        runtime_hash = lock_hash(runtime_parts[arm_id])
        dependency_lock_hash = sha256_file(runtime_parts[arm_id][-1])
        gates = {
            "source_pin": source.get("source_pin") is True,
            "checkpoint_pin": checkpoint.get("revision") == spec.checkpoint_revision and checkpoint.get("resolved_hub_sha") == spec.checkpoint_revision,
            "shard_integrity": checkpoint.get("file_count") == len(checkpoint.get("files", [])) and checkpoint.get("file_count", 0) > 0 and all(len(row.get("sha256", "")) == 64 for row in checkpoint.get("files", [])),
            "code_license": source.get("code_license") is True,
            "model_license": bool(checkpoint.get("model_card_license")),
            "runtime_lock": all(path.is_file() for path in runtime_parts[arm_id]) and "generation_calls=0" in load_text,
            "runner_support": runtime_audit.get("qualified") is True,
            "task_class_support_19_of_19": runtime_audit.get("task_class_support_19_of_19") is True,
            "answer_support_3_of_3": answer_ok and external_answer_ok,
            "coordinate_fixtures": fixture_ok and (runtime_audit.get("coordinate_fixture", {}).get("passed", True) is True),
            "observation_declaration": tuple(spec.observation_privileges) == ("screenshot",),
            "evaluator_isolation": fixture_ok,
            "budget_enforcement": fixture_ok,
            "logger_schema": fixture_ok,
            "protected_hashes": bool(protected),
        }
        capability = {
            "schema_version": "multi_framework_capability.v0.2",
            "arm_id": arm_id,
            "source_commit": spec.source_commit,
            "checkpoint_revision": spec.checkpoint_revision,
            "external_family": spec.external_family,
            "observation_privileges": list(spec.observation_privileges),
            "gates": gates,
            "qualified": all(gates.values()),
            "evidence": {
                "checkpoint_manifest": str(checkpoint_path),
                "model_load_qualification": str(load_qualification),
                "runtime_audit": runtime_audit,
                "runtime_hash": runtime_hash,
                "dependency_lock_hash": dependency_lock_hash,
                "fixture_junit": str(metadata / "protocol_fixture_tests.junit.xml"),
                "answer_fixture": str(metadata / "answer_fixtures.json"),
            },
        }
        validate_capability(capability)
        validate_schema(capability, schema)
        path = capability_dir / f"{arm_id}.json"
        path.write_text(json.dumps(capability, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        capabilities[arm_id] = capability
        capability_summaries[arm_id] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "runtime_hash": runtime_hash,
            "dependency_lock_hash": dependency_lock_hash,
            "qualified": capability["qualified"],
        }

    qualified = {arm_id for arm_id, value in capabilities.items() if value["qualified"]}
    minimum_ok, reasons = minimum_launch_set(qualified)
    global_ok = fixture_ok and answer_ok and bool(protected) and all(capabilities[arm]["qualified"] for arm in ARMS)
    if not (minimum_ok and global_ok):
        raise RuntimeError(f"S0 minimum set failed: {reasons}; qualified={sorted(qualified)}")

    s1_scripts = [
        PROJECT_ROOT / "scripts/run_raven_s1_smoke_v0_2.py",
        PROJECT_ROOT / "scripts/run_guiowl_s1_smoke_v0_2.py",
        PROJECT_ROOT / "scripts/run_uivoyager_s1_smoke_v0_2.py",
    ]
    s1_manifest = {
        "schema_version": "multi_framework_s1_first_call.v0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "classification": "DEV_ONLY",
        "tasks": ["ContactsAddContact", "ClockStopWatchRunning"],
        "task_seed": 20260805,
        "max_actions_per_task": 8,
        "task_failure_reruns": 0,
        "infrastructure_reruns": 1,
        "arm_order": list(ARMS),
        "endpoints": {
            "CB-PX-B3": "http://127.0.0.1:18000",
            "CB-PX-M0": "http://127.0.0.1:18000",
            "NS-PX-GO15": "http://127.0.0.1:18101/v1",
            "NS-PX-UIV4": "http://127.0.0.1:18102",
        },
        "script_hashes": {str(path.relative_to(REPO_ROOT)): sha256_file(path) for path in s1_scripts},
        "capabilities": capability_summaries,
        "protected_hashes": protected,
        "hard_model_calls_authorized": False,
        "output_root": str(PROJECT_ROOT / "outputs/multi_framework_s1_v0_2"),
    }
    s1_path = output / "s1_first_call_manifest.json"
    s1_path.write_text(json.dumps(s1_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s1_hash = sha256_file(s1_path)
    authorization = {
        "schema_version": "multi_framework_s1_authorization.v0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "s0_all_global_gates_pass": True,
        "minimum_potential_launch_set_pass": True,
        "s1_first_call_manifest_frozen": True,
        "s1_first_call_manifest": str(s1_path),
        "s1_first_call_manifest_sha256": s1_hash,
        "s1_generation_authorized": True,
        "hard_model_calls_authorized": False,
        "qualified_arms": sorted(qualified),
        "capabilities": capability_summaries,
        "minimum_set_reasons": reasons,
    }
    auth_path = output / "s1_authorization.json"
    auth_path.write_text(json.dumps(authorization, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema_version": "multi_framework_s0_qualification.v0.2",
        "status": "PASS",
        "generation_calls": 0,
        "android_actions": 0,
        "qualified_arms": sorted(qualified),
        "minimum_potential_launch_set_pass": minimum_ok,
        "s1_authorization": str(auth_path),
        "s1_authorization_sha256": sha256_file(auth_path),
        "hard_model_calls_authorized": False,
    }
    (output / "s0_qualification.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
