"""Run and audit the frozen S0/M0 non-Hard G6/G7 development suite."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import shutil
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402
from raven_m.controller.episode_controller import EpisodeController  # noqa: E402
from raven_m.history.policies import make_history_policy  # noqa: E402
from raven_m.memory.models import MemoryItem  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def all_calls(summary: dict[str, Any]) -> list[dict[str, Any]]:
    values = []
    for step in summary["steps"]:
        values.extend(step.get("model_calls", []))
        values.extend(step.get("history_update", {}).get("model_calls", []))
    return values


def audit_memory_episode(
    episode_dir: Path,
    episode_id: str,
) -> dict[str, Any]:
    event_path = episode_dir / "memory_events.jsonl"
    errors: list[str] = []
    stale_fact_routes = 0
    types: set[str] = set()
    route_counts: dict[str, int] = defaultdict(int)
    statuses: dict[str, str] = {}
    if not event_path.is_file():
        return {
            "event_count": 0,
            "memory_types": [],
            "route_counts": {},
            "stale_fact_routes": 0,
            "errors": ["memory_events.jsonl is missing"],
        }
    records = [
        json.loads(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for expected_index, event in enumerate(records):
        if event.get("event_index") != expected_index:
            errors.append(f"non-contiguous event index {expected_index}")
        if event.get("episode_id") != episode_id:
            errors.append("cross-episode memory event")
        kind = event.get("event")
        snapshots = []
        if kind in {"write", "transition"}:
            snapshots = [event["item"]]
        elif kind in {"contradiction", "supersede"}:
            snapshots = event["items"]
        for raw in snapshots:
            try:
                item = MemoryItem.from_dict(raw)
                item.validate(episode_id)
            except Exception as exc:
                errors.append(f"invalid memory item: {exc}")
                continue
            types.add(item.memory_type)
            statuses[item.memory_id] = item.verification_status
            for relative, expected_hash in zip(
                item.source.screenshot_paths,
                item.source.screenshot_sha256,
                strict=True,
            ):
                path = episode_dir / relative
                if not path.is_file():
                    errors.append(
                        f"{item.memory_id}: missing provenance {relative}"
                    )
                elif sha256(path.read_bytes()).hexdigest() != expected_hash:
                    errors.append(
                        f"{item.memory_id}: provenance hash mismatch {relative}"
                    )
        if kind == "route":
            route = event["route"]
            route_counts[route] += 1
            status = statuses.get(event["memory_id"])
            if route == "FACT" and status in {
                "stale",
                "contradicted",
                "revoked",
                "superseded",
                "archived",
            }:
                stale_fact_routes += 1
                errors.append(
                    f"{event['memory_id']}: inactive memory routed FACT"
                )
    return {
        "event_count": len(records),
        "memory_types": sorted(types),
        "route_counts": dict(sorted(route_counts.items())),
        "stale_fact_routes": stale_fact_routes,
        "errors": errors,
    }


def aggregate(
    *,
    suite_id: str,
    manifest: dict[str, Any],
    health: dict[str, Any],
    summaries: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    finished: bool,
) -> dict[str, Any]:
    by_variant: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = (
        defaultdict(list)
    )
    for summary, audit in zip(summaries, audits, strict=True):
        by_variant[summary["variant"]].append((summary, audit))
    acceptance = manifest["acceptance"]
    variant_results = {}
    for variant, minimum in (
        ("S0", acceptance["s0_min_episodes"]),
        ("M0", acceptance["m0_min_episodes"]),
    ):
        pairs = by_variant.get(variant, [])
        items = [pair[0] for pair in pairs]
        item_audits = [pair[1] for pair in pairs]
        attempts = sum(item["decision_attempt_count"] for item in items)
        valid = sum(
            item["valid_after_one_repair_count"] for item in items
        )
        infra = sum(int(item["error"] is not None) for item in items)
        calls = [call for item in items for call in all_calls(item)]
        max_prompt_tokens = max(
            (
                int(call.get("usage", {}).get("prompt_tokens", 0))
                for call in calls
            ),
            default=0,
        )
        invariant_errors = [
            error for audit in item_audits for error in audit["errors"]
        ]
        stale_fact = sum(
            audit["stale_fact_routes"] for audit in item_audits
        )
        role_counts = {"planner": 0, "critic": 0}
        role_event_counts = {"planner": 0, "critic": 0}
        role_output_errors = []
        for item in items:
            for step in item["steps"]:
                details = (
                    step.get("history_update", {}).get("details", {}) or {}
                )
                counts = details.get("role_call_counts", {}) or {}
                for role in role_counts:
                    role_counts[role] += int(counts.get(role, 0))
                for event in details.get("role_events", []) or []:
                    role = event.get("role")
                    if role in role_event_counts:
                        role_event_counts[role] += 1
                    if event.get("error"):
                        role_output_errors.append(
                            f"{item['episode_id']}:{role}:"
                            f"{event['error']}"
                        )
        invariant_errors.extend(role_output_errors)
        repair_rate = valid / attempts if attempts else 0.0
        infra_rate = infra / len(items) if items else 1.0
        context_ok = (
            max_prompt_tokens + acceptance["max_new_tokens"]
            <= acceptance["context_cap_tokens"]
        )
        variant_results[variant] = {
            "episode_count": len(items),
            "successful_episode_count": sum(
                int(item["success"]) for item in items
            ),
            "decision_attempt_count": attempts,
            "valid_after_one_repair_count": valid,
            "valid_after_one_repair_rate": repair_rate,
            "infrastructure_error_count": infra,
            "infrastructure_error_rate": infra_rate,
            "executor_model_call_count": sum(
                item["executor_model_call_count"] for item in items
            ),
            "conditional_role_model_call_count": sum(
                item["history_model_call_count"] for item in items
            ),
            "role_call_counts": role_counts,
            "role_event_counts": role_event_counts,
            "role_output_error_count": len(role_output_errors),
            "model_call_count": sum(item["model_call_count"] for item in items),
            "max_prompt_tokens": max_prompt_tokens,
            "context_cap_respected": context_ok,
            "memory_event_count": sum(
                audit["event_count"] for audit in item_audits
            ),
            "memory_types_observed": sorted(
                {
                    memory_type
                    for audit in item_audits
                    for memory_type in audit["memory_types"]
                }
            ),
            "stale_fact_route_count": stale_fact,
            "invariant_error_count": len(invariant_errors),
            "invariant_errors": invariant_errors,
            "acceptance_passed": (
                len(items) >= minimum
                and repair_rate
                >= acceptance["valid_after_one_repair_rate_min"]
                and infra_rate
                <= acceptance["infrastructure_error_rate_max"]
                and context_ok
                and len(invariant_errors)
                <= acceptance["invariant_error_max"]
                and stale_fact <= acceptance["stale_fact_route_max"]
                and (
                    variant != "M0"
                    or (
                        role_event_counts["planner"] >= len(items)
                        and role_event_counts["critic"] >= 1
                    )
                )
            ),
        }
    return {
        "suite_id": suite_id,
        "manifest_id": manifest["manifest_id"],
        "protocol": manifest["protocol"],
        "updated_at": utc_now(),
        "finished": finished,
        "model_backend": health["backend"],
        "episode_count": len(summaries),
        "variant_results": variant_results,
        "g6_s0_passed": variant_results["S0"]["acceptance_passed"],
        "g7_m0_passed": variant_results["M0"]["acceptance_passed"],
        "episodes": [
            {
                "episode_id": item["episode_id"],
                "variant": item["variant"],
                "task_name": item["task_name"],
                "seed": item["seed"],
                "success": item["success"],
                "failure_code": item["failure_code"],
                "decision_attempt_count": item["decision_attempt_count"],
                "model_call_count": item["model_call_count"],
                "memory_audit": audit,
            }
            for item, audit in zip(summaries, audits, strict=True)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "configs"
        / "task_manifests"
        / "method_dev_v1.json",
    )
    parser.add_argument("--suite-id", default="method_dev_g6_g7_20260723")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "method_dev_g6_g7",
    )
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    suite_dir = args.output_root / args.suite_id
    episode_root = suite_dir / "episodes"
    episode_root.mkdir(parents=True, exist_ok=True)
    write_json(suite_dir / "manifest.snapshot.json", manifest)
    client = TransformersClient(args.url)
    health = client.health()
    executor_prompt = (PROJECT_ROOT / manifest["executor_prompt"]).read_text(
        encoding="utf-8"
    )
    planner_prompt = (PROJECT_ROOT / manifest["planner_prompt"]).read_text(
        encoding="utf-8"
    )
    critic_prompt = (PROJECT_ROOT / manifest["critic_prompt"]).read_text(
        encoding="utf-8"
    )
    action_schema = PROJECT_ROOT / manifest["action_schema"]
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    summaries: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []

    if args.aggregate_only:
        for sequence, item in enumerate(manifest["schedule"], start=1):
            episode_dir = episode_root / (
                f"{sequence:02d}_{item['variant']}_{item['task']}_"
                f"seed{item['seed']}"
            )
            completed = episode_dir / "episode.json"
            if not completed.is_file():
                continue
            summary = json.loads(completed.read_text(encoding="utf-8"))
            summaries.append(summary)
            audits.append(
                audit_memory_episode(episode_dir, summary["episode_id"])
            )
        final = aggregate(
            suite_id=args.suite_id,
            manifest=manifest,
            health=health,
            summaries=summaries,
            audits=audits,
            finished=len(summaries) == len(manifest["schedule"]),
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False))
        if (
            not final["finished"]
            or not final["g6_s0_passed"]
            or not final["g7_m0_passed"]
        ):
            raise SystemExit(3)
        return

    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    try:
        for sequence, item in enumerate(manifest["schedule"], start=1):
            episode_dir = episode_root / (
                f"{sequence:02d}_{item['variant']}_{item['task']}_"
                f"seed{item['seed']}"
            )
            completed = episode_dir / "episode.json"
            if completed.exists():
                summary = json.loads(completed.read_text(encoding="utf-8"))
            else:
                if episode_dir.exists():
                    interrupted = episode_dir.with_name(
                        episode_dir.name
                        + "_interrupted_"
                        + datetime.now().strftime("%Y%m%dT%H%M%S")
                    )
                    shutil.move(str(episode_dir), str(interrupted))
                random.seed(item["seed"])
                np.random.seed(item["seed"])
                task_type = registered[item["task"]]
                task = task_type(task_type.generate_random_params())
                history_policy = make_history_policy(
                    item["variant"],
                    client=client,
                    summary_system_prompt="",
                    planner_system_prompt=planner_prompt,
                    critic_system_prompt=critic_prompt,
                )
                max_model_calls = (
                    2 * item["max_steps"]
                    if item["variant"] == "S0"
                    else 3 * item["max_steps"] + 4
                )
                controller = EpisodeController(
                    client=client,
                    system_prompt=executor_prompt,
                    max_steps=item["max_steps"],
                    max_model_calls=max_model_calls,
                    history_policy=history_policy,
                    action_schema_path=action_schema,
                )
                episode_id = (
                    f"{args.suite_id}_{sequence:02d}_{item['variant']}_"
                    f"{item['task']}_seed{item['seed']}"
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=episode_id,
                    episode_dir=episode_dir,
                    seed=item["seed"],
                    protocol=manifest["protocol"],
                    variant=item["variant"],
                )
            audit = audit_memory_episode(episode_dir, summary["episode_id"])
            summaries.append(summary)
            audits.append(audit)
            progress = aggregate(
                suite_id=args.suite_id,
                manifest=manifest,
                health=health,
                summaries=summaries,
                audits=audits,
                finished=False,
            )
            write_json(suite_dir / "suite_progress.json", progress)
            print(
                json.dumps(
                    {
                        "episode_count": len(summaries),
                        "latest": progress["episodes"][-1],
                        "variant_results": progress["variant_results"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        final = aggregate(
            suite_id=args.suite_id,
            manifest=manifest,
            health=health,
            summaries=summaries,
            audits=audits,
            finished=True,
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
        if not final["g6_s0_passed"] or not final["g7_m0_passed"]:
            raise SystemExit(3)
    finally:
        env.close()


if __name__ == "__main__":
    main()
