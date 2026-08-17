from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image


R2_RESULT = "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"
R2_SUITE = "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
WINDOW = 12
MIN_REMAINING_ACTIONS = 6
SUCCESS_TASKS = {
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(data).hexdigest()


def file_row(root: Path, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": digest(raw),
    }


@lru_cache(maxsize=4096)
def visible_fingerprint(path: Path) -> str:
    with Image.open(path) as image:
        pixels = np.asarray(image.convert("RGB"))
    top = int(round(pixels.shape[0] * 0.04))
    bottom = int(round(pixels.shape[0] * 0.96))
    crop = np.ascontiguousarray(pixels[top:bottom, :, :3])
    descriptor = f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    return digest(descriptor)


def round_bucket(value: Any, width: float = 0.05) -> str:
    number = min(1.0, max(0.0, float(value)))
    quantized = int(np.floor(number / width + 0.5 + 1e-12)) * width
    return f"{min(1.0, quantized):.2f}"


def route_action_key(action: dict[str, Any] | None) -> str | None:
    if not isinstance(action, dict):
        return None
    kind = str(action.get("type") or "")
    if kind in {"tap", "long_press"}:
        return f"{kind}:{round_bucket(action.get('x'))}:{round_bucket(action.get('y'))}"
    if kind == "swipe":
        dx = float(action.get("x2")) - float(action.get("x"))
        dy = float(action.get("y2")) - float(action.get("y"))
        direction = (
            "right"
            if abs(dx) >= abs(dy) and dx >= 0
            else "left"
            if abs(dx) >= abs(dy)
            else "down"
            if dy >= 0
            else "up"
        )
        return f"swipe:{direction}"
    if kind == "type_text":
        text = " ".join(str(action.get("text") or "").split()).casefold()
        return f"type_text:{digest(text.encode('utf-8'))[:16]}" if text else None
    if kind in {"press_back", "press_home", "press_enter", "press_recents", "wait"}:
        return kind
    return None


def rle(values: Iterable[str]) -> tuple[str, ...]:
    output: list[str] = []
    for value in values:
        if not output or output[-1] != value:
            output.append(value)
    return tuple(output)


def family(task_name: str) -> str:
    for prefix in ("Expense", "Retro", "SimpleCalendar", "SportsTracker", "Recipe", "OsmAnd", "Browser", "Markor", "SaveCopy"):
        if task_name.startswith(prefix):
            return prefix
    return "Other"


def make_policy_episode(root: Path, episode_row: dict[str, Any]) -> dict[str, Any]:
    episode_dir = root / R2_SUITE / "episodes" / episode_row["episode_id"]
    episode_path = episode_dir / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    if digest(episode_path.read_bytes()) != episode_row["episode_json_sha256"]:
        raise RuntimeError(f"episode hash mismatch: {episode_row['episode_id']}")
    transitions: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    raw_files = [file_row(root, episode_path)]
    events = episode_dir / "events.jsonl"
    if events.exists():
        raw_files.append(file_row(root, events))
    for step in episode["steps"]:
        ordinal = int(step["step"])
        before_png = episode_dir / f"step_{ordinal:03d}_before.png"
        raw_files.append(file_row(root, before_png))
        before_state = visible_fingerprint(before_png)
        decision = step.get("decision") or {}
        action = decision.get("canonical_action")
        calls.append(
            {
                "step": ordinal,
                "state": before_state,
                "route_action_key": route_action_key(action),
                "canonical_action": action,
                "terminal": bool(decision.get("terminal_status")),
                "request_sha256": (step.get("model_call") or {}).get("request_sha256"),
                "response_sha256": (step.get("model_call") or {}).get("response_sha256"),
            }
        )
        if step.get("executed"):
            after_png = episode_dir / f"step_{ordinal:03d}_after.png"
            raw_files.append(file_row(root, after_png))
            transitions.append(
                {
                    "step": ordinal,
                    "before": before_state,
                    "after": visible_fingerprint(after_png),
                    "route_action_key": route_action_key(action),
                }
            )
    return {
        "episode_id": episode["episode_id"],
        "native_max_steps": int(episode_row["native_max_steps"]),
        "executed_actions": int(episode["executed_action_count"]),
        "calls": calls,
        "transitions": transitions,
        "raw_files": sorted(raw_files, key=lambda row: row["path"]),
    }


def closed_routes(history: list[dict[str, Any]], anchor: str) -> dict[tuple[str, ...], list[tuple[int, int]]]:
    routes: dict[tuple[str, ...], list[tuple[int, int]]] = {}
    for left in range(len(history)):
        if history[left]["before"] != anchor:
            continue
        actions: list[str] = []
        for right in range(left, len(history)):
            key = history[right]["route_action_key"]
            if key is None:
                break
            actions.append(key)
            compressed = rle(actions)
            if len(compressed) > 6:
                break
            if history[right]["after"] == anchor and 2 <= len(compressed) <= 6:
                routes.setdefault(compressed, []).append((left, right))
    return routes


def detect_events(policy: dict[str, Any]) -> list[dict[str, Any]]:
    transitions = policy["transitions"]
    by_step = {row["step"]: row for row in transitions}
    consumed: set[tuple[str, str, tuple[str, ...]]] = set()
    events: list[dict[str, Any]] = []
    for call in policy["calls"]:
        step = call["step"]
        current_key = call["route_action_key"]
        if call["terminal"] or current_key is None:
            continue
        history = [
            by_step[s]
            for s in sorted(by_step)
            if max(0, step - WINDOW) <= s < step
        ]
        anchor = call["state"]
        remaining = policy["native_max_steps"] - step
        if remaining < MIN_REMAINING_ACTIONS:
            continue
        stationary = [
            row
            for row in history
            if row["before"] == anchor
            and row["after"] == anchor
            and row["route_action_key"] == current_key
        ]
        if len(stationary) >= 2:
            key = ("E1_STATIONARY_REPEAT", anchor, (current_key,))
            if key not in consumed:
                events.append(
                    {
                        "event_type": key[0],
                        "eligible_step": step,
                        "anchor_sha256": anchor,
                        "blocked_route": list(key[2]),
                        "support_steps": [stationary[-2]["step"], stationary[-1]["step"]],
                        "remaining_native_actions": remaining,
                        "base_would_reenter": True,
                    }
                )
                consumed.add(key)
        for signature, occurrences in closed_routes(history, anchor).items():
            nonoverlap = []
            for occurrence in occurrences:
                if not nonoverlap or occurrence[0] > nonoverlap[-1][1]:
                    nonoverlap.append(occurrence)
            if len(nonoverlap) < 2 or signature[0] != current_key:
                continue
            key = ("E2_CLOSED_ROUTE_REPEAT", anchor, signature)
            if key in consumed:
                continue
            support = nonoverlap[-2:]
            events.append(
                {
                    "event_type": key[0],
                    "eligible_step": step,
                    "anchor_sha256": anchor,
                    "blocked_route": list(signature),
                    "support_steps": [
                        [history[left]["step"], history[right]["step"]]
                        for left, right in support
                    ],
                    "remaining_native_actions": remaining,
                    "base_would_reenter": True,
                }
            )
            consumed.add(key)
    for event in events:
        event["event_id"] = "ere_" + digest(
            {"episode_id": policy["episode_id"], **event}
        )[:20]
    return sorted(events, key=lambda row: (row["eligible_step"], row["event_id"]))


def detect_events_reference(policy: dict[str, Any]) -> list[dict[str, Any]]:
    # Independent wrapper: reconstruct each prefix and invoke the detector on a
    # synthetic policy truncated at that request.  Deduplication is performed
    # by event ID after concatenation rather than by the primary scan.
    all_events: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for call_index in range(len(policy["calls"])):
        call = policy["calls"][call_index]
        prefix = {
            **policy,
            "calls": [call],
            "transitions": [
                row for row in policy["transitions"] if row["step"] < call["step"]
            ],
        }
        for event in detect_events(prefix):
            key = (
                event["event_type"],
                event["anchor_sha256"],
                tuple(event["blocked_route"]),
            )
            all_events.setdefault(key, event)
    return sorted(all_events.values(), key=lambda row: (row["eligible_step"], row["event_id"]))


def build(root: Path) -> dict[str, Any]:
    result_path = root / R2_RESULT
    scored = json.loads(result_path.read_text(encoding="utf-8"))["a1r2_result"]
    policy_episodes = [make_policy_episode(root, row) for row in scored["episodes"]]
    manifest_rows = sorted(
        (file for episode in policy_episodes for file in episode["raw_files"]),
        key=lambda row: row["path"],
    )
    m0 = digest(manifest_rows)
    policy_projection = [
        {key: episode[key] for key in ("episode_id", "native_max_steps", "executed_actions", "calls", "transitions")}
        for episode in policy_episodes
    ]
    m1 = digest({"m0": m0, "policy": policy_projection})
    detector_identity = {
        "state": "A8 exact middle-92%-RGB SHA-256",
        "route_action": "A1-R9 0.05 half-up coordinate family",
        "window": WINDOW,
        "route_rle_length": [2, 6],
        "minimum_supports": 2,
        "minimum_remaining_native_actions": MIN_REMAINING_ACTIONS,
    }
    m2 = digest({"m1": m1, "detector": detector_identity})
    unlabeled = []
    for episode in policy_episodes:
        primary = detect_events(episode)
        reference = detect_events_reference(episode)
        if primary != reference:
            raise RuntimeError(f"independent detector mismatch: {episode['episode_id']}")
        unlabeled.append({"episode_id": episode["episode_id"], "events": primary})
    m3 = digest({"m2": m2, "unlabeled_event_ledger": unlabeled})

    labels = {row["episode_id"]: row for row in scored["episodes"]}
    joined = []
    for row in unlabeled:
        label = labels[row["episode_id"]]
        events = row["events"]
        joined.append(
            {
                "episode_id": row["episode_id"],
                "task_name": label["task_name"],
                "task_family": family(label["task_name"]),
                "success": bool(label["success"]),
                "reward": label["reward"],
                "event_count": len(events),
                "first_event_step": events[0]["eligible_step"] if events else None,
                "events": events,
            }
        )
    m4 = digest({"m3": m3, "label_join": joined})
    success_events = [row for row in joined if row["success"] and row["event_count"]]
    failed_events = [row for row in joined if not row["success"] and row["event_count"]]
    failed_families = sorted({row["task_family"] for row in failed_events})
    errors = []
    if len(policy_episodes) != 19:
        errors.append("not_19_formal_r2_episodes")
    if success_events:
        errors.append("r2_success_call_gated_ere_nonzero")
    if len(failed_events) < 4:
        errors.append("failed_task_coverage_below_4")
    if len(failed_families) < 3:
        errors.append("failed_family_coverage_below_3")
    payload: dict[str, Any] = {
        "schema": "p1_tcra_r2_zero_generation_trace_audit_v1",
        "status": "PASS" if not errors else "PREFLIGHT_INVALID_NO_LIVE",
        "errors": errors,
        "generation_calls": 0,
        "source_commit": "152f3b92f6ad1d87f20fa0e6a54101a0d2c07711",
        "raw_result": file_row(root, result_path),
        "detector_identity": detector_identity,
        "hash_chain": {"M0": m0, "M1": m1, "M2": m2, "M3": m3, "M4": m4},
        "raw_manifest": {
            "file_count": len(manifest_rows),
            "total_bytes": sum(row["size_bytes"] for row in manifest_rows),
            "rows": manifest_rows,
        },
        "unlabeled_event_ledger": unlabeled,
        "label_join": joined,
        "summary": {
            "formal_episode_count": len(policy_episodes),
            "success_task_event_count": len(success_events),
            "failed_task_event_count": len(failed_events),
            "failed_task_families": failed_families,
            "failed_task_rows": [row["task_name"] for row in failed_events],
            "live_authorized": not errors,
        },
        "decision": (
            "GO_IMPLEMENT_AND_RUN_FIXED_SEVEN_TASK_GATE"
            if not errors
            else "NO_LIVE_SEAL_DIRECTION_AND_CONTINUE_P2"
        ),
    }
    payload["content_sha256"] = digest(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/p1_failure_recovery/P1_TCRA_R2_ZERO_GENERATION_AUDIT.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build(root)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": payload["status"], "summary": payload["summary"], "content_sha256": payload["content_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
