"""Repair a post-hoc pairing-hash false positive in frozen breadth results.

AndroidWorld's ``SaveCopyOfReceiptTaskEval`` stores a PIL ``ImagingCore``
object in its task parameters.  The generic JSON-safe serializer retained the
object's process-local memory address, so semantically identical task
instances received different parameter hashes.  This script normalizes only
such runtime-object repr strings, updates derived hashes in scored results,
and rebuilds the suite summary.  Raw episodes and scientific outcomes are
never modified.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_frozen_hard_suite as frozen  # noqa: E402


AMENDMENT_ID = "protocol-v1-hotfix-005"
AMENDMENT_MANIFEST = PROJECT_ROOT / "metadata/protocol_amendment_005.json"
EXPECTED_SUITE_ID = "hard_v1_breadth"
EXPECTED_PAIR_ID = "H15-s20260720"
RUNTIME_OBJECT_RE = re.compile(
    r"^<(?P<label>[^<>]+ object) at 0x[0-9A-Fa-f]+>$"
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_amendment_manifest(*, require_tag: bool) -> dict[str, Any]:
    if not AMENDMENT_MANIFEST.is_file():
        raise RuntimeError("Protocol amendment 005 manifest is absent.")
    manifest = json.loads(AMENDMENT_MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("amendment_id") != AMENDMENT_ID
        or manifest.get("status") != "active"
        or manifest.get("scope") != "posthoc_pairing_hash_metadata"
        or manifest.get("semantic_changes") is not False
    ):
        raise RuntimeError("Protocol amendment 005 identity is invalid.")
    for record in manifest["files"]:
        path = REPOSITORY_ROOT / record["path"]
        if (
            not path.is_file()
            or file_sha256(path) != record["sha256"]
            or path.stat().st_size != record["bytes"]
        ):
            raise RuntimeError(
                f"Protocol amendment 005 hash mismatch: {record['path']}"
            )
    if require_tag:
        tag_commit = frozen.git(
            "rev-parse", f"{manifest['git_tag']}^{{commit}}"
        )
        frozen.git("merge-base", "--is-ancestor", tag_commit, "HEAD")
        manifest = {**manifest, "git_tag_commit": tag_commit}
    return manifest


def normalize_runtime_object_reprs(value: Any) -> Any:
    """Return a deep JSON-value copy with process-local addresses removed."""
    if isinstance(value, dict):
        return {
            str(key): normalize_runtime_object_reprs(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_runtime_object_reprs(item) for item in value]
    if isinstance(value, str):
        match = RUNTIME_OBJECT_RE.fullmatch(value)
        if match:
            return f"<{match.group('label')}>"
    return value


def canonical_params_sha256(params: Any) -> str:
    return frozen.digest_json(normalize_runtime_object_reprs(params))


def amendment_result_identity() -> dict[str, Any]:
    manifest = load_amendment_manifest(require_tag=False)
    return {
        "amendment_id": manifest["amendment_id"],
        "scope": manifest["scope"],
        "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
        "repair_script_sha256": file_sha256(Path(__file__).resolve()),
    }


def repair_result(result: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Repair derived metadata for the one affected pair, idempotently."""
    if result.get("pair_id") != EXPECTED_PAIR_ID:
        return result, False
    repaired = dict(result)
    canonical = canonical_params_sha256(repaired["task_params"])
    current = repaired["params_sha256"]
    if current == canonical:
        return repaired, False
    repaired["params_sha256_before_hotfix_005"] = current
    repaired["params_sha256"] = canonical
    repaired["params_hash_scheme"] = "json_runtime_object_address_normalized.v1"
    amendments = list(repaired.get("protocol_amendments", []))
    amendments.append(amendment_result_identity())
    repaired["protocol_amendments"] = amendments
    return repaired, True


def validate_trigger(summary: dict[str, Any]) -> list[dict[str, Any]]:
    if summary.get("suite_id") != EXPECTED_SUITE_ID:
        raise RuntimeError("Hotfix 005 is authorized only for breadth.")
    if not summary.get("finished"):
        raise RuntimeError("Breadth must be finished before post-hoc repair.")
    if summary.get("audit_error_count") != 0:
        raise RuntimeError("Unrelated audit errors are present.")
    if summary.get("pairing_error_ids") != [EXPECTED_PAIR_ID]:
        raise RuntimeError("The authorized pairing false positive is absent.")
    affected = [
        item
        for item in summary["results"]
        if item.get("pair_id") == EXPECTED_PAIR_ID
    ]
    if len(affected) != 5:
        raise RuntimeError("The affected pair does not contain five variants.")
    if {item["variant"] for item in affected} != {
        "B0",
        "B1",
        "B2",
        "B3",
        "M0",
    }:
        raise RuntimeError("The affected pair has unexpected variants.")
    if len({item["goal_sha256"] for item in affected}) != 1:
        raise RuntimeError("The affected task goals are not identical.")
    canonical_hashes = {
        canonical_params_sha256(item["task_params"]) for item in affected
    }
    if len(canonical_hashes) != 1:
        raise RuntimeError("Address normalization does not restore pairing.")
    return affected


def apply_hotfix(suite_dir: Path) -> dict[str, Any]:
    summary_path = suite_dir / "suite_summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"Suite summary is absent: {summary_path}")
    prior = json.loads(summary_path.read_text(encoding="utf-8"))
    affected = validate_trigger(prior)
    expected_episode_ids = {item["episode_id"] for item in affected}

    repaired_results = []
    repaired_episode_ids = []
    for scored_path in sorted(
        (suite_dir / "episodes").glob("*/scored_result.json")
    ):
        result = json.loads(scored_path.read_text(encoding="utf-8"))
        repaired, changed = repair_result(result)
        if changed:
            frozen.write_json(scored_path, repaired)
            repaired_episode_ids.append(repaired["episode_id"])
        repaired_results.append(repaired)
    if set(repaired_episode_ids) != expected_episode_ids:
        raise RuntimeError("Hotfix 005 did not repair exactly the affected pair.")
    repaired_results.sort(key=lambda item: int(item["sequence"]))

    final = frozen.aggregate(
        suite_id=prior["suite_id"],
        phase=prior["phase"],
        schedule_hash=prior["schedule_records_sha256"],
        freeze=prior["freeze"],
        health={
            "backend": prior["model_backend"],
            "revision": prior["model_revision"],
        },
        results=repaired_results,
        expected_count=prior["expected_episode_count"],
        finished=True,
    )
    if (
        final["completed_episode_count"] != prior["expected_episode_count"]
        or final["pairing_error_count"] != 0
        or final["audit_error_count"] != 0
    ):
        raise RuntimeError("Rebuilt breadth audit did not pass.")
    final["posthoc_metadata_amendments"] = [amendment_result_identity()]
    frozen.write_json(summary_path, final)
    frozen.write_json(suite_dir / "suite_progress.json", final)
    return {
        "suite_id": final["suite_id"],
        "completed_episode_count": final["completed_episode_count"],
        "pairing_error_count": final["pairing_error_count"],
        "audit_error_count": final["audit_error_count"],
        "repaired_episode_ids": repaired_episode_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    args = parser.parse_args()
    load_amendment_manifest(require_tag=True)
    result = apply_hotfix(args.suite_dir.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
