"""Resume the frozen PF01 behavioral arm after a suite-level harness crash.

This script does not alter MobileUse, prompts, actions, sampling, task instances,
or any file covered by the post-smoke freeze.  It starts a new, explicitly
labelled recovery suite and records invalid per-task episodes instead of letting
one upstream exception abort all remaining tasks.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
from uuid import uuid4

import run_mobileuse_hard as frozen


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-suite", type=Path, required=True)
    parser.add_argument("--resume-after-task-id", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            frozen.SOURCE_REPOSITORY
            / "05_project"
            / "configs"
            / "task_manifests"
            / "androidworld_hard_v2_instances.json"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=(
            frozen.REPOSITORY_ROOT
            / "runs"
            / "public_framework"
            / "mobileuse"
        ),
    )
    args = parser.parse_args()

    freeze_path = (
        frozen.REPOSITORY_ROOT
        / "evidence"
        / "public_framework"
        / "mobileuse"
        / "PF01_FREEZE_AFTER_SMOKE.json"
    )
    frozen_record = json.loads(freeze_path.read_text(encoding="utf-8"))
    if frozen_record["file_sha256"] != frozen.current_freeze():
        raise RuntimeError("Frozen behavioral source/config changed after smoke")

    source_suite = args.source_suite.resolve()
    source_summaries = [
        load_summary(path)
        for path in sorted(
            (source_suite / "episodes").glob("*/summary.json"),
            key=lambda path: path.parent.stat().st_ctime,
        )
    ]
    source_ids = [item["task_id"] for item in source_summaries]
    resume_index = frozen.FROZEN_ORDER.index(args.resume_after_task_id)
    expected_prefix = frozen.FROZEN_ORDER[: resume_index + 1]
    if source_ids != expected_prefix:
        raise RuntimeError(
            f"Source suite prefix mismatch: expected {expected_prefix}, got {source_ids}"
        )
    terminal = source_summaries[-1]
    if terminal["task_id"] != args.resume_after_task_id:
        raise RuntimeError("Recovery boundary is not the source suite terminal task")
    if terminal["scientifically_valid"]:
        raise RuntimeError("Recovery is only authorized after an invalid terminal episode")

    specs = frozen.load_scored_specs(args.manifest)[resume_index + 1 :]
    registry_value = frozen.registry.TaskRegistry().get_registry(
        frozen.registry.TaskRegistry.ANDROID_WORLD_FAMILY
    )
    tasks = [frozen.instantiate_verified(registry_value, spec) for spec in specs]
    client = frozen.model_client(args.url, args.request_timeout_seconds)
    health = client.health()
    env = frozen.env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
        a11y_method=frozen.android_world_controller.A11yMethod.UIAUTOMATOR,
    )

    suite_id = (
        f"pf01_scored_recovery_{datetime.now().strftime('%Y%m%dT%H%M%S')}_"
        f"{uuid4().hex[:8]}"
    )
    suite_dir = args.output_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.manifest, suite_dir / "manifest.snapshot.json")
    recovery = {
        "schema": "raven_m.mobileuse.recovery_boundary.v1",
        "behavioral_arm_id": frozen.ARM_ID,
        "source_suite": str(source_suite),
        "resume_after_task_id": args.resume_after_task_id,
        "completed_source_task_ids": source_ids,
        "remaining_task_ids": [item["task_id"] for item in specs],
        "reason": terminal["error"],
        "frozen_file_sha256": frozen.current_freeze(),
        "behavioral_changes": [],
        "harness_change": "Catch invalid per-task RuntimeError and continue the suite.",
    }
    (suite_dir / "RECOVERY_BOUNDARY.json").write_text(
        json.dumps(recovery, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summaries: list[dict] = []
    try:
        for spec, task in zip(specs, tasks):
            before = set((suite_dir / "episodes").glob("*"))
            try:
                summary = frozen.run_episode(
                    env=env,
                    task=task,
                    spec=spec,
                    client=client,
                    suite_dir=suite_dir,
                    mode="scored_recovery",
                )
            except RuntimeError:
                after = set((suite_dir / "episodes").glob("*"))
                created = list(after - before)
                if len(created) != 1:
                    raise
                summary_path = created[0] / "summary.json"
                if not summary_path.is_file():
                    raise
                summary = load_summary(summary_path)
            summaries.append(summary)
    finally:
        env.close()

    aggregate = {
        "schema": "raven_m.mobileuse.recovery_suite_summary.v1",
        "behavioral_arm_id": frozen.ARM_ID,
        "suite_id": suite_id,
        "mode": "scored_recovery",
        "source_suite": str(source_suite),
        "resume_after_task_id": args.resume_after_task_id,
        "model_health": health,
        "episode_count": len(summaries),
        "success_count": sum(int(item["success"]) for item in summaries),
        "total_reward": sum(
            float(item["evaluator_reward"] or 0.0) for item in summaries
        ),
        "scientifically_valid_count": sum(
            int(item["scientifically_valid"]) for item in summaries
        ),
        "episodes": summaries,
    }
    (suite_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, indent=2))


if __name__ == "__main__":
    main()
