"""One-cell continuation after hotfix-002 hit a local emulator failure."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
from typing import Any

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_frozen_hard_suite as frozen  # noqa: E402
import run_frozen_hard_suite_hotfix_001 as hotfix001  # noqa: E402
import run_frozen_hard_suite_hotfix_002 as hotfix002  # noqa: E402


AMENDMENT_ID = "protocol-v1-hotfix-003"
AMENDMENT_MANIFEST = (
    PROJECT_ROOT / "metadata/protocol_amendment_003.json"
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_amendment_manifest(*, require_tag: bool) -> dict[str, Any]:
    if not AMENDMENT_MANIFEST.is_file():
        raise RuntimeError("Protocol amendment 003 manifest is absent.")
    manifest = json.loads(AMENDMENT_MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("amendment_id") != AMENDMENT_ID
        or manifest.get("status") != "active"
        or manifest.get("scope")
        != "single_cell_post_outage_emulator_recovery"
    ):
        raise RuntimeError("Protocol amendment 003 identity is invalid.")
    for record in manifest["files"]:
        path = REPOSITORY_ROOT / record["path"]
        if (
            not path.is_file()
            or path.stat().st_size != record["bytes"]
            or file_sha256(path) != record["sha256"]
        ):
            raise RuntimeError(
                f"Protocol amendment 003 hash mismatch: {record['path']}"
            )
    if require_tag:
        tag = manifest["git_tag"]
        tag_commit = frozen.git("rev-parse", f"{tag}^{{commit}}")
        frozen.git("merge-base", "--is-ancestor", tag_commit, "HEAD")
        manifest = {**manifest, "git_tag_commit": tag_commit}
    return manifest


def amendment_result_identity() -> dict[str, Any]:
    manifest = load_amendment_manifest(require_tag=False)
    return {
        "amendment_id": manifest["amendment_id"],
        "scope": manifest["scope"],
        "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
        "hotfix_runner_sha256": file_sha256(Path(__file__).resolve()),
    }


def verify_freeze_hotfix_003() -> dict[str, Any]:
    freeze = hotfix002.verify_freeze_hotfix_002()
    manifest = load_amendment_manifest(require_tag=True)
    return {
        **freeze,
        "protocol_amendment_003": {
            "amendment_id": manifest["amendment_id"],
            "scope": manifest["scope"],
            "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
            "git_tag": manifest["git_tag"],
            "git_tag_commit": manifest["git_tag_commit"],
        },
    }


def validate_attempt_04_emulator_failure(
    events_path: Path,
) -> dict[str, Any]:
    if not events_path.is_file():
        raise RuntimeError("Attempt 04 events are absent.")
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    starts = [
        event for event in events if event.get("event") == "episode_start"
    ]
    steps = [event for event in events if event.get("event") == "step"]
    errors = [
        event for event in events if event.get("event") == "episode_error"
    ]
    if len(starts) != 1 or starts[0].get("episode_id", "").endswith("_a4") is False:
        raise RuntimeError("Attempt 04 episode identity is invalid.")
    if len(steps) != 1 or not steps[0].get("model_calls"):
        raise RuntimeError("Attempt 04 lacks its successful model call.")
    execution_error = steps[0].get("execution_error") or {}
    episode_error = (errors[0].get("error") if errors else None) or {}
    if (
        execution_error.get("type") != "AdbControllerError"
        or episode_error.get("type") != "AdbControllerError"
    ):
        raise RuntimeError("Attempt 04 was not an emulator/ADB failure.")
    if steps[0]["model_calls"][0].get("raven_meta", {}).get("backend_id") != (
        frozen.EXPECTED_BACKEND
    ):
        raise RuntimeError("Attempt 04 model identity differs from the freeze.")
    return {
        "episode_id": starts[0]["episode_id"],
        "model_call_id": steps[0]["model_calls"][0]["call_id"],
        "model_latency_seconds": steps[0]["model_calls"][0][
            "raven_meta"
        ]["latency_seconds"],
        "execution_error": execution_error,
    }


def validate_cold_restart_smoke(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("Cold-restart AndroidWorld smoke is absent.")
    smoke = json.loads(path.read_text(encoding="utf-8"))
    if (
        smoke.get("status") != "ok"
        or smoke.get("registered_android_world_tasks") != 116
        or smoke.get("screen_shape") != [2400, 1080, 3]
    ):
        raise RuntimeError("Cold-restart AndroidWorld smoke did not pass.")
    return smoke


def record_result_hotfix_003(
    *,
    schedule_record: dict[str, Any],
    summary: dict[str, Any],
    attempt_count: int,
    infra_attempts: list[dict[str, Any]],
    episode_dir: Path,
) -> dict[str, Any]:
    result = hotfix002.record_result_hotfix_002(
        schedule_record=schedule_record,
        summary=summary,
        attempt_count=attempt_count,
        infra_attempts=infra_attempts,
        episode_dir=episode_dir,
    )
    result["protocol_amendments"].append(amendment_result_identity())
    return result


def parse_wrapper_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--max-model-recovery-seconds",
        type=float,
        default=21600.0,
    )
    parser.add_argument("--suite-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs/frozen_hard_v1",
    )
    args, _ = parser.parse_known_args()
    return args


def recover_attempt_05(
    *,
    args: argparse.Namespace,
    suite_dir: Path,
) -> str | None:
    manifest = load_amendment_manifest(require_tag=True)
    authorized = manifest["authorized_schedule_cell"]
    record_dir = suite_dir / "episodes" / authorized["record_directory"]
    final_path = record_dir / "scored_result.json"
    if final_path.is_file():
        return None
    attempt_05 = record_dir / "attempt_05"
    if attempt_05.exists():
        raise RuntimeError(
            "Attempt 05 already exists without a scored result."
        )
    schedule_record = json.loads(
        (record_dir / "schedule_record.json").read_text(encoding="utf-8")
    )
    infra_payload = json.loads(
        (record_dir / "infrastructure_attempts.json").read_text(
            encoding="utf-8"
        )
    )
    expected_pair_hash = hotfix002.validate_authorized_exhaustion(
        {
            "authorized_schedule_cell": authorized,
        },
        suite_id=args.suite_id,
        schedule_record=schedule_record,
        attempts=infra_payload["attempts"],
    )
    attempt_04_evidence = validate_attempt_04_emulator_failure(
        record_dir / "attempt_04/events.jsonl"
    )
    smoke_path = (
        REPOSITORY_ROOT
        / "runs/frozen_hard_v1/preflight/androidworld_hotfix_003_resume.json"
    )
    smoke = validate_cold_restart_smoke(smoke_path)
    client = frozen.TransformersClient(args.url)
    hotfix002.wait_for_model_service_stable(
        client,
        recovery_dir=record_dir / "hotfix_003_stability_gate",
        max_wait_seconds=args.max_model_recovery_seconds,
    )
    frozen.write_json(
        record_dir / "protocol_hotfix_003_authorization.json",
        {
            "schema_version": "protocol_hotfix_003_authorization.v1",
            "amendment": amendment_result_identity(),
            "prior_attempt_04": attempt_04_evidence,
            "cold_restart_smoke": {
                "path": smoke_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "sha256": file_sha256(smoke_path),
                "task_count": smoke["registered_android_world_tasks"],
                "screen_shape": smoke["screen_shape"],
            },
            "authorized_attempt": 5,
        },
    )
    task_registry = frozen.registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
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
    env = frozen.load_androidworld_env(
        adb_path=args.adb_path,
        console_port=args.console_port,
        grpc_port=args.grpc_port,
    )
    try:
        random.seed(schedule_record["instance_seed"])
        np.random.seed(schedule_record["instance_seed"])
        task_type = registered[schedule_record["task_class"]]
        task = task_type(task_type.generate_random_params())
        pair_hash = (
            sha256(str(task.goal).encode("utf-8")).hexdigest(),
            frozen.digest_json(frozen._json_safe(task.params)),
        )
        if pair_hash != expected_pair_hash:
            raise RuntimeError("Attempt 05 regenerated a different task.")
        policy, prompt, schema_path, max_calls = frozen.variant_runtime(
            schedule_record["variant"],
            client=client,
            max_steps=schedule_record["native_max_steps"],
            prompts=prompts,
        )
        controller = frozen.EpisodeController(
            client=client,
            system_prompt=prompt,
            max_steps=schedule_record["native_max_steps"],
            max_model_calls=max_calls,
            history_policy=policy,
            action_schema_path=schema_path,
        )
        episode_id = (
            f"{args.suite_id}_{schedule_record['sequence']:03d}_"
            f"{schedule_record['pair_id']}_{schedule_record['variant']}_a5"
        )
        summary = controller.run(
            env=env,
            task=task,
            episode_id=episode_id,
            episode_dir=attempt_05,
            seed=schedule_record["instance_seed"],
            protocol="androidworld_hard_protocol_v1",
            variant=schedule_record["variant"],
        )
        infra_code = frozen.classify_infrastructure(summary)
        if infra_code:
            frozen.write_json(
                record_dir / "hotfix_003_attempt_05_invalid.json",
                {
                    "attempt": 5,
                    "episode_id": episode_id,
                    "code": infra_code,
                    "error": summary["error"],
                },
            )
            raise RuntimeError("Attempt 05 had an infrastructure error.")
        if summary.get("error") is not None:
            raise RuntimeError("Attempt 05 had an unclassified error.")
        result = record_result_hotfix_003(
            schedule_record=schedule_record,
            summary=summary,
            attempt_count=5,
            infra_attempts=infra_payload["attempts"],
            episode_dir=attempt_05,
        )
        frozen.write_json(final_path, result)
        if result["audit_errors"]:
            raise RuntimeError("Attempt 05 protocol audit failed.")
        return result["episode_id"]
    finally:
        env.close()


def main() -> None:
    verify_freeze_hotfix_003()
    args = parse_wrapper_args()
    recovered = recover_attempt_05(
        args=args,
        suite_dir=args.output_root / args.suite_id,
    )
    if recovered:
        print(
            json.dumps(
                {"hotfix_003_recovered_episode_id": recovered},
                ensure_ascii=False,
            ),
            flush=True,
        )
    # Continue the ordinary schedule under hotfix-002.  The manifest-limited
    # exception is complete once the scored result exists.
    hotfix002.main()


if __name__ == "__main__":
    main()
