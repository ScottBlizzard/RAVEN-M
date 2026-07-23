"""Run the protocol-v1 AndroidWorld Hard schedule after an enforced freeze."""

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
import subprocess
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
from raven_m.history.policies import make_history_policy  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402
from run_method_dev_suite import audit_memory_episode  # noqa: E402


EXPECTED_BACKEND = "qwen3_vl_32b_transformers_bf16_4x4090_v1"
EXPECTED_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
INFRA_CODES = {
    "INFRA_EMULATOR_LOST",
    "INFRA_MODEL_UNAVAILABLE",
    "INFRA_ASSET_CORRUPT",
    "INFRA_EVALUATOR_EXCEPTION",
    "INFRA_HOST_RESOURCE",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def digest_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "safe.directory=D:/ZJU/Summer_Camp/RAVEN-M-Research",
            *args,
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed.")
    return result.stdout.strip()


def verify_freeze() -> dict[str, Any]:
    prereg_path = PROJECT_ROOT / "metadata/preregistration_v1.json"
    if not prereg_path.is_file():
        raise RuntimeError("Final preregistration is absent; Hard is blocked.")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("status") != "frozen"
        or not prereg.get("scored_hard_runs_permitted")
    ):
        raise RuntimeError("Preregistration does not permit scored Hard.")
    mismatches = []
    for record in prereg["files"]:
        path = REPOSITORY_ROOT / record["path"]
        if not path.is_file():
            mismatches.append(f"missing:{record['path']}")
            continue
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            mismatches.append(f"hash:{record['path']}")
    if mismatches:
        raise RuntimeError(
            "Protocol-critical hash mismatch: " + ", ".join(mismatches)
        )
    if "scored_runs_permitted: true" not in (
        REPOSITORY_ROOT / "04_protocols/environment_lock.yaml"
    ).read_text(encoding="utf-8"):
        raise RuntimeError("Environment lock still forbids scored runs.")
    audit = json.loads(
        (PROJECT_ROOT / "metadata/protocol_audit.json").read_text(
            encoding="utf-8"
        )
    )
    if audit.get("status") != "passed":
        raise RuntimeError("Protocol audit has not passed.")
    tag_commit = git("rev-parse", "protocol-v1^{commit}")
    if not tag_commit:
        raise RuntimeError("protocol-v1 tag is absent.")
    git("merge-base", "--is-ancestor", tag_commit, "HEAD")
    return {
        "preregistration_sha256": sha256(
            prereg_path.read_bytes()
        ).hexdigest(),
        "protocol_records_sha256": prereg["protocol_records_sha256"],
        "protocol_tag_commit": tag_commit,
    }


def load_androidworld_env(
    *,
    adb_path: str,
    console_port: int,
    grpc_port: int,
) -> Any:
    return env_launcher.load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=adb_path,
        grpc_port=grpc_port,
    )


