#!/usr/bin/env python3
"""Hash-verify and zero-generation replay the frozen real traces for A10-v2."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import (  # noqa: E402
    EvidenceMaturedObligationBranchFrontierMemory,
)
from replay_a10_offline_traces import verify_materialized  # noqa: E402

MANIFEST = ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json"
SOURCE_SPEC = ROOT / "evidence/a10_v2/A10_V2_OFFLINE_TRACE_SOURCE_SPEC.json"
MECHANISM_SOURCE = ROOT / "implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pixels(path: Path, cache: dict[str, np.ndarray], digest: str) -> np.ndarray:
    if digest not in cache:
        with Image.open(path) as image:
            cache[digest] = np.asarray(image.convert("RGB"), dtype=np.uint8)
        while len(cache) > 20:
            del cache[next(iter(cache))]
    return cache[digest]


def replay_episode(trace_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    episode_dir = trace_root / record["role"] / "episodes" / record["episode_id"]
    episode = _load(episode_dir / "episode.json")
    steps = [item for item in episode.get("steps") or [] if item.get("executed")]
    if not steps:
        raise RuntimeError(f"empty episode: {record['episode_id']}")
    memory = EvidenceMaturedObligationBranchFrontierMemory()
    cache: dict[str, np.ndarray] = {}
    goal = str(episode.get("task_goal") or "")
    first = steps[0]["before"]
    text, _ = memory.read({"goal": goal, "before": {"pixels": _pixels(episode_dir / first["screenshot"], cache, first["screenshot_sha256"])}})
    rendered = [text]
    created: list[dict[str, Any]] = []
    second_bad_steps: list[int] = []
    branch_bad: dict[tuple[str, str], int] = {}
    for index, step in enumerate(steps):
        before_ref, after_ref = step["before"], step["after"]
        before = _pixels(episode_dir / before_ref["screenshot"], cache, before_ref["screenshot_sha256"])
        after = _pixels(episode_dir / after_ref["screenshot"], cache, after_ref["screenshot_sha256"])
        decision = step.get("decision") or {}
        action = dict(decision.get("canonical_action") or (step.get("mapped_action") or {}).get("canonical") or {})
        result = memory.observe_step(
            source_step=index,
            action_summary=str(decision.get("action_summary") or ""),
            canonical_action=action,
            before={"pixels": before},
            after={"pixels": after},
            source_response_sha256=str((step.get("model_call") or {}).get("response_sha256") or ""),
        )
        for trigger_id in result.get("trigger_ids_enqueued") or []:
            trigger = next((item for item in memory.trigger_candidates if item.trigger_id == trigger_id), None)
            if trigger is not None:
                created.append({"step": index, "kind": trigger.kind, "frontier_id": trigger.query_frontier_id})
        if str(result.get("immediate_outcome") or "").startswith("NO_PROGRESS"):
            key = (str(result["source_frontier_id"]), str(result["branch_id"]))
            branch_bad[key] = branch_bad.get(key, 0) + 1
            if branch_bad[key] == 2:
                second_bad_steps.append(index)
        text, _ = memory.read({"goal": goal, "before": {"pixels": after}})
        rendered.append(text)
    audit = memory.audit_record()
    reads = list((audit.get("reads") or {}).get("read_events") or [])
    mature_count = int((audit.get("closed_route_watches") or {}).get("matured_count") or 0) + sum(
        int(value) for value in (audit.get("triggers") or {}).get("created_counts_by_kind", {}).values()
    )
    return {
        "role": record["role"], "episode_id": record["episode_id"], "task_name": episode.get("task_name"),
        "replayed_actions": len(steps), "anchor_count": int((audit.get("goal") or {}).get("anchor_count") or 0),
        "group_count": int((audit.get("goal") or {}).get("group_count") or 0),
        "nonempty_read_count": int((audit.get("reads") or {}).get("nonempty_read_count") or 0),
        "mature_trigger_count": mature_count, "read_events": reads, "created_trigger_steps": created,
        "created_counts_by_kind": (audit.get("triggers") or {}).get("created_counts_by_kind") or {},
        "read_events": reads,
        "max_rendered_chars": max((len(item) for item in rendered), default=0),
        "max_rendered_utf8_bytes": max((len(item.encode()) for item in rendered), default=0),
        "second_bad_steps": second_bad_steps,
        "serialized_audit_bytes": int((audit.get("capacity") or {}).get("serialized_audit_bytes") or 0),
        "causal_boundary": audit.get("causal_boundary") or {},
    }


def verify_and_replay(trace_root: Path) -> dict[str, Any]:
    verification = verify_materialized(trace_root, MANIFEST)
    errors = list(verification.get("errors") or [])
    source_spec = _load(SOURCE_SPEC)
    if _sha(MANIFEST) != source_spec.get("materialized_manifest_sha256"):
        errors.append("manifest_source_spec_hash_mismatch")
    if errors:
        return {"schema": "a10_v2_offline_replay_report_v1", "status": "fail", "generation_calls": 0, "verification": verification, "errors": errors}
    manifest = _load(MANIFEST)
    episodes = [replay_episode(trace_root, record) for record in manifest["records"]]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for item in episodes:
        by_role.setdefault(item["role"], []).append(item)
    competent = [item for item in by_role["a0"] if item["task_name"] != "RecipeDeleteMultipleRecipesWithConstraint"]
    if len(competent) != 4 or any(item["nonempty_read_count"] or item["mature_trigger_count"] or item["max_rendered_chars"] for item in competent):
        errors.append("a0_absolute_silence_and_no_maturity_gate_failed")
    frozen_reference = _load(ROOT / "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json")
    reference_by_episode = {
        str(item["episode_id"]): list(item.get("loop_qualification_records") or [])
        for item in frozen_reference.get("episodes") or []
        if item.get("role") == "a6"
    }
    a6_segments = sum(len(items) for items in reference_by_episode.values())
    a6_timely = 0
    a6_t12 = 0
    for item in by_role["a6"]:
        for reference in reference_by_episode.get(str(item["episode_id"]), []):
            deadline = int(reference["second_no_progress_step"])
            reads = [
                event for event in item["read_events"]
                if int(event.get("step", -1)) <= deadline + 1
                and int(event.get("step", -1)) >= deadline
                and event.get("trigger_kind") in {"BAD_BRANCH_REPEAT", "MATURED_CLOSED_ROUTE_STAGNATION", "MATURED_FRONTIER_EXHAUSTION"}
                and str(event.get("frontier_id")) == str(reference["source_frontier_id"])
                and str((event.get("retrieved_branch_ids") or [""])[0]) == str(reference["branch_id"])
            ]
            a6_timely += bool(reads)
            a6_t12 += any(event["trigger_kind"] in {"BAD_BRANCH_REPEAT", "MATURED_CLOSED_ROUTE_STAGNATION"} for event in reads)
    if a6_segments < 23 or a6_timely < 20 or a6_t12 < 18:
        errors.append("a6_timing_or_kind_gate_failed")
    a8 = by_role["a8v2_expense"][0]
    a8_relevant = [event for event in a8["read_events"] if int(event.get("step", -1)) <= 14 and event.get("trigger_kind") in {"BAD_BRANCH_REPEAT", "MATURED_CLOSED_ROUTE_STAGNATION", "MATURED_FRONTIER_EXHAUSTION"}]
    if not a8_relevant or a8["mature_trigger_count"] > 13 or a8["nonempty_read_count"] > 5:
        errors.append("a8_exposure_gate_failed")
    a9 = by_role["a9_retro"][0]
    a9_relevant = [event for event in a9["read_events"] if int(event.get("step", -1)) <= 23 and event.get("trigger_kind") in {"BAD_BRANCH_REPEAT", "MATURED_CLOSED_ROUTE_STAGNATION", "VALUE_REENTRY_AFTER_BAD_OUTCOME"}]
    if not a9_relevant or a9["mature_trigger_count"] > 22 or a9["nonempty_read_count"] > 5:
        errors.append("a9_exposure_or_pure_t3_gate_failed")
    recipe = by_role["a1_recipe"][0]
    if recipe["group_count"] != 1 or recipe["anchor_count"] < 2 or recipe["nonempty_read_count"] > 1:
        errors.append("recipe_structure_or_sparse_read_gate_failed")
    if any(item["serialized_audit_bytes"] > 131072 for item in episodes):
        errors.append("audit_capacity_gate_failed")
    forbidden = [item for item in episodes if any(bool((item["causal_boundary"] or {}).get(key)) for key in ("evaluator_used", "hidden_ui_used", "future_information_used", "guard_enabled")) or int((item["causal_boundary"] or {}).get("model_calls_added") or 0)]
    if forbidden:
        errors.append("causal_boundary_gate_failed")
    return {
        "schema": "a10_v2_offline_replay_report_v1", "status": "pass" if not errors else "fail", "generation_calls": 0,
        "replay_source_sha256": _sha(Path(__file__)), "mechanism_source_sha256": _sha(MECHANISM_SOURCE),
        "source_spec_sha256": _sha(SOURCE_SPEC), "manifest_sha256": _sha(MANIFEST), "verification": verification,
        "episode_count": len(episodes), "a6_qualifying_segments": a6_segments, "a6_timely_segments": a6_timely,
        "a6_t1_t2_segments": a6_t12, "episodes": episodes, "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify_and_replay(args.trace_root.resolve())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "episodes"}, indent=2, default=str))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
