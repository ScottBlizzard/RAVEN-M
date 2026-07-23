"""Exercise every frozen ablation/control path on one paired non-Hard task."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
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
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402
from raven_m.controller.episode_controller import (  # noqa: E402
    EpisodeController,
    _json_safe,
)
from raven_m.models.transformers_client import TransformersClient  # noqa: E402
from run_frozen_hard_suite import (  # noqa: E402
    EXPECTED_BACKEND,
    EXPECTED_REVISION,
    all_calls,
    classify_infrastructure,
    digest_json,
    recover_androidworld_env,
    variant_runtime,
    wait_for_model_service,
)
from run_method_dev_suite import audit_memory_episode  # noqa: E402


MEMORY_VARIANTS = {
    "MREL",
    "MNO_WM",
    "MNO_VEL",
    "MNO_FRM",
    "MNO_PSI",
    "MNO_CRITIC",
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def role_audit(summary: dict[str, Any]) -> dict[str, Any]:
    events = []
    for step in summary["steps"]:
        details = step.get("history_update", {}).get("details", {}) or {}
        events.extend(details.get("role_events", []) or [])
    return {
        "planner_events": sum(
            event.get("role") == "planner" for event in events
        ),
        "critic_events": sum(
            event.get("role") == "critic" for event in events
        ),
        "output_errors": [
            {
                "role": event.get("role"),
                "error": event.get("error"),
            }
            for event in events
            if event.get("error")
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--max-model-recovery-seconds",
        type=float,
        default=1800.0,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "configs/task_manifests/component_smoke_v1.json",
    )
    parser.add_argument(
        "--suite-id",
        default="component_smoke_v1_20260724",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs/component_smoke",
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=PROJECT_ROOT / "metadata/component_smoke_audit.json",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    hard = json.loads(
        (
            PROJECT_ROOT
            / "configs/task_manifests/androidworld_hard_v1.json"
        ).read_text(encoding="utf-8")
    )
    hard_names = {item["class_name"] for item in hard["tasks"]}
    if manifest["task"] in hard_names:
        raise RuntimeError("Component smoke must never use a Hard task.")
    if len(set(manifest["variants"])) != len(manifest["variants"]):
        raise RuntimeError("Component-smoke variants are not unique.")

    suite_dir = args.output_root / args.suite_id
    suite_dir.mkdir(parents=True, exist_ok=True)
    write_json(suite_dir / "manifest.snapshot.json", manifest)
    client = TransformersClient(args.url)
    health = wait_for_model_service(
        client,
        recovery_dir=suite_dir / "recoveries" / "model_preflight",
        max_wait_seconds=args.max_model_recovery_seconds,
    )
    if (
        health.get("backend") != EXPECTED_BACKEND
        or health.get("revision") != EXPECTED_REVISION
    ):
        raise RuntimeError("Component smoke model identity mismatch.")
    prompts = {
        name: (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for name, path in {
            "executor": "prompts/executor_v1.md",
            "executor_raven": "prompts/executor_raven_v1.md",
            "summary": "prompts/summary_v1.md",
            "planner": "prompts/planner_v1.md",
            "critic": "prompts/critic_v1.md",
        }.items()
    }

    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    results = []
    infrastructure_attempts = []
    try:
        for sequence, variant in enumerate(manifest["variants"], start=1):
            episode_dir = suite_dir / "episodes" / (
                f"{sequence:02d}_{variant}_{manifest['task']}_"
                f"seed{manifest['seed']}"
            )
            completed = episode_dir / "episode.json"
            if completed.is_file():
                summary = json.loads(completed.read_text(encoding="utf-8"))
            else:
                if episode_dir.exists():
                    interrupted = episode_dir.with_name(
                        episode_dir.name
                        + "_interrupted_"
                        + datetime.now().strftime("%Y%m%dT%H%M%S")
                    )
                    shutil.move(str(episode_dir), str(interrupted))
                base_episode_id = (
                    f"{args.suite_id}_{sequence:02d}_{variant}_"
                    f"{manifest['task']}_seed{manifest['seed']}"
                )
                expected_pair_hash = None
                summary = None
                for attempt in range(1, 4):
                    random.seed(manifest["seed"])
                    np.random.seed(manifest["seed"])
                    task_type = registered[manifest["task"]]
                    task = task_type(task_type.generate_random_params())
                    pair_hash = (
                        sha256(str(task.goal).encode("utf-8")).hexdigest(),
                        digest_json(_json_safe(task.params)),
                    )
                    if (
                        expected_pair_hash is not None
                        and pair_hash != expected_pair_hash
                    ):
                        raise RuntimeError(
                            "Component-smoke retry regenerated a different "
                            "task instance."
                        )
                    expected_pair_hash = pair_hash
                    policy, prompt, schema_path, max_calls = variant_runtime(
                        variant,
                        client=client,
                        max_steps=manifest["max_steps"],
                        prompts=prompts,
                    )
                    controller = EpisodeController(
                        client=client,
                        system_prompt=prompt,
                        max_steps=manifest["max_steps"],
                        max_model_calls=max_calls,
                        history_policy=policy,
                        action_schema_path=schema_path,
                    )
                    episode_id = f"{base_episode_id}_a{attempt}"
                    summary = controller.run(
                        env=env,
                        task=task,
                        episode_id=episode_id,
                        episode_dir=episode_dir,
                        seed=manifest["seed"],
                        protocol=manifest["protocol"],
                        variant=variant,
                    )
                    if not summary.get("error"):
                        break
                    infra_code = classify_infrastructure(summary)
                    if infra_code is None:
                        write_json(
                            suite_dir / "unclassified_controller_error.json",
                            summary,
                        )
                        raise RuntimeError(
                            "Unclassified component-smoke controller error."
                        )
                    archive_root = (
                        suite_dir / "invalid_infrastructure_attempts"
                    )
                    archive_root.mkdir(parents=True, exist_ok=True)
                    archived = archive_root / (
                        episode_dir.name + f"_attempt_{attempt:02d}"
                    )
                    if archived.exists():
                        raise RuntimeError(
                            f"Infrastructure archive already exists: {archived}"
                        )
                    shutil.move(str(episode_dir), str(archived))
                    infrastructure_attempts.append(
                        {
                            "sequence": sequence,
                            "variant": variant,
                            "attempt": attempt,
                            "episode_id": episode_id,
                            "code": infra_code,
                            "goal_sha256": pair_hash[0],
                            "params_sha256": pair_hash[1],
                            "archive": archived.relative_to(
                                REPOSITORY_ROOT
                            ).as_posix(),
                            "error": summary["error"],
                        }
                    )
                    write_json(
                        suite_dir / "infrastructure_attempts.json",
                        {
                            "schema_version": (
                                "component_infrastructure_attempts.v1"
                            ),
                            "attempts": infrastructure_attempts,
                        },
                    )
                    if attempt >= 3:
                        raise RuntimeError(
                            "Component-smoke infrastructure retries "
                            "exhausted."
                        )
                    if infra_code == "INFRA_EMULATOR_LOST":
                        env.close()
                        env = recover_androidworld_env(
                            adb_path=args.adb_path,
                            console_port=args.console_port,
                            grpc_port=args.grpc_port,
                            recovery_dir=(
                                suite_dir
                                / "recoveries"
                                / f"{sequence:02d}_after_attempt_{attempt:02d}"
                            ),
                        )
                    elif infra_code == "INFRA_MODEL_UNAVAILABLE":
                        wait_for_model_service(
                            client,
                            recovery_dir=(
                                suite_dir
                                / "recoveries"
                                / (
                                    f"{sequence:02d}_model_after_attempt_"
                                    f"{attempt:02d}"
                                )
                            ),
                            max_wait_seconds=(
                                args.max_model_recovery_seconds
                            ),
                        )
                if summary is None or summary.get("error"):
                    raise RuntimeError(
                        "No valid component-smoke episode after recovery."
                    )
            calls = all_calls(summary)
            max_prompt_tokens = max(
                (
                    int(call.get("usage", {}).get("prompt_tokens", 0))
                    for call in calls
                ),
                default=0,
            )
            roles = role_audit(summary)
            memory_audit = (
                audit_memory_episode(episode_dir, summary["episode_id"])
                if variant in MEMORY_VARIANTS
                else None
            )
            errors = []
            if summary.get("error"):
                errors.append("infrastructure_or_controller_error")
            if (
                max_prompt_tokens
                + manifest["acceptance"]["max_new_tokens"]
                > manifest["acceptance"]["context_cap_tokens"]
            ):
                errors.append("context_cap_exceeded")
            if roles["output_errors"]:
                errors.append("role_output_error")
            if variant in MEMORY_VARIANTS and roles["planner_events"] < 1:
                errors.append("planner_not_exercised")
            if variant == "MNO_CRITIC" and roles["critic_events"] != 0:
                errors.append("critic_not_disabled")
            if memory_audit and memory_audit["errors"]:
                errors.append("memory_invariant_error")
            if (
                variant in {"B3_CTX", "B3_CALL"}
                and summary["history_model_call_count"] < 1
            ):
                errors.append("summary_control_not_exercised")
            result = {
                "variant": variant,
                "episode_id": summary["episode_id"],
                "episode_path": episode_dir.relative_to(
                    REPOSITORY_ROOT
                ).as_posix(),
                "task_goal": summary["task_goal"],
                "goal_sha256": sha256(
                    summary["task_goal"].encode("utf-8")
                ).hexdigest(),
                "params_sha256": digest_json(
                    _json_safe(summary["task_params"])
                ),
                "success": summary["success"],
                "failure_code": summary["failure_code"],
                "model_call_count": summary["model_call_count"],
                "max_prompt_tokens": max_prompt_tokens,
                "role_audit": roles,
                "memory_audit": memory_audit,
                "errors": errors,
            }
            results.append(result)
            write_json(suite_dir / "suite_progress.json", {"results": results})
            print(
                json.dumps(
                    {
                        "completed": len(results),
                        "expected": len(manifest["variants"]),
                        "variant": variant,
                        "errors": errors,
                    }
                ),
                flush=True,
            )
    finally:
        env.close()

    pair_hashes = {
        (item["goal_sha256"], item["params_sha256"]) for item in results
    }
    errors = [
        f"{item['variant']}:{error}"
        for item in results
        for error in item["errors"]
    ]
    if len(pair_hashes) != 1:
        errors.append("paired_task_instance_drift")
    if len(results) != manifest["acceptance"]["exact_episode_count"]:
        errors.append("episode_count_mismatch")
    output = {
        "schema_version": "component_smoke_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "suite_id": args.suite_id,
        "manifest_id": manifest["manifest_id"],
        "protocol": manifest["protocol"],
        "model_backend": health["backend"],
        "model_revision": health["revision"],
        "paired_instance_hash_count": len(pair_hashes),
        "infrastructure_attempt_count": len(infrastructure_attempts),
        "results": results,
        "errors": errors,
    }
    write_json(suite_dir / "suite_summary.json", output)
    write_json(args.audit_output, output)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
