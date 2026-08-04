"""Read-only audit of frozen M6 runner-owned ADB client invocations for INFRA-M7."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
M6_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_display_observability"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority_audit"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.json"

SOURCES = [
    "05_project/scripts/run_role_binding_timing_infra_m6.py",
    "05_project/scripts/run_role_binding_timing_infra_m5.py",
    "05_project/scripts/run_role_binding_timing_infra_m4.py",
    "05_project/scripts/run_role_binding_timing_infra_m2.py",
    "05_project/scripts/qualify_role_binding_timing_b2_10_a11y_lifecycle.py",
    "05_project/src/raven_m/role_binding_timing/infra_m5_process_identity.py",
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def walk_commands(value: Any, source: str, found: dict[tuple[str, ...], set[str]]) -> None:
    if isinstance(value, dict):
        command = value.get("command")
        if isinstance(command, list) and command and str(command[0]).casefold().endswith("adb.exe"):
            found.setdefault(tuple(str(item) for item in command), set()).add(source)
        for item in value.values():
            walk_commands(item, source, found)
    elif isinstance(value, list):
        for item in value:
            walk_commands(item, source, found)


def command_class(command: tuple[str, ...]) -> str:
    lowered = [item.casefold() for item in command]
    if "start-server" in lowered:
        return "SERVER_LIFECYCLE_START_LAUNCH_ONLY"
    if "kill-server" in lowered:
        return "SERVER_LIFECYCLE_STOP_CLEANUP_ONLY"
    if "nodaemon" in lowered or "fork-server" in lowered or "server" in lowered:
        return "FORBIDDEN_SERVER_MODE"
    return "GENERIC_RUNNER_OWNED_CLIENT"


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M7_AUDIT_OUTPUT_EXISTS")
    OUTPUT_ROOT.mkdir(parents=True)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    completion = json.loads((M6_ROOT / "qualification_completion.json").read_text(encoding="utf-8"))
    found: dict[tuple[str, ...], set[str]] = {}
    for path in sorted(M6_ROOT.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        walk_commands(value, path.relative_to(M6_ROOT).as_posix(), found)
    commands = []
    for command, sources in sorted(found.items()):
        port_indexes = [index for index, token in enumerate(command) if token.casefold() == "-p"]
        explicit_5038 = len(port_indexes) == 1 and port_indexes[0] + 1 < len(command) and command[port_indexes[0] + 1] == "5038"
        commands.append({
            "argv": list(command),
            "classification": command_class(command),
            "explicit_single_5038": explicit_5038,
            "locked_binary_path": str(Path(command[0]).resolve()) == str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()),
            "artifact_occurrences": len(sources),
            "artifact_sources": sorted(sources),
        })
    source_records = []
    needles = ("adb_prefix", "RawAdb", "start-server", "kill-server", "run_raw(")
    for relative in SOURCES:
        path = REPOSITORY_ROOT / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        source_records.append({
            "path": relative,
            "sha256": digest(path),
            "relevant_lines": [
                {"line": index, "text": line.strip()}
                for index, line in enumerate(lines, 1)
                if any(needle in line for needle in needles)
            ],
        })
    offending = completion["first_broken_edge"]
    result = {
        "schema_version": "role_binding_timing.infra_m7.adb_authority_audit.v1",
        "mode": "read_only_frozen_m6_evidence",
        "generation_calls": 0,
        "device_mutations": 0,
        "m6_completion_commit": "f17f18ec595588de98e244920845d97f97c20407",
        "m6_verdict_immutable": completion["status"],
        "m6_first_broken_edge_immutable": offending,
        "source_identity": source_records,
        "observed_m6_adb_argv": commands,
        "observed_summary": {
            "unique_argv": len(commands),
            "generic_clients": sum(item["classification"] == "GENERIC_RUNNER_OWNED_CLIENT" for item in commands),
            "server_lifecycle": sum(item["classification"].startswith("SERVER_LIFECYCLE") for item in commands),
            "forbidden_server_mode": sum(item["classification"] == "FORBIDDEN_SERVER_MODE" for item in commands),
            "all_explicit_single_5038": all(item["explicit_single_5038"] for item in commands),
            "all_locked_binary_path": all(item["locked_binary_path"] for item in commands),
        },
        "root_cause": {
            "direct_evidence": "M6 rejected a locked, direct-runner, explicit-5038 `devices -l` client because M5 enumerated allowed argv classes.",
            "policy_defect": "OWNERSHIP_POLICY_COUPLED_TO_HARMLESS_SUBCOMMAND_ENUMERATION",
            "non_claims": [
                "M6 display quorum would have passed",
                "boot would have qualified",
                "AndroidEnv a11y is stable",
                "any role-binding or memory hypothesis",
            ],
        },
        "m7_required_predicate": {
            "ordinary_client": [
                "exact locked adb.exe path and SHA-256",
                "argv begins with the locked executable and contains exactly one `-P 5038`",
                "direct frozen-runner parent identity; no cmd.exe or PowerShell wrapper",
                "created after runner and no older than 45 seconds at first authorization",
                "no listening socket on any local TCP port at every observed sample",
                "bounded active lifetime of at most 45 seconds",
                "not a server lifecycle/server-mode argv",
            ],
            "server_lifecycle": {
                "start-server": "launch only",
                "kill-server": "cleanup only",
                "nodaemon/fork-server/server mode": "forbidden as runner client",
            },
            "completed_client_ledger": "Once admitted while current or independently bounded by a listener-bearing history sample plus a later absence snapshot, a completed identity remains auditable without aging into a false failure.",
            "permanent_vetoes": ["missing or other port", "path/hash mismatch", "parent/ancestry mismatch", "PID reuse", "listener ownership", "active age above 45 seconds", "wrapper ambiguity", "server-mode argv"],
        },
        "observation_gap": {
            "m5_snapshot_limitation": "Only selected ports were mapped to PIDs and continuous history did not retain listener evidence per transient process.",
            "m7_requirement": "Every structural snapshot/history sample must attach the full local TCP listener-port set for each process identity and persist it in the triggering snapshot.",
        },
        "continue_decision": "ELIGIBLE_FOR_M7_OFFLINE_IMPLEMENTATION_ONLY",
    }
    audit_path = OUTPUT_ROOT / "adb_authority_audit.json"
    audit_path.write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    manifest = {"schema_version": "role_binding_timing.infra_m7.audit_manifest.v1", "artifacts": [{"path": audit_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": audit_path.stat().st_size, "sha256": digest(audit_path)}]}
    (OUTPUT_ROOT / "artifact_manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"summary": result["observed_summary"], "defect": result["root_cause"]["policy_defect"], "decision": result["continue_decision"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
