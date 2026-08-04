"""Zero-generation preflight for role-binding timing Stage-1 v0.1."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.contract import (  # noqa: E402
    assert_contract_budget,
    assert_generated_schema_conformance,
    load_contract,
    sha256_path,
)
from raven_m.role_binding_timing.parser import parse_action, parse_grounding  # noqa: E402
from raven_m.role_binding_timing.prompts import (  # noqa: E402
    PromptInstance,
    build_prompt_pair,
)
from raven_m.role_binding_timing.snapshots import (  # noqa: E402
    load_snapshot_manifest,
    qualify_snapshot_manifest,
)
from raven_m.role_binding_timing.token_audit import (  # noqa: E402
    HuggingFaceChatTokenCounter,
    assert_pair_token_match,
)


PROTECTED_WIP = {
    "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}
EXPECTED_MODEL = {
    "model": "Qwen/Qwen3-VL-32B-Instruct",
    "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
    "backend": "qwen3_vl_32b_transformers_bf16_4x4090_v1",
}
NAMESPACE_ROOT = PROJECT_ROOT / "src/raven_m/role_binding_timing"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def verify_protected_wip() -> dict[str, str]:
    status = git("status", "--short").replace("\\", "/")
    actual: dict[str, str] = {}
    for relative, expected in PROTECTED_WIP.items():
        digest = sha256_path(REPOSITORY_ROOT / relative)
        if digest != expected:
            raise RuntimeError(f"Protected legacy WIP hash changed: {relative}")
        if relative not in status:
            raise RuntimeError(f"Protected legacy WIP status unexpectedly clean: {relative}")
        actual[relative] = digest
    return actual


def verify_namespace_isolation() -> dict[str, Any]:
    forbidden_import_fragments = (
        "raven_m.eest_ac",
        "raven_m.controller.episode_controller",
        "raven_m.controller.protocol_v2_guard",
    )
    forbidden_literal_fragments = (
        "h17",
        "r79",
        "p2a",
        "p2b",
        "n2",
        "m-risk",
        "m_risk",
    )
    imports: list[str] = []
    literals: list[str] = []
    paths = sorted(NAMESPACE_ROOT.glob("*.py"))
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                rendered = ast.unparse(node)
                if any(item in rendered for item in forbidden_import_fragments):
                    imports.append(f"{path.name}:{rendered}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                folded = node.value.casefold()
                if any(item in folded for item in forbidden_literal_fragments):
                    literals.append(f"{path.name}:{node.value}")
    if imports or literals:
        raise RuntimeError(
            f"New namespace isolation failed: imports={imports}; literals={literals}"
        )
    return {
        "paths": [
            str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
            for path in paths
        ],
        "forbidden_imports": imports,
        "forbidden_legacy_literals": literals,
    }


def verify_lock(lock_path: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != "role_binding_timing.lock.v0_1":
        raise RuntimeError("Unexpected Phase-B lock version.")
    if lock.get("frozen_before_generation_calls") is not True:
        raise RuntimeError("Lock was not frozen before generation calls.")
    records: list[dict[str, str]] = []
    for item in lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        actual = sha256_path(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"Locked file drifted: {item['path']}")
        records.append({"path": item["path"], "sha256": actual})
    return {
        "lock_sha256": sha256_path(lock_path),
        "locked_files": records,
        "frozen_source_parent_commit": lock["frozen_source_parent_commit"],
    }


def verify_model_health(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    health = response.json()
    actual = {
        "model": health.get("model"),
        "revision": health.get("revision"),
        "backend": health.get("backend"),
    }
    if actual != EXPECTED_MODEL:
        raise RuntimeError(f"Model identity drift: {actual}")
    if health.get("status") != "ok" or health.get("loaded") is not True:
        raise RuntimeError(f"Model service is not ready: {health}")
    return {
        **actual,
        "status": health["status"],
        "loaded": health["loaded"],
        "mode": health.get("mode"),
        "health_method": "GET",
        "generation_endpoint_called": False,
    }


def verify_adb(config: dict[str, Any]) -> dict[str, Any]:
    runtime = config["runtime"]
    if runtime["fallback_to_5037"] is not False:
        raise RuntimeError("ADB fallback must remain disabled.")
    adb = REPOSITORY_ROOT / runtime["adb_binary"]
    if sha256_path(adb) != runtime["adb_binary_sha256"]:
        raise RuntimeError("ADB binary hash drifted.")
    command = [
        str(adb),
        "-P",
        str(runtime["adb_server_port"]),
        "-s",
        runtime["device_serial"],
        "shell",
        "getprop",
        "sys.boot_completed",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode or result.stdout.strip() != "1":
        raise RuntimeError(
            result.stderr.strip() or "Frozen ADB 5038 emulator is not ready."
        )
    return {
        "adb_server_port": runtime["adb_server_port"],
        "device_serial": runtime["device_serial"],
        "adb_binary_sha256": sha256_path(adb),
        "boot_completed": result.stdout.strip(),
        "fallback_to_5037": False,
    }


def verify_token_tooling(
    *,
    contract: dict[str, Any],
    config: dict[str, Any],
    cache_dir: Path,
) -> dict[str, Any]:
    tokenizer_config = config["tokenizer"]
    counter = HuggingFaceChatTokenCounter(
        model=tokenizer_config["model"],
        revision=tokenizer_config["revision"],
        cache_dir=cache_dir,
        local_files_only=tokenizer_config["local_files_only"],
    )
    resolved_commit = counter.tokenizer.init_kwargs.get("_commit_hash")
    if resolved_commit not in (None, tokenizer_config["revision"]):
        raise RuntimeError(
            f"Tokenizer revision drift: expected {tokenizer_config['revision']}, got {resolved_commit}"
        )
    candidate_targets = tuple(
        {"target_id": target, "entity_id": f"E{index + 1}", "widget_role": "input"}
        for index, target in enumerate("ABCDEFGH")
    )
    instance = PromptInstance(
        base_family_id="BF-000",
        role_ambiguity="high",
        task_without_value="Transfer the requested source field to the intended destination field.",
        source_entity_id="E1",
        destination_entity_id="E2",
        field="reference code",
        value="QX-7319-K",
        candidate_targets=candidate_targets,
    )
    grounding = {
        "phase": "grounding",
        "destination_target_id": "B",
        "source_entity_id": "E1",
        "destination_entity_id": "E2",
        "confidence": 0.5,
    }
    early = build_prompt_pair(
        instance=instance,
        fact_timing="early",
        grounding=grounding,
        counter=counter,
        contract=contract,
    )
    late = build_prompt_pair(
        instance=instance,
        fact_timing="late",
        grounding=grounding,
        counter=counter,
        contract=contract,
    )
    counts = assert_pair_token_match(
        early_call_1=list(early.call_1_messages),
        early_call_2=list(early.call_2_messages),
        late_call_1=list(late.call_1_messages),
        late_call_2=list(late.call_2_messages),
        counter=counter,
        tolerance=tokenizer_config["early_late_text_token_tolerance"],
    )
    if min(counts["early_call_1"], counts["late_call_1"]) < 64:
        raise RuntimeError(f"Degenerate chat-template certificate: {counts}")
    target_alias_counts = {value: counter.count_text(value) for value in "ABCDEFGH"}
    entity_alias_counts = {value: counter.count_text(value) for value in [f"E{i}" for i in range(1, 9)]}
    if len(set(target_alias_counts.values())) != 1:
        raise RuntimeError(f"Target aliases are not token-isometric: {target_alias_counts}")
    if len(set(entity_alias_counts.values())) != 1:
        raise RuntimeError(f"Entity aliases are not token-isometric: {entity_alias_counts}")
    if counter.count_text(early.fact_block) != counter.count_text(early.neutral_block):
        raise RuntimeError("Fact/neutral blocks are not exactly token matched.")
    return {
        "tokenizer_class": type(counter.tokenizer).__name__,
        "model": tokenizer_config["model"],
        "revision": tokenizer_config["revision"],
        "resolved_commit": resolved_commit,
        "local_files_only": tokenizer_config["local_files_only"],
        "synthetic_prompt_pair_counts": counts,
        "fact_block_tokens": counter.count_text(early.fact_block),
        "neutral_block_tokens": counter.count_text(early.neutral_block),
        "target_alias_token_counts": target_alias_counts,
        "entity_alias_token_counts": entity_alias_counts,
        "certificate_scope": "tooling_and_aliases_only_no_held_out_instances",
    }


def verify_parser_smoke() -> dict[str, Any]:
    allowed = {"A", "B"}
    grounding = {
        "phase": "grounding",
        "destination_target_id": "B",
        "source_entity_id": "E1",
        "destination_entity_id": "E2",
        "confidence": 0.5,
    }
    action = {
        "phase": "action",
        "grounded_destination_target_id": "B",
        "recalled_value": "QX-7319-K",
        "action": {"type": "type_text", "target_id": "B", "text": "QX-7319-K"},
        "confidence": 0.5,
    }
    parse_grounding(json.dumps(grounding, separators=(",", ":")), allowed_target_ids=allowed)
    parse_action(json.dumps(action, separators=(",", ":")), allowed_target_ids=allowed)
    return {"grounding_schema": "pass", "action_schema": "pass"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs/role_binding_timing/stage1_v0_1.json",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=PROJECT_ROOT / "configs/role_binding_timing/stage1_v0_1.lock.json",
    )
    parser.add_argument(
        "--tokenizer-cache",
        type=Path,
        default=Path("D:/ZJU/Summer_Camp/_model_tokenizer_cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "reports/role_binding_timing/PHASE_B_ZERO_GENERATION_PREFLIGHT_2026-08-04.json",
    )
    args = parser.parse_args()

    started = utc_now()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    contract = load_contract(REPOSITORY_ROOT / config["contract"])
    if config.get("generation_calls_authorized") != 0:
        raise RuntimeError("Phase B authorizes zero generation calls only.")

    assert_contract_budget(contract)
    protected = verify_protected_wip()
    schemas = assert_generated_schema_conformance(contract)
    isolation = verify_namespace_isolation()
    lock = verify_lock(args.lock)
    parser_smoke = verify_parser_smoke()
    token_audit = verify_token_tooling(
        contract=contract,
        config=config,
        cache_dir=args.tokenizer_cache,
    )
    model_health = verify_model_health(config["runtime"]["model_health_url"])
    adb = verify_adb(config)
    snapshot_path = REPOSITORY_ROOT / config["snapshot_manifest"]
    snapshot_manifest = load_snapshot_manifest(snapshot_path)
    snapshot = qualify_snapshot_manifest(
        snapshot_manifest,
        repository_root=REPOSITORY_ROOT,
    )
    gates = contract["pilot_gates"]
    snapshot_gate = (
        snapshot.rate >= gates["snapshot_oracle_qualification_min"]
        and snapshot.retained_base_families >= gates["base_families"]
    )
    generation_eligible = bool(
        snapshot_gate
        and contract["generation_eligible"]
        and config["generation_eligible"]
    )
    report = {
        "schema_version": "role_binding_timing.preflight.v0_1",
        "study_id": contract["study_id"],
        "started_at": started,
        "finished_at": utc_now(),
        "head": git("rev-parse", "HEAD"),
        "offline_tooling_status": "pass",
        "generation_calls_by_preflight": 0,
        "generation_endpoint_called": False,
        "generation_eligible": generation_eligible,
        "gate_verdict": "NOT_ELIGIBLE_FOR_GENERATION" if not generation_eligible else "ELIGIBLE_FOR_SEPARATE_FROZEN_PILOT",
        "blocking_gates": ([] if snapshot_gate else ["fresh_snapshot_oracle_qualification"]),
        "novelty_status": "UNRESOLVED",
        "protected_legacy_wip": protected,
        "schema_conformance": schemas,
        "namespace_isolation": isolation,
        "lock": lock,
        "parser_smoke": parser_smoke,
        "token_audit": token_audit,
        "model_health": model_health,
        "adb": adb,
        "snapshot_oracle": {
            "manifest_sha256": sha256_path(snapshot_path),
            "total_variants": snapshot.total_variants,
            "qualified_variants": snapshot.qualified_variants,
            "qualification_rate": snapshot.rate,
            "retained_base_families": snapshot.retained_base_families,
            "required_base_families": gates["base_families"],
            "required_rate": gates["snapshot_oracle_qualification_min"],
            "issues": list(snapshot.issues),
        },
        "contamination_boundary": {
            "phase_a_dev_screenshots_used_as_held_out": False,
            "old_runs_used_as_held_out": False,
            "fresh_held_out_base_families": snapshot.retained_base_families,
        },
        "claim_evidence": {
            "prompt_schema_parser_tooling": "qualified_offline",
            "exact_token_matching_on_held_out_instances": "untested",
            "snapshot_oracle_gate": "failed_empty_manifest",
            "timing_effect": "untested",
            "memory_efficacy": "untested_out_of_scope",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
