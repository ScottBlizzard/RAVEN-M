#!/usr/bin/env python3
"""Zero-generation replay of frozen A1-R2 traces through A1-R3-v3."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r3v3_one_shot_cnr import (  # noqa: E402
    MECHANISM_ID,
    OneShotControllerNonprogressReceiptMemory,
)


A1R2_SUITE_ID = "official_qwen_20260814T145307_50081981"
DEFAULT_SUITE = ROOT / "runs/a1r2_cvp" / A1R2_SUITE_ID
R2_RESULT_PATH = ROOT / "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"
SUCCESS_TASKS = {
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
}
DEFAULT_TOKENIZER = Path(
    r"D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\cache\qwen3_vl_32b_tokenizer"
    r"\models--Qwen--Qwen3-VL-32B-Instruct\snapshots"
    r"\0cfaf48183f594c314753d30a4c4974bc75f3ccb"
)
EXPECTED_EXPOSURES = {
    "BrowserMultiply": (12, 13, 14, "tap:10:4"),
    "ExpenseAddMultipleFromMarkor": (
        12,
        13,
        14,
        "type_text:6ce2a93768760cfed2f01db260c064864481162abe8887f9d0b6d94b67d651a8",
    ),
    "MarkorCreateNoteAndSms": (11, 12, 13, "swipe:left"),
    "MarkorMergeNotes": (11, 12, 13, "tap:9:2"),
    "OsmAndTrack": (
        13,
        14,
        15,
        "type_text:f941154c4f94f0851adfa3dcba30aec75e1cb0a153dc3d3fe4ae433b73cf6d53",
    ),
    "RecipeAddMultipleRecipesFromImage": (4, 5, 6, "swipe:up"),
    "RecipeAddMultipleRecipesFromMarkor": (13, 14, 15, "tap:10:8"),
    "RecipeAddMultipleRecipesFromMarkor2": (18, 19, 20, "tap:10:11"),
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _content_sha(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return _canonical_sha(payload)


def _trace_manifest(suite_dir: Path, episode_ids: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    episode_root = suite_dir / "episodes"
    for episode_id in episode_ids:
        root = episode_root / episode_id
        if not root.is_dir():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(suite_dir).as_posix()
            files.append(
                {
                    "relative_path": relative,
                    "episode_id": episode_id,
                    "byte_size": path.stat().st_size,
                    "sha256": _sha(path),
                }
            )
    payload = {
        "schema": "a1r3v3_r2_trace_manifest_v1",
        "suite_id": A1R2_SUITE_ID,
        "episode_count": len(episode_ids),
        "file_count": len(files),
        "total_bytes": sum(item["byte_size"] for item in files),
        "files": files,
        "generation_calls": 0,
        "read_only": True,
    }
    return {**payload, "content_sha256": _content_sha(payload)}


def replay(
    suite_dir: Path,
    *,
    tokenizer_path: Path,
    include_manifest_files: bool = True,
) -> dict[str, Any]:
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_path), local_files_only=True, trust_remote_code=False
    )
    checkpoint_path = suite_dir / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a1r2_valid_entries") or [])
    invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
    entry_by_id = {str(item.get("episode_id")): item for item in entries}
    binding_errors: list[str] = []
    episodes: list[dict[str, Any]] = []
    for summary in summaries:
        episode_id = str(summary["episode_id"])
        entry = entry_by_id.get(episode_id) or {}
        path = suite_dir / "episodes" / episode_id / "episode.json"
        if not path.is_file():
            binding_errors.append(f"episode_missing:{episode_id}")
            continue
        if _sha(path) != entry.get("episode_json_sha256"):
            binding_errors.append(f"episode_hash:{episode_id}")
        if _canonical_sha(summary) != entry.get("summary_sha256"):
            binding_errors.append(f"summary_hash:{episode_id}")
        episode = json.loads(path.read_text(encoding="utf-8"))
        memory = OneShotControllerNonprogressReceiptMemory()
        actual_chars = 0
        actual_tokens = 0
        projected_tokens = 0
        projected_reads: list[dict[str, Any]] = []
        creations: list[dict[str, Any]] = []
        for step in episode.get("steps") or []:
            rendered, read = memory.read({})
            projected_tokens += len(
                tokenizer.encode(rendered, add_special_tokens=False)
            )
            if rendered:
                commit = memory.commit_injection(
                    str(read["ticket_id"]), f"offline:{episode_id}:{step['step']}"
                )
                if commit.get("failure_evidence_injected"):
                    projected_reads.append(
                        {
                            "request_step": int(step["step"]),
                            "receipt_id": read.get("cnr_receipt_id"),
                            "family_key": read.get("failed_action_family"),
                            "second_support_step": read.get(
                                "failure_second_support_step"
                            ),
                            "rendered_chars": len(rendered),
                            "rendered_sha256": commit[
                                "exact_injected_text_sha256"
                            ],
                            "r2_ledger_active": bool(
                                (step.get("memory_read") or {}).get("nonempty")
                            ),
                        }
                    )
            actual_chars += len(
                str((step.get("memory_read") or {}).get("exact_injected_text") or "")
            )
            actual_tokens += len(
                tokenizer.encode(
                    str(
                        (step.get("memory_read") or {}).get(
                            "exact_injected_text"
                        )
                        or ""
                    ),
                    add_special_tokens=False,
                )
            )
            if not step.get("executed"):
                continue
            event = memory.observe_step(
                source_step=int(step["step"]),
                action_summary=str(
                    (step.get("decision") or {}).get("action_summary") or ""
                ),
                canonical_action=(step.get("decision") or {}).get(
                    "canonical_action"
                ),
                transition=step.get("transition") or {},
                source_call_id=str(
                    (step.get("model_call") or {}).get("call_id") or ""
                ),
                source_response_sha256=str(
                    (step.get("model_call") or {}).get("response_sha256") or ""
                ),
                source_screenshot_sha256=str(
                    step.get("before_screenshot_sha256") or ""
                ),
                source_after_screenshot_sha256=str(
                    step.get("after_screenshot_sha256")
                    or (step.get("after") or {}).get("screenshot_sha256")
                    or ""
                ),
            )
            if event.get("cnr_receipt_created"):
                creations.append(
                    {
                        "receipt_id": event["cnr_receipt_id"],
                        "family_key": event["cnr_family_key"],
                        "first_support_step": event["cnr_first_support_step"],
                        "second_support_step": event["cnr_second_support_step"],
                    }
                )
        counters = memory.audit_record()["counters"]
        episodes.append(
            {
                "task_name": summary["task_name"],
                "episode_id": episode_id,
                "episode_json_sha256": entry.get("episode_json_sha256"),
                "reward": summary.get("evaluator_reward"),
                "success": bool(summary.get("success")),
                "model_calls": int(summary.get("model_call_count") or 0),
                "executed_actions": int(
                    summary.get("executed_action_count") or 0
                ),
                "a1r2_actual_rendered_chars": actual_chars,
                "a1r2_actual_rendered_tokens": actual_tokens,
                "projected_nonempty_reads": counters["nonempty_read_count"],
                "projected_rendered_chars": counters["injected_chars"],
                "projected_rendered_tokens": projected_tokens,
                "cnr_receipt_creation_count": counters[
                    "cnr_receipt_creation_count"
                ],
                "cnr_receipt_committed_read_count": counters[
                    "cnr_receipt_committed_read_count"
                ],
                "cnr_creations": creations,
                "cnr_reads": projected_reads,
            }
        )
    totals = {
        "valid_episode_count": len(episodes),
        "invalid_attempt_count": len(invalid_attempts),
        "model_calls": sum(item["model_calls"] for item in episodes),
        "executed_actions": sum(item["executed_actions"] for item in episodes),
        "a1r2_actual_rendered_chars": sum(
            item["a1r2_actual_rendered_chars"] for item in episodes
        ),
        "a1r2_actual_rendered_tokens": sum(
            item["a1r2_actual_rendered_tokens"] for item in episodes
        ),
        "projected_nonempty_reads": sum(
            item["projected_nonempty_reads"] for item in episodes
        ),
        "projected_rendered_chars": sum(
            item["projected_rendered_chars"] for item in episodes
        ),
        "projected_rendered_tokens": sum(
            item["projected_rendered_tokens"] for item in episodes
        ),
        "cnr_receipt_creation_count": sum(
            item["cnr_receipt_creation_count"] for item in episodes
        ),
        "cnr_receipt_committed_read_count": sum(
            item["cnr_receipt_committed_read_count"] for item in episodes
        ),
        "success_task_receipt_creation_count": sum(
            item["cnr_receipt_creation_count"]
            for item in episodes
            if item["task_name"] in SUCCESS_TASKS
        ),
        "success_task_receipt_read_count": sum(
            item["cnr_receipt_committed_read_count"]
            for item in episodes
            if item["task_name"] in SUCCESS_TASKS
        ),
        "failure_tasks_with_receipt": sum(
            item["cnr_receipt_creation_count"] > 0
            for item in episodes
            if item["task_name"] not in SUCCESS_TASKS
        ),
        "non_expense_failure_tasks_with_receipt": sum(
            item["cnr_receipt_creation_count"] > 0
            and not str(item["task_name"]).startswith("Expense")
            for item in episodes
            if item["task_name"] not in SUCCESS_TASKS
        ),
    }
    episode_ids = [str(item["episode_id"]) for item in summaries]
    episode_ids += [
        str(item.get("episode_id"))
        for item in invalid_attempts
        if item.get("episode_id")
    ]
    manifest = _trace_manifest(suite_dir, episode_ids)
    errors = list(binding_errors)
    if len(summaries) != 19 or len(entries) != 19 or len(episodes) != 19:
        errors.append("a1r2_trace_closure")
    if totals["invalid_attempt_count"] != 1 or any(
        not item.get("resolved_by_episode_id") for item in invalid_attempts
    ):
        errors.append("invalid_replacement_binding")
    if totals["model_calls"] != 603 or totals["executed_actions"] != 595:
        errors.append("a1r2_execution_totals")
    if (
        totals["success_task_receipt_creation_count"] != 0
        or totals["success_task_receipt_read_count"] != 0
    ):
        errors.append("six_success_preservation")
    observed_exposures: dict[str, tuple[int, int, int, str]] = {}
    for item in episodes:
        if not item["cnr_creations"]:
            continue
        creation = item["cnr_creations"][0]
        reads = item["cnr_reads"]
        observed_exposures[str(item["task_name"])] = (
            int(creation["first_support_step"]),
            int(creation["second_support_step"]),
            int(reads[0]["request_step"]) if reads else -1,
            str(creation["family_key"]),
        )
    if observed_exposures != EXPECTED_EXPOSURES:
        errors.append("exact_development_exposure_manifest")
    if totals["projected_nonempty_reads"] != 436:
        errors.append("projected_read_budget")
    if totals["projected_rendered_chars"] != 109_185:
        errors.append("projected_char_budget")
    if totals["projected_rendered_tokens"] != 21_870:
        errors.append("projected_token_budget")
    if totals["projected_rendered_chars"] > 109_447:
        errors.append("projected_char_envelope")
    if totals["projected_rendered_tokens"] > 21_966:
        errors.append("projected_token_envelope")
    if any(item["cnr_receipt_creation_count"] > 1 for item in episodes):
        errors.append("episode_one_shot_violation")
    source_files = {
        name: _sha(ROOT / name)
        for name in (
            "implementation/src/raven_m/official_qwen_mobile/a1r3v3_one_shot_cnr.py",
            "implementation/scripts/replay_a1r3v3_one_shot_cnr.py",
            "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json",
        )
    }
    report = {
        "schema": "a1r3v3_one_shot_cnr_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "development_calibration_not_confirmation": True,
        "mechanism_id": MECHANISM_ID,
        "created_at": max(str(item.get("finished_at") or "") for item in summaries),
        "source": {
            "suite_id": A1R2_SUITE_ID,
            "checkpoint_sha256": _sha(checkpoint_path),
            "checkpoint_content_sha256": _canonical_sha(checkpoint),
            "r2_result_sha256": _sha(R2_RESULT_PATH),
            "tokenizer_path": str(tokenizer_path),
            "tokenizer_json_sha256": _sha(tokenizer_path / "tokenizer.json"),
            "source_files": source_files,
            "trace_manifest": (
                manifest
                if include_manifest_files
                else {
                    key: value
                    for key, value in manifest.items()
                    if key != "files"
                }
            ),
        },
        "totals": totals,
        "episodes": episodes,
    }
    report["content_sha256"] = _content_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument(
        "--tokenizer-path", type=Path, default=DEFAULT_TOKENIZER
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "evidence/a1r3_v3/A1R3V3_ONE_SHOT_CNR_OFFLINE_REPLAY_REPORT.json",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=ROOT
        / "evidence/a1r3_v3/A1R3V3_R2_TRACE_MANIFEST.json",
    )
    args = parser.parse_args()
    report = replay(
        args.suite_dir.resolve(),
        tokenizer_path=args.tokenizer_path.resolve(),
        include_manifest_files=True,
    )
    manifest = report["source"]["trace_manifest"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    compact_report = dict(report)
    compact_report["source"] = dict(report["source"])
    compact_report["source"]["trace_manifest"] = {
        key: value for key, value in manifest.items() if key != "files"
    }
    compact_report["source"]["trace_manifest_file_sha256"] = _sha(
        args.manifest_output
    )
    compact_report["content_sha256"] = _content_sha(compact_report)
    args.output.write_text(
        json.dumps(compact_report, ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": compact_report["status"],
                "output": str(args.output),
                "manifest_output": str(args.manifest_output),
                "errors": compact_report["errors"],
                "totals": compact_report["totals"],
            },
            indent=2,
        )
    )
    return 0 if compact_report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
