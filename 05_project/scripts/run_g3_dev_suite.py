"""Run the frozen five-task, non-scored AndroidWorld G3 development suite."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
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


def aggregate(
    *,
    manifest: dict[str, Any],
    suite_id: str,
    health: dict[str, Any],
    summaries: list[dict[str, Any]],
    finished: bool,
) -> dict[str, Any]:
    def is_legacy_model_output_error(item: dict[str, Any]) -> bool:
        return (
            item.get("error", {}).get("type") == "ActionValidationError"
            if isinstance(item.get("error"), dict)
            else False
        )

    def execution_decision_gap(item: dict[str, Any]) -> int:
        """Recover a pre-fix decision lost when execution raised after parsing."""
        logged_calls = sum(
            len(step.get("model_calls", [])) for step in item["steps"]
        )
        call_gap = item["model_call_count"] - logged_calls
        traceback_text = (
            item.get("error", {}).get("traceback", "")
            if isinstance(item.get("error"), dict)
            else ""
        )
        return int(call_gap == 1 and "self.adapter.execute" in traceback_text)

    attempts = sum(
        item.get(
            "decision_attempt_count",
            item["decision_count"] + int(is_legacy_model_output_error(item)),
        )
        + execution_decision_gap(item)
        for item in summaries
    )
    valid_after_repair = sum(
        item.get("valid_after_one_repair_count", item["decision_count"])
        + execution_decision_gap(item)
        for item in summaries
    )
    first_pass = sum(
        item["first_pass_parse_count"] + execution_decision_gap(item)
        for item in summaries
    )
    model_calls = sum(
        item["model_call_count"] + 2 * int(is_legacy_model_output_error(item))
        for item in summaries
    )
    locally_logged_model_calls = sum(
        len(step.get("model_calls", []))
        for item in summaries
        for step in item["steps"]
    )
    successful = sum(int(item["success"]) for item in summaries)
    errors = sum(
        int(item["error"] is not None and not is_legacy_model_output_error(item))
        for item in summaries
    )
    latencies = [
        call["raven_meta"]["latency_seconds"]
        for item in summaries
        for step in item["steps"]
        for call in step.get("model_calls", [])
        if call.get("raven_meta", {}).get("latency_seconds") is not None
    ]
    return {
        "suite_id": suite_id,
        "manifest_id": manifest["manifest_id"],
        "protocol": manifest["protocol"],
        "variant": manifest["variant"],
        "updated_at": utc_now(),
        "finished": finished,
        "target_decisions": manifest["target_decisions"],
        "gate_target_met": attempts >= manifest["target_decisions"],
        "sample_size_target_met": attempts >= manifest["target_decisions"],
        "episode_count": len(summaries),
        "distinct_task_count": len({item["task_name"] for item in summaries}),
        "decision_count": valid_after_repair,
        "decision_attempt_count": attempts,
        "first_pass_parse_count": first_pass,
        "first_pass_parse_rate": first_pass / attempts if attempts else None,
        "first_pass_parse_gate_passed": (
            first_pass / attempts >= 0.90 if attempts else False
        ),
        "valid_after_one_repair_count": valid_after_repair,
        "valid_after_one_repair_rate": (
            valid_after_repair / attempts if attempts else None
        ),
        "valid_after_one_repair_gate_passed": (
            valid_after_repair / attempts >= 0.95 if attempts else False
        ),
        "parse_gate_passed": (
            attempts >= manifest["target_decisions"]
            and first_pass / attempts >= 0.90
            and valid_after_repair / attempts >= 0.95
        ),
        "model_call_count": model_calls,
        "locally_logged_model_call_count": locally_logged_model_calls,
        "successful_episode_count": successful,
        "episode_success_rate": successful / len(summaries) if summaries else None,
        "infrastructure_or_controller_error_count": errors,
        "mean_model_latency_seconds": (
            sum(latencies) / len(latencies) if latencies else None
        ),
        "max_model_latency_seconds": max(latencies) if latencies else None,
        "model_backend": health.get("backend"),
        "episodes": [
            {
                "episode_id": item["episode_id"],
                "task_name": item["task_name"],
                "seed": item["seed"],
                "success": item["success"],
                "failure_code": (
                    "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
                    if is_legacy_model_output_error(item)
                    else item["failure_code"]
                ),
                "decision_count": (
                    item.get(
                        "valid_after_one_repair_count",
                        item["decision_count"],
                    )
                    + execution_decision_gap(item)
                ),
                "decision_attempt_count": item.get(
                    "decision_attempt_count",
                    item["decision_count"]
                    + int(is_legacy_model_output_error(item)),
                )
                + execution_decision_gap(item),
                "model_call_count": (
                    item["model_call_count"]
                    + 2 * int(is_legacy_model_output_error(item))
                ),
                "first_pass_parse_rate": (
                    (
                        item["first_pass_parse_count"]
                        + execution_decision_gap(item)
                    )
                    / (
                        item.get(
                            "decision_attempt_count",
                            item["decision_count"]
                            + int(is_legacy_model_output_error(item)),
                        )
                        + execution_decision_gap(item)
                    )
                ),
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
        / "dev_nonhard_v1.json",
    )
    parser.add_argument("--suite-id", default="g3_b0_20260723")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "dev_nonhard_g3",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    suite_dir = args.output_root / args.suite_id
    episode_root = suite_dir / "episodes"
    episode_root.mkdir(parents=True, exist_ok=True)
    write_json(suite_dir / "manifest.snapshot.json", manifest)

    task_specs = {item["name"]: item for item in manifest["tasks"]}
    schedule: list[tuple[str, int, str]] = []
    for index, item in enumerate(manifest["tasks"]):
        schedule.append((item["name"], manifest["base_seed"] + index, "core"))
    for round_index in range(manifest["max_top_up_rounds"]):
        for index, name in enumerate(manifest["top_up_order"]):
            schedule.append(
                (
                    name,
                    manifest["base_seed"] + 100 * (round_index + 1) + index,
                    f"top_up_{round_index + 1}",
                )
            )

    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    unknown = sorted({name for name, _, _ in schedule} - set(registered))
    if unknown:
        raise KeyError(f"Unknown AndroidWorld tasks: {unknown}")

    client = TransformersClient(args.url)
    health = client.health()
    prompt_path = PROJECT_ROOT / manifest.get(
        "prompt", "prompts/executor_v0.md"
    )
    system_prompt = prompt_path.read_text(encoding="utf-8")
    summaries: list[dict[str, Any]] = []

    if args.aggregate_only:
        for sequence, (task_name, seed, phase) in enumerate(schedule, start=1):
            completed_path = (
                episode_root
                / f"{sequence:02d}_{phase}_{task_name}_seed{seed}"
                / "episode.json"
            )
            if completed_path.exists():
                summaries.append(
                    json.loads(completed_path.read_text(encoding="utf-8"))
                )
        final = aggregate(
            manifest=manifest,
            suite_id=args.suite_id,
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
        for sequence, (task_name, seed, phase) in enumerate(schedule, start=1):
            completed_path = (
                episode_root
                / f"{sequence:02d}_{phase}_{task_name}_seed{seed}"
                / "episode.json"
            )
            if completed_path.exists():
                summaries.append(
                    json.loads(completed_path.read_text(encoding="utf-8"))
                )
            else:
                if (
                    phase != "core"
                    and sum(
                        item.get(
                            "decision_attempt_count",
                            item["decision_count"]
                            + int(
                                isinstance(item.get("error"), dict)
                                and item["error"].get("type")
                                == "ActionValidationError"
                            ),
                        )
                        for item in summaries
                    )
                    >= manifest["target_decisions"]
                ):
                    break
                episode_dir = completed_path.parent
                if episode_dir.exists():
                    interrupted = episode_dir.with_name(
                        episode_dir.name
                        + "_interrupted_"
                        + datetime.now().strftime("%Y%m%dT%H%M%S")
                    )
                    shutil.move(str(episode_dir), str(interrupted))
                random.seed(seed)
                np.random.seed(seed)
                task_type = registered[task_name]
                task = task_type(task_type.generate_random_params())
                controller = EpisodeController(
                    client=client,
                    system_prompt=system_prompt,
                    max_steps=task_specs[task_name]["max_steps"],
                    max_model_calls=2 * task_specs[task_name]["max_steps"],
                )
                episode_id = (
                    f"{args.suite_id}_{sequence:02d}_{phase}_{task_name}_seed{seed}"
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=episode_id,
                    episode_dir=episode_dir,
                    seed=seed,
                    protocol=manifest["protocol"],
                    variant=manifest["variant"],
                )
                summaries.append(summary)
            progress = aggregate(
                manifest=manifest,
                suite_id=args.suite_id,
                health=health,
                summaries=summaries,
                finished=False,
            )
            write_json(suite_dir / "suite_progress.json", progress)
            print(
                json.dumps(
                    {
                        "episode_count": progress["episode_count"],
                        "latest_task": summaries[-1]["task_name"],
                        "latest_success": summaries[-1]["success"],
                        "decision_attempt_count": progress[
                            "decision_attempt_count"
                        ],
                        "target_decisions": progress["target_decisions"],
                        "first_pass_parse_rate": progress[
                            "first_pass_parse_rate"
                        ],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        final = aggregate(
            manifest=manifest,
            suite_id=args.suite_id,
            health=health,
            summaries=summaries,
            finished=True,
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
        if not final["gate_target_met"] or final["distinct_task_count"] < 5:
            raise SystemExit(3)
    finally:
        env.close()


if __name__ == "__main__":
    main()
