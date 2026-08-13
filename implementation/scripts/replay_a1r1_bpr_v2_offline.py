#!/usr/bin/env python3
"""Zero-generation reconstruction of the frozen A1 legacy pending envelope."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r1_bpr_v2 import (  # noqa: E402
    A1R1_BPR_V2_SUFFIX,
    MECHANISM_ID,
)
from raven_m.official_qwen_mobile.a1r1_bpr_v2_contract import (  # noqa: E402
    DESIGN_SHA256,
    OFFLINE_REPLAY_SCHEMA,
    content_sha256,
    file_sha256,
)


LEGACY_RE = re.compile(r"^MEMORY\[observed=.*?; verified=.*?; pending=(.*?)\] \| ", re.S)
EXPECTED_SUITE = "official_qwen_20260810T122419_26573d7c"
EXPECTED_AGGREGATE_SHA256 = "7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51"


def _canonical_digest(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def reconstruct(source_suite: Path) -> dict:
    aggregate_path = source_suite / "aggregate.json"
    episode_paths = sorted((source_suite / "episodes").glob("*/episode.json"))
    errors: list[str] = []
    if source_suite.name != EXPECTED_SUITE:
        errors.append("source_suite_id_drift")
    if not aggregate_path.is_file() or file_sha256(aggregate_path) != EXPECTED_AGGREGATE_SHA256:
        errors.append("source_aggregate_hash_drift")
    if len(episode_paths) != 19:
        errors.append("episode_count_not_19")

    records: list[dict] = []
    episode_hashes: dict[str, str] = {}
    terminal_prefix_count = 0
    for path in episode_paths:
        episode = json.loads(path.read_text(encoding="utf-8"))
        episode_hashes[str(episode.get("episode_id"))] = file_sha256(path)
        for step in episode.get("steps") or []:
            decision = step.get("decision") or {}
            summary = str(decision.get("action_summary") or "")
            match = LEGACY_RE.match(summary)
            if not match:
                continue
            if not bool(step.get("executed")):
                terminal_prefix_count += 1
                continue
            pending = " ".join(match.group(1).split()).strip()
            if pending == "none":
                continue
            chars = len(pending)
            bytes_ = len(pending.encode("utf-8"))
            records.append(
                {
                    "ordinal": len(records),
                    "episode_id": episode.get("episode_id"),
                    "task_name": episode.get("task_name"),
                    "source_step": int(step.get("step")),
                    "pending": pending,
                    "chars": chars,
                    "utf8_bytes": bytes_,
                    "fits": chars <= 100 and bytes_ <= 128,
                    "source_response_sha256": ((step.get("model_call") or {}).get("response_sha256")),
                }
            )

    fit_count = sum(int(item["fits"]) for item in records)
    if len(records) != 514:
        errors.append("legacy_non_none_record_count_not_514")
    if fit_count != 511:
        errors.append("legacy_joint_fit_count_not_511")
    if fit_count < 489:
        errors.append("R3_threshold_fail")
    suffix_bytes = len(A1R1_BPR_V2_SUFFIX.encode("utf-8"))
    suffix_sha = sha256(A1R1_BPR_V2_SUFFIX.encode("utf-8")).hexdigest()
    if suffix_bytes != 686 or suffix_sha != "6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b":
        errors.append("suffix_identity_drift")

    status = "PASS" if not errors else "FAIL"
    payload = {
        "schema": OFFLINE_REPLAY_SCHEMA,
        "status": status,
        "errors": errors,
        "generation_calls": 0,
        "live_generation_authorized": status == "PASS",
        "mechanism_id": MECHANISM_ID,
        "design_sha256": DESIGN_SHA256,
        "source": {
            "suite_id": source_suite.name,
            "aggregate_sha256": file_sha256(aggregate_path) if aggregate_path.is_file() else None,
            "episode_json_count": len(episode_paths),
            "episode_json_hashes_sha256": _canonical_digest(episode_hashes),
            "terminal_or_unexecuted_valid_prefix_count": terminal_prefix_count,
        },
        "R3": {
            "denominator_definition": "executed valid legacy MEMORY prefixes with pending != exact lowercase none; duplicates retained",
            "record_count": len(records),
            "joint_fit_count": fit_count,
            "required_minimum": 489,
            "pass": fit_count >= 489 and len(records) == 514,
            "ordered_records_sha256": _canonical_digest(records),
            "nonfit_records": [item for item in records if not item["fits"]],
        },
        "R5_status": "PROSPECTIVE_UNKNOWN_PRELIVE",
        "suffix": {"utf8_bytes": suffix_bytes, "sha256": suffix_sha},
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-suite",
        type=Path,
        default=REPOSITORY_ROOT / "runs/a1_working_memory" / EXPECTED_SUITE,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json",
    )
    args = parser.parse_args()
    report = reconstruct(args.source_suite.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "status": report["status"], "R3": report["R3"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
