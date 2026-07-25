"""Protocol-v1 outage-continuation hotfix for one exhausted schedule cell.

This wrapper preserves protocol-v1 and hotfix-001 byte-for-byte.  It authorizes
exactly one fourth attempt for the manifest-named cell after three archived
attempts were invalidated by one flapping model-network outage.  It also
requires consecutive healthy endpoint checks before execution resumes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import time
from typing import Any

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_frozen_hard_suite as frozen  # noqa: E402
import run_frozen_hard_suite_hotfix_001 as hotfix001  # noqa: E402


AMENDMENT_ID = "protocol-v1-hotfix-002"
AMENDMENT_MANIFEST = (
    PROJECT_ROOT / "metadata/protocol_amendment_002.json"
)
ORIGINAL_WAIT_FOR_MODEL_SERVICE = frozen.wait_for_model_service


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_amendment_manifest(*, require_tag: bool) -> dict[str, Any]:
    if not AMENDMENT_MANIFEST.is_file():
        raise RuntimeError("Protocol amendment 002 manifest is absent.")
    manifest = json.loads(AMENDMENT_MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("amendment_id") != AMENDMENT_ID
        or manifest.get("status") != "active"
        or manifest.get("scope")
        != "single_cell_contiguous_model_outage_recovery"
    ):
        raise RuntimeError("Protocol amendment 002 identity is invalid.")
    for record in manifest["files"]:
        path = REPOSITORY_ROOT / record["path"]
        if (
            not path.is_file()
            or file_sha256(path) != record["sha256"]
            or path.stat().st_size != record["bytes"]
        ):
            raise RuntimeError(
                f"Protocol amendment 002 hash mismatch: {record['path']}"
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


def verify_freeze_hotfix_002() -> dict[str, Any]:
    freeze = hotfix001.verify_freeze_hotfix_001()
    manifest = load_amendment_manifest(require_tag=True)
    return {
        **freeze,
        "protocol_amendment_002": {
            "amendment_id": manifest["amendment_id"],
            "scope": manifest["scope"],
            "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
            "git_tag": manifest["git_tag"],
            "git_tag_commit": manifest["git_tag_commit"],
        },
    }


def _health_identity_ok(health: dict[str, Any]) -> bool:
    return (
        health.get("status") == "ok"
        and health.get("loaded") is True
        and health.get("backend") == frozen.EXPECTED_BACKEND
        and health.get("revision") == frozen.EXPECTED_REVISION
    )


def wait_for_model_service_stable(
    client: Any,
    *,
    recovery_dir: Path,
    max_wait_seconds: float = 1800.0,
    poll_seconds: float = 15.0,
    sleep_fn: Any = time.sleep,
    monotonic_fn: Any = time.monotonic,
    stable_checks: int = 3,
) -> dict[str, Any]:
    """Require consecutive exact-identity health checks after recovery."""
    if stable_checks < 1:
        raise ValueError("stable_checks must be positive.")
    started = monotonic_fn()
    initial = ORIGINAL_WAIT_FOR_MODEL_SERVICE(
        client,
        recovery_dir=recovery_dir,
        max_wait_seconds=max_wait_seconds,
        poll_seconds=poll_seconds,
        sleep_fn=sleep_fn,
        monotonic_fn=monotonic_fn,
    )
    attempts = [
        {
            "checked_at_utc": utc_now(),
            "healthy": True,
            "consecutive": 1,
            "backend": initial.get("backend"),
            "revision": initial.get("revision"),
        }
    ]
    consecutive = 1
    latest = initial
    while consecutive < stable_checks:
        elapsed = monotonic_fn() - started
        if elapsed >= max_wait_seconds:
            frozen.write_json(
                recovery_dir / "model_stability_gate.json",
                {
                    "schema_version": "model_stability_gate.v1",
                    "status": "timed_out",
                    "required_consecutive_checks": stable_checks,
                    "attempts": attempts,
                },
            )
            raise TimeoutError("Stable model-health window timed out.")
        sleep_fn(poll_seconds)
        try:
            latest = client.health()
            if not _health_identity_ok(latest):
                raise RuntimeError(
                    "Recovered endpoint identity differs from the freeze."
                )
            consecutive += 1
            attempts.append(
                {
                    "checked_at_utc": utc_now(),
                    "healthy": True,
                    "consecutive": consecutive,
                    "backend": latest.get("backend"),
                    "revision": latest.get("revision"),
                }
            )
        except RuntimeError:
            raise
        except Exception as exc:
            consecutive = 0
            attempts.append(
                {
                    "checked_at_utc": utc_now(),
                    "healthy": False,
                    "consecutive": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    frozen.write_json(
        recovery_dir / "model_stability_gate.json",
        {
            "schema_version": "model_stability_gate.v1",
            "status": "stable",
            "required_consecutive_checks": stable_checks,
            "poll_seconds": poll_seconds,
            "attempts": attempts,
        },
    )
    return latest


def validate_authorized_exhaustion(
    manifest: dict[str, Any],
    *,
    suite_id: str,
    schedule_record: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> tuple[str, str]:
    authorized = manifest["authorized_schedule_cell"]
    actual = {
        "suite_id": suite_id,
        "sequence": int(schedule_record["sequence"]),
        "pair_id": schedule_record["pair_id"],
        "variant": schedule_record["variant"],
        "task_class": schedule_record["task_class"],
    }
    expected = {
        key: authorized[key]
        for key in (
            "suite_id",
            "sequence",
            "pair_id",
            "variant",
            "task_class",
        )
    }
    if actual != expected:
        raise RuntimeError("Exhausted cell is not authorized by hotfix-002.")
    if len(attempts) != 3 or [item.get("attempt") for item in attempts] != [
        1,
        2,
        3,
    ]:
        raise RuntimeError("Hotfix-002 requires exactly three prior attempts.")
    if any(
        item.get("code") != "INFRA_MODEL_UNAVAILABLE"
        for item in attempts
    ):
        raise RuntimeError("Prior attempts were not all model outages.")
    hashes = {
        (item.get("goal_sha256"), item.get("params_sha256"))
        for item in attempts
    }
    if len(hashes) != 1 or None in next(iter(hashes)):
        raise RuntimeError("Prior attempt instance hashes are inconsistent.")
    return next(iter(hashes))


def record_result_hotfix_002(
    *,
    schedule_record: dict[str, Any],
    summary: dict[str, Any],
    attempt_count: int,
    infra_attempts: list[dict[str, Any]],
    episode_dir: Path,
) -> dict[str, Any]:
    result = hotfix001.record_result_hotfix_001(
        schedule_record=schedule_record,
        summary=summary,
        attempt_count=attempt_count,
        infra_attempts=infra_attempts,
        episode_dir=episode_dir,
    )
    first = result.pop("protocol_amendment")
    result["protocol_amendments"] = [
        first,
        amendment_result_identity(),
    ]
    return result


def recover_authorized_exhausted_cell(
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
    schedule_path = record_dir / "schedule_record.json"
    infra_path = record_dir / "infrastructure_attempts.json"
    if not schedule_path.is_file() or not infra_path.is_file():
        raise RuntimeError("Authorized exhausted cell evidence is absent.")
    schedule_record = json.loads(schedule_path.read_text(encoding="utf-8"))
    infra_payload = json.loads(infra_path.read_text(encoding="utf-8"))
    attempts = infra_payload["attempts"]
    expected_pair_hash = validate_authorized_exhaustion(
        manifest,
        suite_id=args.suite_id,
        schedule_record=schedule_record,
        attempts=attempts,
    )
    attempt = 4
    attempt_dir = record_dir / "attempt_04"
    if attempt_dir.exists():
        raise RuntimeError(
            "Authorized fourth attempt already exists without a scored result."
        )
    client = frozen.TransformersClient(args.url)
    wait_for_model_service_stable(
        client,
        recovery_dir=record_dir / "hotfix_002_stability_gate",
        max_wait_seconds=args.max_model_recovery_seconds,
    )
    frozen.write_json(
        record_dir / "protocol_hotfix_002_authorization.json",
        {
            "schema_version": "protocol_hotfix_002_authorization.v1",
            "authorized_at_utc": utc_now(),
            "amendment": amendment_result_identity(),
            "prior_invalid_attempt_count": 3,
            "authorized_attempt": 4,
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
            raise RuntimeError("Fourth attempt regenerated a different task.")
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
            f"{schedule_record['pair_id']}_{schedule_record['variant']}_a4"
        )
        summary = controller.run(
            env=env,
            task=task,
            episode_id=episode_id,
            episode_dir=attempt_dir,
            seed=schedule_record["instance_seed"],
            protocol="androidworld_hard_protocol_v1",
            variant=schedule_record["variant"],
        )
        infra_code = frozen.classify_infrastructure(summary)
        if infra_code:
            frozen.write_json(
                record_dir / "hotfix_002_attempt_04_invalid.json",
                {
                    "attempt": 4,
                    "episode_id": episode_id,
                    "code": infra_code,
                    "goal_sha256": pair_hash[0],
                    "params_sha256": pair_hash[1],
                    "error": summary["error"],
                },
            )
            raise RuntimeError(
                "The one authorized post-outage attempt was invalid."
            )
        if summary.get("error") is not None:
            frozen.write_json(
                record_dir / "hotfix_002_unclassified_error.json",
                summary,
            )
            raise RuntimeError("Fourth attempt had an unclassified error.")
        result = record_result_hotfix_002(
            schedule_record=schedule_record,
            summary=summary,
            attempt_count=attempt,
            infra_attempts=attempts,
            episode_dir=attempt_dir,
        )
        frozen.write_json(final_path, result)
        if result["audit_errors"]:
            raise RuntimeError("Fourth-attempt protocol audit failed.")
        return result["episode_id"]
    finally:
        env.close()


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


def main() -> None:
    verify_freeze_hotfix_002()
    args = parse_wrapper_args()
    suite_dir = args.output_root / args.suite_id
    recovered = recover_authorized_exhausted_cell(
        args=args,
        suite_dir=suite_dir,
    )
    if recovered:
        print(
            json.dumps(
                {"hotfix_002_recovered_episode_id": recovered},
                ensure_ascii=False,
            ),
            flush=True,
        )
    frozen.record_result = record_result_hotfix_002
    frozen.verify_freeze = verify_freeze_hotfix_002
    frozen.wait_for_model_service = wait_for_model_service_stable
    frozen.main()


if __name__ == "__main__":
    main()
