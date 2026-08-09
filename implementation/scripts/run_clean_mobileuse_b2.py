"""Run the pre-registered B2 Clean MobileUse smoke or five-task diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import random
import shutil
from uuid import uuid4

import numpy as np

import run_mobileuse_hard as pf01
from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient
from raven_m.public_frameworks.mobileuse.clean_controller import (
    ARM_ID,
    CleanMobileUseController,
)
from raven_m.public_frameworks.mobileuse.logging import LayeredEventLog


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_mobileuse_b2_v1"
TASK_ORDER = ["H12", "H08", "H05", "H01", "H14"]
CONFIG_PATH = (
    pf01.REPOSITORY_ROOT
    / "implementation/configs/b2_clean_mobileuse_qwen3_vl_32b_diagnostic_seed20260806.yaml"
)
MANIFEST_PATH = (
    pf01.REPOSITORY_ROOT
    / "implementation/configs/b2_clean_mobileuse_diagnostic_seed20260806.final.json"
)
PREREG_JSON = (
    pf01.REPOSITORY_ROOT
    / "protocols/B2_CLEAN_MOBILEUSE_DIAGNOSTIC_PREREG.json"
)
PREREG_MD = (
    pf01.REPOSITORY_ROOT
    / "protocols/B2_CLEAN_MOBILEUSE_DIAGNOSTIC_PREREG.md"
)
EVIDENCE_DIR = (
    pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_b2"
)
FREEZE_PATH = EVIDENCE_DIR / "B2_FREEZE_AFTER_SMOKE.json"
PREFLIGHT_PATH = EVIDENCE_DIR / "B2_ZERO_GENERATION_PREFLIGHT.json"
FREEZE_FILES = [
    CONFIG_PATH,
    MANIFEST_PATH,
    PREREG_JSON,
    PREREG_MD,
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/clean_controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/action_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/logging.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/mechanism_metrics.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/prompt_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/models/vllm_multi_image_client.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/preflight_clean_mobileuse_b2.py",
    Path(__file__).resolve(),
]


def digest(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def current_freeze() -> dict[str, str]:
    return {
        str(path.relative_to(pf01.REPOSITORY_ROOT)).replace("\\", "/"): digest(path)
        for path in FREEZE_FILES
    }


def model_client(url: str, timeout: float) -> VLLMMultiImageClient:
    return VLLMMultiImageClient(
        url,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        backend_id=BACKEND_ID,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        seed=3407,
        timeout_seconds=timeout,
    )


def load_diagnostic_specs() -> list[dict]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if value.get("androidworld_commit") != "3e50888527ef9f29b9157ecd537e408008bb1c85":
        raise RuntimeError("AndroidWorld source-lock drift")
    if value.get("arm_id") != ARM_ID:
        raise RuntimeError("B2 manifest arm drift")
    specs = value.get("instances") or []
    if [item.get("task_id") for item in specs] != TASK_ORDER:
        raise RuntimeError("B2 diagnostic task order drift")
    if any(int(item.get("task_seed")) != 20260806 for item in specs):
        raise RuntimeError("B2 diagnostic seed drift")
    return specs


def load_created_summary(suite_dir: Path, before: set[Path]) -> dict:
    created = list(set((suite_dir / "episodes").glob("*")) - before)
    if len(created) != 1:
        raise RuntimeError(f"Expected one created episode, found {len(created)}")
    path = created[0] / "summary.json"
    if not path.is_file():
        raise RuntimeError("Invalid episode did not preserve summary.json")
    return json.loads(path.read_text(encoding="utf-8"))


def event_metrics(summaries: list[dict]) -> dict:
    roles: Counter[str] = Counter()
    hash_errors: list[str] = []
    false_successes: list[str] = []
    decisions = 0
    for summary in summaries:
        path = Path(summary["events_path"])
        if not path.is_absolute():
            path = pf01.REPOSITORY_ROOT / path
        if path.is_file():
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            roles.update(
                record.get("role") for record in records
                if record.get("event") == "model_request" and record.get("role")
            )
            hash_errors.extend(
                f"{summary['task_id']}:{error}"
                for error in LayeredEventLog.validate(path)
            )
        decisions += int(summary.get("operator_decisions") or 0)
        claimed = "FINISHED" in json.dumps(
            summary.get("controller_status"), ensure_ascii=False
        )
        if claimed and float(summary.get("evaluator_reward") or 0.0) != 1.0:
            false_successes.append(summary["task_id"])
    total_requests = sum(roles.values())
    return {
        "model_requests_by_role": dict(sorted(roles.items())),
        "total_model_requests": total_requests,
        "operator_decisions": decisions,
        "model_requests_per_operator_decision": (
            total_requests / decisions if decisions else None
        ),
        "false_success_task_ids": false_successes,
        "hash_chain_errors": hash_errors,
    }


def evaluate_gate(summaries: list[dict], metrics: dict) -> dict:
    by_id = {item["task_id"]: item for item in summaries}
    checks = {
        "five_valid": sum(bool(item.get("scientifically_valid")) for item in summaries) == 5,
        "h08_retained": float(by_id.get("H08", {}).get("evaluator_reward") or 0.0) == 1.0,
        "reward_at_least_2": sum(float(item.get("evaluator_reward") or 0.0) for item in summaries) >= 2.0,
        "false_success_at_most_1": len(metrics["false_success_task_ids"]) <= 1,
        "requests_per_decision_at_most_2_4": (
            metrics["model_requests_per_operator_decision"] is not None
            and metrics["model_requests_per_operator_decision"] <= 2.4
        ),
        "hash_chain_clean": not metrics["hash_chain_errors"],
        "no_implementation_or_infrastructure_errors": not any(item.get("error") for item in summaries),
    }
    return {
        "schema": "raven_m.b2_clean_mobileuse.expansion_gate.v1",
        "arm_id": ARM_ID,
        "pass": all(checks.values()),
        "checks": checks,
        "directive": (
            "freeze_same_code_for_full_seed_20260807"
            if all(checks.values())
            else "do_not_expand_preserve_diagnostic"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "diagnostic"), required=True)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=pf01.REPOSITORY_ROOT / "runs/public_framework/mobileuse_b2",
    )
    args = parser.parse_args()

    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("B2 zero-generation preflight has not run")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "pass":
        raise RuntimeError("B2 zero-generation preflight has not passed")
    if args.mode == "diagnostic":
        if not FREEZE_PATH.is_file():
            raise RuntimeError("B2 live smoke has not produced a freeze")
        frozen = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        if frozen.get("file_sha256") != current_freeze():
            raise RuntimeError("B2 source/config drift after smoke")

    client = model_client(args.url, args.request_timeout_seconds)
    health = client.health()
    env = pf01.env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
        a11y_method=pf01.android_world_controller.A11yMethod.UIAUTOMATOR,
    )
    registry_value = pf01.registry.TaskRegistry().get_registry(
        pf01.registry.TaskRegistry.ANDROID_WORLD_FAMILY
    )
    if args.mode == "smoke":
        task_name = "ContactsAddContact"
        random.seed(20260809)
        np.random.seed(20260809)
        task_type = registry_value[task_name]
        specs = [{
            "task_id": "B2_SMOKE",
            "task_class": task_name,
            "task_seed": 20260809,
            "native_max_steps": 3,
        }]
        tasks = [task_type(task_type.generate_random_params())]
    else:
        specs = load_diagnostic_specs()
        tasks = [pf01.instantiate_verified(registry_value, spec) for spec in specs]

    # Reuse the already-audited episode harness with a process-local controller
    # substitution. No PF01 source or frozen result is modified.
    pf01.MobileUseController = CleanMobileUseController
    pf01.ARM_ID = ARM_ID
    suite_id = (
        f"b2_{args.mode}_{datetime.now().strftime('%Y%m%dT%H%M%S')}_"
        f"{uuid4().hex[:8]}"
    )
    suite_dir = args.output_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(MANIFEST_PATH, suite_dir / "manifest.snapshot.json")
    summaries: list[dict] = []
    try:
        for spec, task in zip(specs, tasks):
            before = set((suite_dir / "episodes").glob("*"))
            try:
                summary = pf01.run_episode(
                    env=env,
                    task=task,
                    spec=spec,
                    client=client,
                    suite_dir=suite_dir,
                    mode=args.mode,
                )
            except RuntimeError:
                summary = load_created_summary(suite_dir, before)
            summaries.append(summary)
    finally:
        env.close()

    metrics = event_metrics(summaries)
    aggregate = {
        "schema": "raven_m.b2_clean_mobileuse.suite_summary.v1",
        "arm_id": ARM_ID,
        "suite_id": suite_id,
        "mode": args.mode,
        "model_health": health,
        "episode_count": len(summaries),
        "success_count": sum(int(item.get("success")) for item in summaries),
        "total_reward": sum(float(item.get("evaluator_reward") or 0.0) for item in summaries),
        "scientifically_valid_count": sum(int(item.get("scientifically_valid")) for item in summaries),
        **metrics,
        "episodes": summaries,
    }
    (suite_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.mode == "smoke":
        events = Path(summaries[0]["events_path"]).read_text(encoding="utf-8")
        required = (
            '"role": "Operator"',
            '"event": "role_schedule_decision"',
            '"event": "environment_action_complete"',
        )
        missing = [token for token in required if token not in events]
        if missing or not summaries[0].get("scientifically_valid"):
            raise RuntimeError(f"B2 smoke qualification failed: {missing}")
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        FREEZE_PATH.write_text(
            json.dumps({
                "schema": "raven_m.b2_clean_mobileuse.freeze_after_smoke.v1",
                "arm_id": ARM_ID,
                "smoke_suite": str(suite_dir),
                "smoke_aggregate_sha256": digest(suite_dir / "aggregate.json"),
                "file_sha256": current_freeze(),
            }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        gate = evaluate_gate(summaries, metrics)
        (suite_dir / "expansion_gate.json").write_text(
            json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        aggregate["expansion_gate"] = gate
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
