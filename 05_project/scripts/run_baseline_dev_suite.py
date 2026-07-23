"""Run and aggregate the frozen B1/B2/B3 non-Hard development suite."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
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
    calls = []
    for step in summary["steps"]:
        calls.extend(step.get("model_calls", []))
        calls.extend(step.get("history_update", {}).get("model_calls", []))
    return calls


def aggregate(
    *,
    suite_id: str,
    manifest: dict[str, Any],
    health: dict[str, Any],
    summaries: list[dict[str, Any]],
    finished: bool,
) -> dict[str, Any]:
    by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        by_variant[summary["variant"]].append(summary)

    variant_results: dict[str, Any] = {}
    acceptance = manifest["acceptance"]
    minimum_episodes = {
        "B1": acceptance["b1_min_episodes"],
        "B2": acceptance["b2_min_episodes"],
        "B3": acceptance["b3_min_episodes"],
    }
    for variant in ("B1", "B2", "B3"):
        items = by_variant.get(variant, [])
        attempts = sum(item["decision_attempt_count"] for item in items)
        valid = sum(item["valid_after_one_repair_count"] for item in items)
        first_pass = sum(item["first_pass_parse_count"] for item in items)
        infra = sum(int(item["error"] is not None) for item in items)
        calls = [call for item in items for call in all_calls(item)]
        prompt_tokens = [
            int(call.get("usage", {}).get("prompt_tokens", 0))
            for call in calls
        ]
        context_ok = all(tokens + 256 <= 8192 for tokens in prompt_tokens)
        first_rate = first_pass / attempts if attempts else None
        repair_rate = valid / attempts if attempts else None
        infra_rate = infra / len(items) if items else None
        variant_results[variant] = {
            "episode_count": len(items),
            "decision_attempt_count": attempts,
            "first_pass_parse_count": first_pass,
            "first_pass_parse_rate": first_rate,
            "valid_after_one_repair_count": valid,
            "valid_after_one_repair_rate": repair_rate,
            "successful_episode_count": sum(
                int(item["success"]) for item in items
            ),
            "infrastructure_error_count": infra,
            "infrastructure_error_rate": infra_rate,
            "executor_model_call_count": sum(
                item["executor_model_call_count"] for item in items
            ),
            "history_model_call_count": sum(
                item["history_model_call_count"] for item in items
            ),
            "model_call_count": sum(item["model_call_count"] for item in items),
            "max_prompt_tokens": max(prompt_tokens) if prompt_tokens else None,
            "context_cap_respected": context_ok,
            "acceptance_passed": (
                len(items) >= minimum_episodes[variant]
                and attempts > 0
                and first_rate is not None
                and first_rate >= acceptance["first_pass_parse_rate_min"]
                and repair_rate is not None
                and repair_rate
                >= acceptance["valid_after_one_repair_rate_min"]
                and infra_rate is not None
                and infra_rate
                <= acceptance["infrastructure_error_rate_max"]
                and context_ok
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
        "g4_history_baselines_passed": all(
            variant_results[item]["acceptance_passed"]
            for item in ("B1", "B2", "B3")
        ),
        "episodes": [
            {
                "episode_id": item["episode_id"],
                "variant": item["variant"],
                "task_name": item["task_name"],
                "seed": item["seed"],
                "success": item["success"],
                "failure_code": item["failure_code"],
                "decision_attempt_count": item["decision_attempt_count"],
                "first_pass_parse_rate": item["first_pass_parse_rate"],
                "model_call_count": item["model_call_count"],
                "history_model_call_count": item["history_model_call_count"],
            }
            for item in summaries
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
        / "baseline_dev_v1.json",
    )
    parser.add_argument("--suite-id", default="baseline_dev_g4_20260723")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "baseline_dev_g4",
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
    executor_prompt = (
        PROJECT_ROOT / manifest["executor_prompt"]
    ).read_text(encoding="utf-8")
    summary_prompt = (
        PROJECT_ROOT / manifest["summary_prompt"]
    ).read_text(encoding="utf-8")

    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    unknown = sorted(
        {item["task"] for item in manifest["schedule"]} - set(registered)
    )
    if unknown:
        raise KeyError(f"Unknown AndroidWorld tasks: {unknown}")

    summaries: list[dict[str, Any]] = []
    if args.aggregate_only:
        for sequence, item in enumerate(manifest["schedule"], start=1):
            path = (
                episode_root
                / (
                    f"{sequence:02d}_{item['variant']}_{item['task']}_"
                    f"seed{item['seed']}"
                )
                / "episode.json"
            )
            if path.exists():
                summaries.append(json.loads(path.read_text(encoding="utf-8")))
        final = aggregate(
            suite_id=args.suite_id,
            manifest=manifest,
            health=health,
            summaries=summaries,
            finished=True,
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False))
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
            completed_path = episode_dir / "episode.json"
            if completed_path.exists():
                summary = json.loads(
                    completed_path.read_text(encoding="utf-8")
                )
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
                    summary_system_prompt=summary_prompt,
                )
                summary_slots = (
                    2 * math.ceil(item["max_steps"] / 5)
                    if item["variant"] == "B3"
                    else 0
                )
                controller = EpisodeController(
                    client=client,
                    system_prompt=executor_prompt,
                    max_steps=item["max_steps"],
                    max_model_calls=2 * item["max_steps"] + summary_slots,
                    history_policy=history_policy,
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
            summaries.append(summary)
            progress = aggregate(
                suite_id=args.suite_id,
                manifest=manifest,
                health=health,
                summaries=summaries,
                finished=False,
            )
            write_json(suite_dir / "suite_progress.json", progress)
            print(
                json.dumps(
                    {
                        "episode_count": progress["episode_count"],
                        "latest_variant": summary["variant"],
                        "latest_task": summary["task_name"],
                        "latest_success": summary["success"],
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
            finished=True,
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
        if not final["g4_history_baselines_passed"]:
            raise SystemExit(3)
    finally:
        env.close()


if __name__ == "__main__":
    main()
