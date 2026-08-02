"""Preflight or run the one authorized non-scored r76 H17/M0 smoke."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OVERLAY = (
    PROJECT_ROOT / "configs/experiments/v2_2_h17_candidate_r76.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_h17_candidate_r76.generated.json"
)
SOURCE_COMMIT = "0231b8f0c7f9e806bf763a60d975dcc76b128b67"
SOURCE_TAG = "protocol-v2-2-r76-local-candidate"
PARENT_GATE_E_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"
R75_STOP_COMMIT = "752e8a7a119e6190aac102c2b5345fc14423f71e"
R75_STOP_TAG = "protocol-v2-2-r75-h17-stopped"
AUTHORIZED_SEQUENCE = 2


def _git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        text=True,
        timeout=30,
    ).strip()


def _verify_json_prerequisite(
    record: dict[str, str],
) -> dict[str, object]:
    path = REPOSITORY_ROOT / record["path"]
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != record["sha256"]:
        raise RuntimeError(f"Prerequisite drifted: {record['path']}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_candidate_manifest() -> Path:
    """Build the r76 candidate from frozen r56 experimental controls."""
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    if _git_output("rev-list", "-n", "1", SOURCE_TAG) != SOURCE_COMMIT:
        raise RuntimeError("r76 source tag drifted.")
    if _git_output("rev-list", "-n", "1", R75_STOP_TAG) != R75_STOP_COMMIT:
        raise RuntimeError("r75 stop tag drifted.")
    stopped = _verify_json_prerequisite(
        overlay["prerequisite_r75_stop_report"]
    )
    if (
        stopped.get("decision")
        != "r75_blocked_imprecise_target_row_repair_before_execution_"
        "but_generic_row_tap_contract_could_not_route_the_single_repair_"
        "to_an_exact_center"
        or stopped.get("immutability", {}).get("suite_may_be_resumed")
        is not False
    ):
        raise RuntimeError("r75 stop prerequisite is invalid.")
    local = _verify_json_prerequisite(
        overlay["prerequisite_r76_local_validation"]
    )
    if (
        local.get("decision")
        != "local_candidate_passed_exact_package_preflight_pending"
        or local.get("source_commit") != SOURCE_COMMIT
        or local.get("formal_gate_f_authorized") is not False
        or local.get("live_development_smoke_authorized") is not False
    ):
        raise RuntimeError("r76 local-validation prerequisite is invalid.")

    base_path = REPOSITORY_ROOT / overlay["base_manifest"]
    manifest = json.loads(base_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_h17_candidate_r76.v1",
            "manifest_id": overlay["manifest_id"],
            "source_tag": overlay["source_tag"],
            "source_commit": overlay["source_commit"],
            "suite_id": overlay["suite_id"],
            "output_root": overlay["output_root"],
            "candidate_scope": {
                "formal_scoring": False,
                "authorized_development_sequence": AUTHORIZED_SEQUENCE,
                "authorized_task_id": "H17",
                "authorized_variant": "M0",
            },
            "prerequisite_r75_stop_report": overlay[
                "prerequisite_r75_stop_report"
            ],
            "prerequisite_r76_local_validation": overlay[
                "prerequisite_r76_local_validation"
            ],
        }
    )
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    overrides = overlay["updated_freeze_hashes"]
    if not overrides.keys() <= records_by_path.keys():
        raise RuntimeError("r76 freeze override is absent from r56.")
    for path, digest in overrides.items():
        records_by_path[path]["sha256"] = digest
    GENERATED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return GENERATED_MANIFEST


def validate_invocation(argv: list[str]) -> None:
    """Fail closed unless this is a preflight or exact H17 sequence 2."""
    if "--batch" in argv or any(
        item.startswith("--batch=") for item in argv
    ):
        raise RuntimeError("r76 candidate wrapper forbids formal batches.")
    smoke_values: list[str] = []
    for index, item in enumerate(argv):
        if item == "--development-smoke-sequence":
            if index + 1 >= len(argv):
                raise RuntimeError("Missing development-smoke sequence.")
            smoke_values.append(argv[index + 1])
        elif item.startswith("--development-smoke-sequence="):
            smoke_values.append(item.split("=", 1)[1])
    if "--preflight-only" in argv:
        if smoke_values:
            raise RuntimeError("r76 preflight cannot also launch a smoke.")
        return
    if smoke_values != [str(AUTHORIZED_SEQUENCE)]:
        raise RuntimeError(
            "r76 candidate permits only H17/M0 development sequence 2."
        )


if __name__ == "__main__":
    validate_invocation(sys.argv[1:])
    raise SystemExit(
        main(
            default_manifest=build_candidate_manifest(),
            expected_source_tag=SOURCE_TAG,
            expected_source_commit=SOURCE_COMMIT,
            expected_prerequisite_commit=PARENT_GATE_E_COMMIT,
            diagnostic_pause=None,
            allow_development_smoke=True,
        )
    )