def recover_androidworld_env(
    *,
    adb_path: str,
    console_port: int,
    grpc_port: int,
    recovery_dir: Path,
) -> Any:
    """Cold-restart and warm-verify AndroidWorld after an invalid infra attempt."""
    recovery_dir.mkdir(parents=True, exist_ok=True)
    stop_script = LOCAL_RUNTIME / "scripts/stop_emulator.ps1"
    start_script = LOCAL_RUNTIME / "scripts/start_emulator.ps1"
    smoke_script = LOCAL_RUNTIME / "scripts/androidworld_smoke.py"
    smoke_output = recovery_dir / "androidworld_smoke.json"
    commands = [
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(stop_script),
        ],
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(start_script),
            "-BootTimeoutSeconds",
            "300",
        ],
        [
            sys.executable,
            str(smoke_script),
            "--adb-path",
            adb_path,
            "--console-port",
            str(console_port),
            "--grpc-port",
            str(grpc_port),
            "--output",
            str(smoke_output),
        ],
    ]
    records = []
    for index, command in enumerate(commands, start=1):
        timeout = 60 if index == 1 else 420
        try:
            if index == 2:
                # The emulator is intentionally long-lived. On Windows its
                # descendants can inherit a captured PowerShell pipe even
                # after start_emulator.ps1 exits, preventing communicate()
                # from observing EOF. Direct the launcher output to files so
                # recovery waits only for the PowerShell process.
                stdout_path = recovery_dir / "start_emulator_stdout.log"
                stderr_path = recovery_dir / "start_emulator_stderr.log"
                with (
                    stdout_path.open("wb") as stdout_stream,
                    stderr_path.open("wb") as stderr_stream,
                ):
                    completed = subprocess.run(
                        command,
                        cwd=REPOSITORY_ROOT,
                        stdout=stdout_stream,
                        stderr=stderr_stream,
                        check=False,
                        timeout=timeout,
                    )
                command_stdout = stdout_path.read_bytes().decode(
                    "utf-8", errors="replace"
                )
                command_stderr = stderr_path.read_bytes().decode(
                    "utf-8", errors="replace"
                )
            else:
                completed = subprocess.run(
                    command,
                    cwd=REPOSITORY_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout,
                )
                command_stdout = completed.stdout
                command_stderr = completed.stderr
        except subprocess.TimeoutExpired as error:
            records.append(
                {
                    "index": index,
                    "command": command,
                    "returncode": None,
                    "timed_out_after_seconds": timeout,
                    "stdout": str(error.stdout or ""),
                    "stderr": str(error.stderr or ""),
                }
            )
            write_json(recovery_dir / "commands.json", records)
            raise RuntimeError(
                "AndroidWorld infrastructure recovery timed out at command "
                f"{index}; see {recovery_dir / 'commands.json'}."
            ) from error
        record = {
            "index": index,
            "command": command,
            "returncode": completed.returncode,
            "stdout": command_stdout,
            "stderr": command_stderr,
        }
        records.append(record)
        write_json(recovery_dir / "commands.json", records)
        if completed.returncode:
            raise RuntimeError(
                "AndroidWorld infrastructure recovery failed at command "
                f"{index}; see {recovery_dir / 'commands.json'}."
            )
    smoke = json.loads(smoke_output.read_text(encoding="utf-8"))
    if (
        smoke.get("status") != "ok"
        or smoke.get("registered_android_world_tasks") != 116
        or smoke.get("screen_shape") != [2400, 1080, 3]
    ):
        raise RuntimeError("AndroidWorld recovery smoke did not pass.")
    return load_androidworld_env(
        adb_path=adb_path,
        console_port=console_port,
        grpc_port=grpc_port,
    )


