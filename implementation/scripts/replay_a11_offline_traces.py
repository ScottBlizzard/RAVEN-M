#!/usr/bin/env python3
"""Hash-verify and zero-generation replay the frozen real traces for A11."""

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

from raven_m.official_qwen_mobile.a11_confirmed_route_contraction import (  # noqa: E402
    ConfirmedRouteContractionECOBFMemory,
)
from raven_m.official_qwen_mobile.a11_contract import competent_sparse_gate  # noqa: E402
from replay_a10_offline_traces import verify_materialized  # noqa: E402

MANIFEST = ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json"
SOURCE_SPEC = ROOT / "evidence/a11/A11_OFFLINE_TRACE_SOURCE_SPEC.json"
MECHANISM_SOURCE = ROOT / "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py"


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
    memory = ConfirmedRouteContractionECOBFMemory()
    cache: dict[str, np.ndarray] = {}
    goal = str(episode.get("task_goal") or "")
    first = steps[0]["before"]
    text, _ = memory.read({"goal": goal, "before": {"pixels": _pixels(episode_dir / first["screenshot"], cache, first["screenshot_sha256"])}})
    rendered = [text]
    created: list[dict[str, Any]] = []
    branch_bad: dict[tuple[str, str], list[int]] = {}
    for index, step in enumerate(steps):
        before_ref, after_ref = step["before"], step["after"]
        before = _pixels(episode_dir / before_ref["screenshot"], cache, before_ref["screenshot_sha256"])
        after = _pixels(episode_dir / after_ref["screenshot"], cache, after_ref["screenshot_sha256"])
        decision = step.get("decision") or {}
        action = dict(decision.get("canonical_action") or (step.get("mapped_action") or {}).get("canonical") or {})
        result = memory.observe_step(
            source_step=index, action_summary=str(decision.get("action_summary") or ""), canonical_action=action,
            before={"pixels": before}, after={"pixels": after},
            source_response_sha256=str((step.get("model_call") or {}).get("response_sha256") or ""),
        )
        for trigger_id in result.get("trigger_ids_enqueued") or []:
            trigger = next((item for item in memory.trigger_candidates if item.trigger_id == trigger_id), None)
            if trigger is not None:
                created.append({"step": index, "kind": trigger.kind, "frontier_id": trigger.query_frontier_id, "support_count": trigger.support_count})
        if str(result.get("immediate_outcome") or "").startswith("NO_PROGRESS"):
            key = (str(result["source_frontier_id"]), str(result["branch_id"]))
            branch_bad.setdefault(key, []).append(index)
        text, _ = memory.read({"goal": goal, "before": {"pixels": after}})
        rendered.append(text)
    audit = memory.audit_record()
    reads = list((audit.get("reads") or {}).get("read_events") or [])
    qualifying: list[dict[str, Any]] = []
    for (frontier, branch), bad_steps in branch_bad.items():
        if len(bad_steps) >= 2:
            qualifying.append({"frontier_id": frontier, "branch_id": branch, "deadline": bad_steps[2] if len(bad_steps) >= 3 else bad_steps[1]})
    normal_navigation_violations = sum(
        1 for event in reads
        if event.get("trigger_kind") == "CONFIRMED_ROUTE_TRAP"
        and int(event.get("support_count") or 0) < 2
    )
    return {
        "role": record["role"], "episode_id": record["episode_id"], "task_name": episode.get("task_name"),
        "replayed_actions": len(steps), "anchor_count": int((audit.get("goal") or {}).get("anchor_count") or 0),
        "constraint_anchor_count": int((audit.get("goal") or {}).get("constraint_anchor_count") or 0),
        "nonempty_read_count": int((audit.get("reads") or {}).get("nonempty_read_count") or 0),
        "rendered_chars": sum(len(item) for item in rendered), "read_events": reads,
        "created_trigger_steps": created, "qualifying_segments": qualifying,
        "normal_navigation_exemption_violation_count": normal_navigation_violations,
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
        return {"schema": "a11_offline_replay_report_v1", "status": "fail", "generation_calls": 0, "verification": verification, "errors": errors}
    manifest = _load(MANIFEST)
    episodes = [replay_episode(trace_root, record) for record in manifest["records"]]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for item in episodes:
        by_role.setdefault(item["role"], []).append(item)
    competent = [item for item in by_role["a0"] if item["task_name"] != "RecipeDeleteMultipleRecipesWithConstraint"]
    sparse = competent_sparse_gate(competent)
    if sparse["status"] != "pass":
        errors.append("a0_competent_sparse_gate_failed")
    a6_segments = sum(len(item["qualifying_segments"]) for item in by_role["a6"])
    a6_qualified = 0
    for item in by_role["a6"]:
        for segment in item["qualifying_segments"]:
            a6_qualified += any(
                int(event.get("step", -1)) <= int(segment["deadline"]) + 1
                and int(event.get("step", -1)) >= int(segment["deadline"])
                and str(event.get("frontier_id")) == str(segment["frontier_id"])
                and str((event.get("retrieved_branch_ids") or [""])[0]) == str(segment["branch_id"])
                and event.get("trigger_kind") in {"BAD_BRANCH_REPEAT", "CONFIRMED_ROUTE_TRAP", "CONTRACTED_FRONTIER"}
                and int(event.get("support_count") or 0) >= 2
                for event in item["read_events"]
            )
    a6_rate = a6_qualified / a6_segments if a6_segments else 0.0
    if a6_segments < 20 or a6_rate < .80:
        errors.append("a6_confirmed_segment_timing_gate_failed")
    for role in ("a8v2_expense", "a9_retro"):
        item = by_role[role][0]
        earliest = min((int(segment["deadline"]) for segment in item["qualifying_segments"]), default=-1)
        relevant_reads = [
            event for event in item["read_events"]
            if earliest >= 0
            and int(event.get("step", -1)) <= earliest + 1
            and event.get("trigger_kind") in {"BAD_BRANCH_REPEAT", "CONFIRMED_ROUTE_TRAP", "CONTRACTED_FRONTIER"}
            and int(event.get("support_count") or 0) >= 2
        ]
        if not item["qualifying_segments"] or not relevant_reads:
            errors.append(f"{role}_independent_segment_gate_failed")
    recipe = by_role["a1_recipe"][0]
    if recipe["constraint_anchor_count"] != 1 or recipe["nonempty_read_count"] > 2:
        errors.append("recipe_constraint_or_sparse_read_gate_failed")
    if any(item["serialized_audit_bytes"] > 131072 for item in episodes):
        errors.append("audit_capacity_gate_failed")
    forbidden = [item for item in episodes if int((item["causal_boundary"] or {}).get("model_calls_added") or 0) or bool((item["causal_boundary"] or {}).get("evaluator_used_for_decision")) or bool((item["causal_boundary"] or {}).get("hidden_ui_used_for_decision")) or bool((item["causal_boundary"] or {}).get("future_information_used")) or bool((item["causal_boundary"] or {}).get("guard_enabled")) or int((item["causal_boundary"] or {}).get("action_override_count") or 0) or int((item["causal_boundary"] or {}).get("forced_termination_count") or 0)]
    if forbidden:
        errors.append("causal_boundary_gate_failed")
    return {
        "schema": "a11_offline_replay_report_v1", "status": "pass" if not errors else "fail", "generation_calls": 0,
        "replay_source_sha256": _sha(Path(__file__)), "mechanism_source_sha256": _sha(MECHANISM_SOURCE),
        "source_spec_sha256": _sha(SOURCE_SPEC), "manifest_sha256": _sha(MANIFEST), "verification": verification,
        "episode_count": len(episodes), "competent_sparse_gate": sparse, "a6_qualifying_segments": a6_segments,
        "a6_qualified_segments": a6_qualified, "a6_qualification_rate": a6_rate, "episodes": episodes, "errors": errors,
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
