"""Zero-generation, zero-emulator replay of the 19 frozen first-seed records."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.public_frameworks.mobileuse.action_adapter import MobileUseActionAdapter  # noqa: E402


FROZEN_ORDER = [
    "H06", "H04", "H03", "H15", "H11", "H13", "H02", "H05", "H10",
    "H12", "H08", "H16", "H14", "H19", "H09", "H18", "H17", "H01", "H07",
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def structured_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def replay(
    *,
    combined: Path,
    manifest: Path,
    handoff_audit: Path,
    output: Path,
) -> dict[str, Any]:
    combined_data = load_json(combined)
    manifest_data = load_json(manifest)
    instances = {
        item["task_class"]: item
        for item in manifest_data["instances"]
        if int(item["task_seed"]) == 20260806
    }
    id_to_task = {item["task_id"]: item["task_class"] for item in instances.values()}
    selected = [
        item for item in combined_data["episodes"]
        if int(item["seed"]) == 20260806 and item.get("scientifically_eligible")
    ]
    if len(selected) != 19 or len({item["task_name"] for item in selected}) != 19:
        raise RuntimeError("Expected exactly 19 unique eligible first-seed episodes")
    selected_by_task = {item["task_name"]: item for item in selected}
    ordered_tasks = [id_to_task[task_id] for task_id in FROZEN_ORDER]
    if set(ordered_tasks) != set(selected_by_task):
        raise RuntimeError("Frozen task order does not match selected first-seed records")

    adapter = MobileUseActionAdapter()
    action_counts: Counter[str] = Counter()
    allowed_counts: Counter[str] = Counter()
    prohibited_counts: Counter[str] = Counter()
    episodes: list[dict[str, Any]] = []
    total_steps = 0
    total_reward = 0.0
    successes = 0
    for task_name in ordered_tasks:
        summary = selected_by_task[task_name]
        source_summary = Path(summary["source_summary"])
        episode_dir = source_summary.parent / "episodes" / summary["episode_id"]
        episode_path = episode_dir / "episode.json"
        if not episode_path.is_file():
            raise FileNotFoundError(episode_path)
        episode = load_json(episode_path)
        spec = instances[task_name]
        if episode["task_name"] != task_name or int(episode["seed"]) != 20260806:
            raise RuntimeError(f"Episode identity mismatch: {episode_path}")
        events_path = episode_dir / "events.jsonl"
        first_event = json.loads(
            events_path.read_text(encoding="utf-8").splitlines()[0]
        )
        initial_goal = first_event.get("task_goal_before_initialization")
        if sha256(str(initial_goal).encode("utf-8")).hexdigest() != spec["goal_hash"]:
            raise RuntimeError(f"Goal hash mismatch: {task_name}")
        suite_manifest = load_json(source_summary.parent / "manifest.snapshot.json")
        suite_spec = next(
            item for item in suite_manifest["instances"]
            if item["task_class"] == task_name and int(item["task_seed"]) == 20260806
        )
        if (
            suite_spec["task_params_hash"] != spec["task_params_hash"]
            or suite_spec["goal_hash"] != spec["goal_hash"]
        ):
            raise RuntimeError(f"Frozen suite-manifest mismatch: {task_name}")
        if int(episode["step_count"]) > int(spec["native_max_steps"]):
            raise RuntimeError(f"Native budget exceeded: {task_name}")

        episode_allowed = 0
        episode_prohibited = 0
        layer_errors: list[str] = []
        packages: list[str] = []
        cross_app_transitions = 0
        unchanged_steps = 0
        for index, step in enumerate(episode["steps"]):
            expected_layers = {
                "L0_runtime", "L1_perception_grounding", "L2_protocol_coordinate",
                "L3_execution", "L4_transition_progress", "L5_completion_evaluator",
            }
            missing = expected_layers - set(step.get("layers", {}))
            if missing:
                layer_errors.append(f"step_{index}:missing:{sorted(missing)}")
            for side in ("before", "after"):
                snapshot = step.get(side)
                if not snapshot:
                    continue
                screenshot = episode_dir / snapshot["screenshot"]
                if digest(screenshot) != snapshot["screenshot_sha256"]:
                    raise RuntimeError(f"Screenshot hash mismatch: {screenshot}")
                package = snapshot.get("foreground", {}).get("package")
                if package:
                    packages.append(package)
            transition = step.get("transition") or {}
            if transition.get("activity_changed"):
                cross_app_transitions += 1
            if transition.get("exactly_unchanged"):
                unchanged_steps += 1
            tool = (step.get("decision") or {}).get("tool")
            if not tool:
                continue
            arguments = dict(tool.get("arguments") or {})
            name = arguments.pop("action", None)
            if not isinstance(name, str):
                raise RuntimeError(f"Missing action name: {task_name}/step_{index}")
            action_counts[name] += 1
            try:
                adapter.map({"name": name, "parameters": arguments})
                allowed_counts[name] += 1
                episode_allowed += 1
            except ValueError:
                # This is expected for baseline long_press/wait. The PF01
                # parser must reject them and request a format repair.
                prohibited_counts[name] += 1
                episode_prohibited += 1
        if layer_errors:
            raise RuntimeError(f"Layer logging incomplete for {task_name}: {layer_errors}")
        total_steps += int(episode["step_count"])
        reward = float(summary["evaluator_reward"])
        total_reward += reward
        successes += int(bool(summary["success"]))
        episodes.append({
            "task_id": spec["task_id"],
            "task_name": task_name,
            "episode_id": summary["episode_id"],
            "episode_json": str(episode_path),
            "episode_json_sha256": digest(episode_path),
            "events_jsonl_sha256": digest(events_path),
            "goal_hash": spec["goal_hash"],
            "task_params_hash": spec["task_params_hash"],
            "native_budget": spec["native_max_steps"],
            "step_count": episode["step_count"],
            "reward": reward,
            "success": bool(summary["success"]),
            "allowed_action_count": episode_allowed,
            "prohibited_baseline_action_count": episode_prohibited,
            "unique_foreground_packages": sorted(set(packages)),
            "cross_activity_transition_count": cross_app_transitions,
            "exactly_unchanged_step_count": unchanged_steps,
        })

    handoff = load_json(handoff_audit)
    first_seed_handoff = [
        item for item in handoff["episodes"] if int(item["seed"]) == 20260806
    ]
    result = {
        "schema": "raven_m.mobileuse.baseline_replay_reference.v1",
        "mode": "zero_generation_zero_emulator_read_only",
        "source_combined": str(combined),
        "source_combined_sha256": digest(combined),
        "source_manifest": str(manifest),
        "source_manifest_sha256": digest(manifest),
        "source_handoff_audit": str(handoff_audit),
        "source_handoff_audit_sha256": digest(handoff_audit),
        "seed": 20260806,
        "frozen_order": FROZEN_ORDER,
        "episode_count": len(episodes),
        "success_count": successes,
        "total_reward": total_reward,
        "total_operator_decisions": total_steps,
        "action_counts": dict(sorted(action_counts.items())),
        "pf01_allowed_action_counts": dict(sorted(allowed_counts.items())),
        "pf01_intentionally_rejected_baseline_action_counts": dict(sorted(prohibited_counts.items())),
        "first_seed_cross_app_handoff": first_seed_handoff,
        "episodes": episodes,
    }
    if (successes, total_reward, total_steps) != (4, 4.5, 329):
        raise RuntimeError(
            f"Frozen baseline mismatch: success={successes}, reward={total_reward}, steps={total_steps}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    sibling = REPOSITORY_ROOT.parent / "RAVEN-M-Research"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--combined", type=Path,
        default=REPOSITORY_ROOT / "evidence" / "baseline" / "official_qwen32b_full_hard_combined_corrected_final.json",
    )
    parser.add_argument(
        "--manifest", type=Path,
        default=sibling / "05_project" / "configs" / "task_manifests" / "androidworld_hard_v2_instances.json",
    )
    parser.add_argument(
        "--handoff-audit", type=Path,
        default=REPOSITORY_ROOT / "evidence" / "layer_audits" / "official_qwen32b_cross_app_handoff_audit_2026-08-08.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_BASELINE_FIRST_SEED_REPLAY_REFERENCE.json",
    )
    args = parser.parse_args()
    result = replay(
        combined=args.combined,
        manifest=args.manifest,
        handoff_audit=args.handoff_audit,
        output=args.output,
    )
    print(json.dumps({
        "output": str(args.output),
        "episodes": result["episode_count"],
        "success": result["success_count"],
        "reward": result["total_reward"],
        "operator_decisions": result["total_operator_decisions"],
    }, indent=2))


if __name__ == "__main__":
    main()
