"""Validate a completed A2-v1r1 suite and produce paired diagnostic reports."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)
    args = parser.parse_args()
    suite = args.suite_dir.resolve()
    aggregate = _load(suite / "aggregate.json")
    checkpoint = _load(suite / "checkpoint.json")
    signature = _load(suite / "run_signature.json")
    ledger = _load(args.ledger.resolve())
    expected = [(str(item[0]), int(item[1])) for item in signature["ordered_expected_keys"]]
    entries = checkpoint.get("valid_entries") or []
    if checkpoint.get("status") != "complete" or len(entries) != 19:
        raise RuntimeError("A2 suite is not an exact completed 19-entry checkpoint")
    if (
        any(not item.get("resolved_by_episode_id") for item in aggregate.get("invalid_attempts") or [])
        or aggregate.get("orphan_episode_directories")
    ):
        raise RuntimeError("A2 suite contains unresolved invalid attempts or orphan episodes")
    a2_by_task: dict[str, dict[str, Any]] = {}
    support_audit = []
    for expected_key, entry in zip(expected, entries, strict=True):
        key = (str(entry["task_name"]), int(entry["seed"]))
        if key != expected_key:
            raise RuntimeError("A2 checkpoint order/key drift")
        path = suite / entry["episode_json_relative_path"]
        if _hash(path) != entry["episode_json_sha256"]:
            raise RuntimeError(f"A2 episode hash drift: {path}")
        episode = _load(path)
        a2_by_task[key[0]] = episode
        for step in episode.get("steps") or []:
            state = ((step.get("memory_write") or {}).get("state") or {})
            verified = str(state.get("verified") or "none").strip()
            if verified.casefold() == "none":
                label = "none"
            else:
                # Screenshot support is deliberately not inferred from hidden UI or
                # controller metadata. Non-none assertions remain a manual review item.
                label = "ambiguous"
            support_audit.append(
                {
                    "task_name": key[0],
                    "step": step.get("step"),
                    "verified_assertion": verified,
                    "support_label": label,
                    "eligible_for_memory_supported_candidate": label == "supported",
                    "before_screenshot": step.get("before_screenshot"),
                }
            )
    a1_by_task = {item["task_name"]: item["A1"] for item in ledger["tasks"]}
    rows = []
    for task_name, seed in expected:
        episode = a2_by_task[task_name]
        a1 = a1_by_task[task_name]
        guard_blocks = int((episode.get("cost_guard") or {}).get("block_count") or 0)
        memory_reads = int((episode.get("memory_mechanism") or {}).get("nonempty_read_count") or 0)
        improved = bool(episode["success"]) and not bool(a1["success"])
        task_support = [item for item in support_audit if item["task_name"] == task_name and item["support_label"] != "none"]
        all_supported = bool(task_support) and all(item["support_label"] == "supported" for item in task_support)
        if guard_blocks and memory_reads:
            exposure = "mixed_memory_and_guard"
        elif guard_blocks:
            exposure = "guard_exposed"
        elif memory_reads:
            exposure = "memory_exposed"
        else:
            exposure = "unattributed"
        rows.append(
            {
                "task_name": task_name,
                "seed": seed,
                "A0_success": next(item["A0"]["success"] for item in ledger["tasks"] if item["task_name"] == task_name),
                "A1_success": a1["success"],
                "A2_success": episode["success"],
                "A2_reward": episode["evaluator_reward"],
                "memory_nonempty_reads": memory_reads,
                "guard_blocks": guard_blocks,
                "exposure": exposure,
                "memory_supported_candidate": improved and memory_reads > 0 and guard_blocks == 0 and all_supported,
            }
        )
    a2_success = sum(int(row["A2_success"]) for row in rows)
    a2_tokens = int(aggregate["token_usage"]["total_tokens"])
    a2_elapsed = float(aggregate["exact_valid_elapsed_seconds"])
    a1 = ledger["summaries"]["A1"]
    report = {
        "schema": "a2_v1r1_paired_validation_v1",
        "status": "pass",
        "suite_dir": str(suite),
        "suite_run_signature_sha256": aggregate["run_signature_sha256"],
        "ledger_sha256": _hash(args.ledger.resolve()),
        "accuracy_improvement": a2_success > 5,
        "cost_improvement": a2_tokens < 3_464_267 and a2_elapsed < float(a1["valid_elapsed_seconds"]),
        "A2_success_count": a2_success,
        "A2_total_tokens": a2_tokens,
        "A2_exact_valid_elapsed_seconds": a2_elapsed,
        "claim_limits": [
            "single seed descriptive paired diagnostic only",
            "verified means model-authored screenshot assertion, not objective confirmation",
            "A2-v1r1 is a compound memory-plus-guard arm",
            "guard-exposed gains are not pure memory candidates",
            "guard blocks save Android execution, not the already-consumed model proposal call",
        ],
        "rows": rows,
        "verified_assertion_support_audit": support_audit,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# A2-v1r1 paired validation", "",
        f"- Accuracy: {a2_success}/19 (A1: 5/19); improvement claim: {report['accuracy_improvement']}",
        f"- Tokens: {a2_tokens:,} (A1: 3,464,267)",
        f"- Exact valid elapsed: {a2_elapsed:.1f}s (A1: {float(a1['valid_elapsed_seconds']):.1f}s)",
        f"- Joint cost improvement claim: {report['cost_improvement']}", "",
        "| Task | A0 | A1 | A2 | Exposure | Memory-supported candidate |", "|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['task_name']} | {int(row['A0_success'])} | {int(row['A1_success'])} | {int(row['A2_success'])} | {row['exposure']} | {row['memory_supported_candidate']} |")
    args.md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "json": str(args.json_output), "markdown": str(args.md_output)}, indent=2))


if __name__ == "__main__":
    main()