def all_calls(summary: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for step in summary.get("steps", []):
        calls.extend(step.get("model_calls", []))
        calls.extend(step.get("history_update", {}).get("model_calls", []))
    return calls


def classify_infrastructure(summary: dict[str, Any]) -> str | None:
    error = summary.get("error")
    if not error:
        return None
    text = json.dumps(error, ensure_ascii=False).lower()
    if "is_successful" in text:
        return "INFRA_EVALUATOR_EXCEPTION"
    if any(
        token in text
        for token in (
            "adb",
            "emulator",
            "device offline",
            "device not found",
            "grpc",
        )
    ):
        return "INFRA_EMULATOR_LOST"
    if any(
        token in text
        for token in (
            "http",
            "connection",
            "model endpoint",
            "remoteprotocolerror",
            "timeout",
        )
    ):
        return "INFRA_MODEL_UNAVAILABLE"
    if any(
        token in text
        for token in ("no space left", "out of memory", "disk full")
    ):
        return "INFRA_HOST_RESOURCE"
    if any(token in text for token in ("asset", "snapshot", "apk corrupt")):
        return "INFRA_ASSET_CORRUPT"
    return None


def variant_runtime(
    variant: str,
    *,
    client: TransformersClient,
    max_steps: int,
    prompts: dict[str, str],
) -> tuple[Any, str, Path | None, int]:
    if variant in {
        "B0",
        "B1",
        "B2",
        "B3",
        "B3_CTX",
        "B3_CALL",
    }:
        policy = make_history_policy(
            variant,
            client=client,
            summary_system_prompt=prompts["summary"],
        )
        summary_slots = (
            2 * math.ceil(max_steps / 5)
            if variant in {"B3", "B3_CTX"}
            else 0
        )
        max_calls = (
            3 * max_steps + 4
            if variant == "B3_CALL"
            else 2 * max_steps + summary_slots
        )
        return (
            policy,
            prompts["executor"],
            None,
            max_calls,
        )
    if variant in {
        "M0",
        "MREL",
        "MNO_WM",
        "MNO_VEL",
        "MNO_FRM",
        "MNO_PSI",
        "MNO_CRITIC",
    }:
        policy = make_history_policy(
            variant,
            client=client,
            summary_system_prompt="",
            planner_system_prompt=prompts["planner"],
            critic_system_prompt=prompts["critic"],
        )
        return (
            policy,
            prompts["executor_raven"],
            PROJECT_ROOT / "schemas/action.raven.v1.schema.json",
            3 * max_steps + 4,
        )
    if variant == "S0":
        policy = make_history_policy(
            variant,
            client=client,
            summary_system_prompt="",
        )
        return (
            policy,
            prompts["executor_raven"],
            PROJECT_ROOT / "schemas/action.raven.v1.schema.json",
            2 * max_steps,
        )
    raise ValueError(f"Unsupported frozen main variant: {variant}")


def record_result(
    *,
    schedule_record: dict[str, Any],
    summary: dict[str, Any],
    attempt_count: int,
    infra_attempts: list[dict[str, Any]],
    episode_dir: Path,
) -> dict[str, Any]:
    calls = all_calls(summary)
    max_prompt = max(
        (
            int(call.get("usage", {}).get("prompt_tokens", 0))
            for call in calls
        ),
        default=0,
    )
    prompt_tokens = sum(
        int(call.get("usage", {}).get("prompt_tokens", 0))
        for call in calls
    )
    completion_tokens = sum(
        int(call.get("usage", {}).get("completion_tokens", 0))
        for call in calls
    )
    model_latency_seconds = sum(
        float(call.get("raven_meta", {}).get("latency_seconds", 0.0))
        for call in calls
    )
    peak_vram_bytes = max(
        (
            int(call.get("raven_meta", {}).get("peak_vram_bytes", 0))
            for call in calls
        ),
        default=0,
    )
    steps = summary.get("steps", [])
    loop_event_count = sum(
        int(
            bool(
                step.get("history_update", {})
                .get("details", {})
                .get("loop_detected")
            )
        )
        for step in steps
    )
    memory_citation_decisions = sum(
        int(bool(step.get("decision", {}).get("memory_citations")))
        for step in steps
    )
    decisions_with_memory_bundle = 0
    for step in steps:
        rendered = step.get("history_context", {}).get("rendered", "")
        try:
            bundle = json.loads(rendered)
        except (json.JSONDecodeError, TypeError):
            bundle = {}
        if isinstance(bundle, dict) and bundle.get("items"):
            decisions_with_memory_bundle += 1
    started = datetime.fromisoformat(summary["started_at"])
    finished = datetime.fromisoformat(summary["finished_at"])
    memory_audit = (
        audit_memory_episode(episode_dir, summary["episode_id"])
        if schedule_record["variant"]
        in {
            "S0",
            "M0",
            "MREL",
            "MNO_WM",
            "MNO_VEL",
            "MNO_FRM",
            "MNO_PSI",
            "MNO_CRITIC",
        }
        else None
    )
    errors = []
    if max_prompt + 256 > 8192:
        errors.append("context cap exceeded")
    if memory_audit and memory_audit["errors"]:
        errors.extend(memory_audit["errors"])
    if summary.get("protocol") != "androidworld_hard_protocol_v1":
        errors.append("episode protocol label mismatch")
    return {
        **schedule_record,
        "episode_id": summary["episode_id"],
        "attempt_count": attempt_count,
        "invalid_infrastructure_attempts": infra_attempts,
        "task_goal": summary["task_goal"],
        "task_params": summary["task_params"],
        "goal_sha256": sha256(
            summary["task_goal"].encode("utf-8")
        ).hexdigest(),
        "params_sha256": digest_json(summary["task_params"]),
        "success": bool(summary["success"]),
        "failure_code": summary["failure_code"],
        "evaluator_reward": summary["evaluator_reward"],
        "decision_attempt_count": summary["decision_attempt_count"],
        "executed_action_count": summary["executed_action_count"],
        "executor_model_call_count": summary["executor_model_call_count"],
        "history_model_call_count": summary["history_model_call_count"],
        "model_call_count": summary["model_call_count"],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "model_latency_seconds": model_latency_seconds,
        "episode_wall_seconds": (finished - started).total_seconds(),
        "peak_vram_bytes": peak_vram_bytes,
        "loop_event_count": loop_event_count,
        "memory_citation_decision_count": memory_citation_decisions,
        "decisions_with_memory_bundle": decisions_with_memory_bundle,
        "first_pass_parse_rate": summary["first_pass_parse_rate"],
        "max_prompt_tokens": max_prompt,
        "memory_audit": memory_audit,
        "audit_errors": errors,
        "valid_scored_episode": not errors and summary.get("error") is None,
        "episode_path": episode_dir.relative_to(
            REPOSITORY_ROOT
        ).as_posix(),
    }


def aggregate(
    *,
    suite_id: str,
    phase: str,
    schedule_hash: str,
    freeze: dict[str, Any],
    health: dict[str, Any],
    results: list[dict[str, Any]],
    expected_count: int,
    finished: bool,
) -> dict[str, Any]:
    pairing: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for result in results:
        pairing[result["pair_id"]].add(
            (result["goal_sha256"], result["params_sha256"])
        )
    pair_errors = [
        pair_id for pair_id, hashes in pairing.items() if len(hashes) != 1
    ]
    audit_errors = [
        f"{item['episode_id']}:{error}"
        for item in results
        for error in item["audit_errors"]
    ]
    by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_variant[result["variant"]].append(result)
    variants = {}
    for variant, items in sorted(by_variant.items()):
        valid = [item for item in items if item["valid_scored_episode"]]
        variants[variant] = {
            "episode_count": len(items),
            "valid_scored_episode_count": len(valid),
            "success_count": sum(int(item["success"]) for item in valid),
            "task_success_rate": (
                sum(int(item["success"]) for item in valid) / len(valid)
                if valid
                else None
            ),
            "model_call_count": sum(
                item["model_call_count"] for item in valid
            ),
            "max_prompt_tokens": max(
                (item["max_prompt_tokens"] for item in valid),
                default=0,
            ),
        }
    return {
        "schema_version": "hard_suite_summary.v1",
        "suite_id": suite_id,
        "phase": phase,
        "updated_at_utc": utc_now(),
        "finished": finished,
        "expected_episode_count": expected_count,
        "completed_episode_count": len(results),
        "model_backend": health["backend"],
        "model_revision": health["revision"],
        "schedule_records_sha256": schedule_hash,
        "freeze": freeze,
        "pairing_error_count": len(pair_errors),
        "pairing_error_ids": pair_errors,
        "audit_error_count": len(audit_errors),
        "audit_errors": audit_errors,
        "variant_results": variants,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--phase",
        choices=[
            "breadth",
            "confirmatory_additional",
            "strict_control",
            "ablation_controls",
        ],
        required=True,
    )
    parser.add_argument("--suite-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs/frozen_hard_v1",
    )
    args = parser.parse_args()

    freeze = verify_freeze()
    disk = shutil.disk_usage(REPOSITORY_ROOT)
    if disk.free < 20 * 1024**3:
        raise RuntimeError(
            "Fewer than 20 GiB are free on the artifact volume; Hard is "
            "blocked before creating an episode."
        )
    schedule_file = PROJECT_ROOT / "configs/experiments/hard_schedule_v1.json"
    schedule = json.loads(schedule_file.read_text(encoding="utf-8"))
    selected = [
        item for item in schedule["records"] if item["phase"] == args.phase
    ]
    expected = {
        "breadth": 95,
        "confirmatory_additional": 114,
        "strict_control": 19,
        "ablation_controls": 136,
    }[args.phase]
    if len(selected) != expected:
        raise RuntimeError("Frozen phase size differs from preregistration.")
    suite_dir = args.output_root / args.suite_id
    suite_dir.mkdir(parents=True, exist_ok=True)
    write_json(suite_dir / "schedule.snapshot.json", selected)
    write_json(suite_dir / "freeze.snapshot.json", freeze)

    client = TransformersClient(args.url)
    health = client.health()
    if (
        health.get("backend") != EXPECTED_BACKEND
        or health.get("revision") != EXPECTED_REVISION
    ):
        raise RuntimeError("Model backend/revision differs from protocol v1.")
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
    results: list[dict[str, Any]] = []
    env = load_androidworld_env(
        adb_path=args.adb_path,
        console_port=args.console_port,
        grpc_port=args.grpc_port,
    )
    try:
        for record in selected:
            record_dir = suite_dir / "episodes" / (
                f"{record['sequence']:03d}_{record['pair_id']}_"
                f"{record['variant']}_{record['task_class']}"
            )
            final_path = record_dir / "scored_result.json"
            if final_path.is_file():
                result = json.loads(final_path.read_text(encoding="utf-8"))
                results.append(result)
                continue
            write_json(record_dir / "schedule_record.json", record)
            infra_attempts: list[dict[str, Any]] = []
            result = None
            expected_pair_hash: tuple[str, str] | None = None
            for attempt in range(1, 4):
                attempt_dir = record_dir / f"attempt_{attempt:02d}"
                random.seed(record["instance_seed"])
                np.random.seed(record["instance_seed"])
                task_type = registered[record["task_class"]]
                task = task_type(task_type.generate_random_params())
                pair_hash = (
                    sha256(str(task.goal).encode("utf-8")).hexdigest(),
                    digest_json(_json_safe(task.params)),
                )
                if expected_pair_hash and pair_hash != expected_pair_hash:
                    raise RuntimeError("Retry regenerated a different instance.")
                expected_pair_hash = pair_hash
                policy, prompt, schema_path, max_calls = variant_runtime(
                    record["variant"],
                    client=client,
                    max_steps=record["native_max_steps"],
                    prompts=prompts,
                )
                controller = EpisodeController(
                    client=client,
                    system_prompt=prompt,
                    max_steps=record["native_max_steps"],
                    max_model_calls=max_calls,
                    history_policy=policy,
                    action_schema_path=schema_path,
                )
                episode_id = (
                    f"{args.suite_id}_{record['sequence']:03d}_"
                    f"{record['pair_id']}_{record['variant']}_a{attempt}"
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=episode_id,
                    episode_dir=attempt_dir,
                    seed=record["instance_seed"],
                    protocol="androidworld_hard_protocol_v1",
                    variant=record["variant"],
                )
                infra_code = classify_infrastructure(summary)
                if summary.get("error") and infra_code is None:
                    write_json(
                        record_dir / "unclassified_controller_error.json",
                        summary,
                    )
                    raise RuntimeError(
                        "Unclassified controller error; protocol requires "
                        "manual engineering correction before continuation."
                    )
                if infra_code:
                    if infra_code not in INFRA_CODES:
                        raise RuntimeError("Unknown infrastructure code.")
                    infra_attempts.append(
                        {
                            "attempt": attempt,
                            "episode_id": episode_id,
                            "code": infra_code,
                            "error": summary["error"],
                        }
                    )
                    if (
                        infra_code == "INFRA_EMULATOR_LOST"
                        and attempt < 3
                    ):
                        env.close()
                        env = None
                        env = recover_androidworld_env(
                            adb_path=args.adb_path,
                            console_port=args.console_port,
                            grpc_port=args.grpc_port,
                            recovery_dir=(
                                record_dir
                                / f"recovery_after_attempt_{attempt:02d}"
                            ),
                        )
                    continue
                result = record_result(
                    schedule_record=record,
                    summary=summary,
                    attempt_count=attempt,
                    infra_attempts=infra_attempts,
                    episode_dir=attempt_dir,
                )
                break
            if result is None:
                write_json(
                    record_dir / "infrastructure_retries_exhausted.json",
                    {"attempts": infra_attempts},
                )
                raise RuntimeError(
                    "All permitted infrastructure retries were exhausted."
                )
            write_json(final_path, result)
            results.append(result)
            if result["audit_errors"]:
                raise RuntimeError(
                    "Protocol audit invariant failed; scored execution stops "
                    "without changing the frozen method."
                )
            progress = aggregate(
                suite_id=args.suite_id,
                phase=args.phase,
                schedule_hash=schedule["records_sha256"],
                freeze=freeze,
                health=health,
                results=results,
                expected_count=expected,
                finished=False,
            )
            write_json(suite_dir / "suite_progress.json", progress)
            print(
                json.dumps(
                    {
                        "completed": len(results),
                        "expected": expected,
                        "latest": result["episode_id"],
                        "success": result["success"],
                        "audit_errors": result["audit_errors"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        final = aggregate(
            suite_id=args.suite_id,
            phase=args.phase,
            schedule_hash=schedule["records_sha256"],
            freeze=freeze,
            health=health,
            results=results,
            expected_count=expected,
            finished=True,
        )
        write_json(suite_dir / "suite_summary.json", final)
        write_json(suite_dir / "suite_progress.json", final)
        if (
            final["pairing_error_count"]
            or final["audit_error_count"]
            or final["completed_episode_count"] != expected
        ):
            raise SystemExit(3)
    finally:
        if env is not None:
            env.close()


if __name__ == "__main__":
    main()
