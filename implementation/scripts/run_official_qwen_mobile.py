"""Run the faithful Qwen3-VL Mobile Agent baseline on AndroidWorld."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import random
import shutil
import sys
from uuid import uuid4

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import android_world_controller, env_launcher  # noqa: E402
from raven_m.models.vllm_client import VLLMClient  # noqa: E402
from raven_m.multi_framework_benchmark.task_instances import (  # noqa: E402
    instantiate_verified,
    load_frozen_instances,
)
from raven_m.official_qwen_mobile.controller import (  # noqa: E402
    OfficialQwenMobileController,
)
from raven_m.official_qwen_mobile.source_document_coverage_gate import (  # noqa: E402
    SourceDocumentCoverageGate,
)
from raven_m.official_qwen_mobile.protocol import (  # noqa: E402
    EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT,
    OFFICIAL_SYSTEM_PROMPT,
    SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT,
    TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_official_public_v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--task", action="append")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Frozen task-instance manifest; preferred for comparable runs.",
    )
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument(
        "--step-cap",
        type=int,
        help="Diagnostic-only cap applied to each manifest task's frozen native limit.",
    )
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--generation-seed", type=int, default=3407)
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=3600.0,
        help=(
            "HTTP transport deadline for one model call. This does not alter "
            "generation; a shorter replacement-run value prevents a dead SSH "
            "tunnel from blocking the runner for an hour."
        ),
    )
    parser.add_argument(
        "--observation-backend",
        choices=("uiautomator", "a11y_forwarder"),
        default="uiautomator",
        help=(
            "Hidden AndroidWorld state backend. The official visual agent still "
            "receives screenshots only."
        ),
    )
    parser.add_argument("--run-stage", default="held_out_full")
    parser.add_argument(
        "--transient-observation-carry",
        action="store_true",
        help=(
            "Opt into the preregistered post-hoc prompt diagnostic that carries "
            "disappearing task values in the model's own Action summary."
        ),
    )
    parser.add_argument(
        "--transition-attested-history",
        action="store_true",
        help=(
            "Use the preregistered L4 diagnostic history policy: when an "
            "executed action causes no observable pixel/activity/UI transition, "
            "carry an unverified-effect attestation instead of model prose."
        ),
    )
    parser.add_argument(
        "--evidence-qualified-progress",
        action="store_true",
        help=(
            "Use the preregistered object-role evidence diagnostic prompt; "
            "history otherwise remains the official text-action summary."
        ),
    )
    parser.add_argument(
        "--source-document-coverage",
        action="store_true",
        help=(
            "Use the preregistered development prompt requiring auditable "
            "forward coverage of multi-record source documents."
        ),
    )
    parser.add_argument(
        "--source-document-coverage-gate",
        action="store_true",
        help=(
            "Use the source-document coverage prompt plus an executable gate "
            "that forces forward scans until the document end is attested."
        ),
    )
    parser.add_argument(
        "--stop-after-markor-source-exit",
        action="store_true",
        help=(
            "Bound a diagnostic at the first transition out of Markor "
            "DocumentActivity and skip the task evaluator."
        ),
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Mark the output as diagnostic and ineligible for held-out claims.",
    )
    parser.add_argument(
        "--held-out-ineligible-reason",
        help="Run full limits but explicitly forbid a pristine held-out claim.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "official_qwen_mobile",
    )
    args = parser.parse_args()

    if bool(args.task) == bool(args.manifest):
        parser.error("provide exactly one of --task or --manifest")
    if args.step_cap is not None and args.step_cap < 1:
        parser.error("--step-cap must be positive")
    if args.step_cap is not None and not args.diagnostic:
        parser.error("--step-cap requires --diagnostic")
    if args.stop_after_markor_source_exit and not args.diagnostic:
        parser.error("--stop-after-markor-source-exit requires --diagnostic")
    if args.request_timeout_seconds <= 0:
        parser.error("--request-timeout-seconds must be positive")
    diagnostic_modes = sum(
        bool(item)
        for item in (
            args.transient_observation_carry,
            args.transition_attested_history,
            args.evidence_qualified_progress,
            args.source_document_coverage,
            args.source_document_coverage_gate,
        )
    )
    if diagnostic_modes > 1:
        parser.error(
            "--transient-observation-carry, --transition-attested-history, "
            "--evidence-qualified-progress, and --source-document-coverage "
            "or --source-document-coverage-gate are mutually exclusive diagnostics"
        )
    held_out_eligible = not bool(args.diagnostic) and not bool(
        args.held_out_ineligible_reason
    )

    task_registry = registry.TaskRegistry()
    available = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    if args.manifest:
        specs = load_frozen_instances(args.manifest)
    else:
        specs = [
            {
                "task_class": task_name,
                "task_seed": args.seed,
                "native_max_steps": args.max_steps,
            }
            for task_name in args.task
        ]
    unknown = sorted(
        {str(item["task_class"]) for item in specs} - set(available)
    )
    if unknown:
        raise KeyError(f"Unknown AndroidWorld tasks: {unknown}")

    suite_id = f"official_qwen_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    suite_dir = args.output_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)
    if args.manifest:
        shutil.copy2(args.manifest, suite_dir / "manifest.snapshot.json")
    client = VLLMClient(
        args.url,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        backend_id=BACKEND_ID,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        seed=args.generation_seed,
        timeout_seconds=args.request_timeout_seconds,
    )
    health = client.health()
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
        a11y_method=(
            android_world_controller.A11yMethod.UIAUTOMATOR
            if args.observation_backend == "uiautomator"
            else android_world_controller.A11yMethod.A11Y_FORWARDER_APP
        ),
    )
    summaries: list[dict] = []
    try:
        for spec in specs:
            task_name = str(spec["task_class"])
            episode_seed = int(spec["task_seed"])
            if "task_params_hash" in spec and "goal_hash" in spec:
                task = instantiate_verified(available, spec)
            else:
                random.seed(episode_seed)
                np.random.seed(episode_seed)
                task_type = available[task_name]
                task = task_type(task_type.generate_random_params())
            native_limit = int(spec.get("native_max_steps", args.max_steps))
            effective_limit = (
                min(native_limit, args.step_cap)
                if args.step_cap is not None
                else native_limit
            )
            controller = OfficialQwenMobileController(
                client,
                max_steps=effective_limit,
                max_tokens=args.max_tokens,
                run_metadata={
                    "run_stage": args.run_stage,
                    "diagnostic": bool(args.diagnostic),
                    "held_out_eligible": held_out_eligible,
                    "held_out_ineligible_reason": args.held_out_ineligible_reason,
                    "native_max_steps": native_limit,
                    "effective_max_steps": effective_limit,
                    "step_cap": args.step_cap,
                    "hidden_observation_backend": args.observation_backend,
                    "model_visible_observation": "current_screenshot_only",
                    "transient_observation_carry": bool(
                        args.transient_observation_carry
                    ),
                    "transition_attested_history": bool(
                        args.transition_attested_history
                    ),
                    "evidence_qualified_progress": bool(
                        args.evidence_qualified_progress
                    ),
                    "source_document_coverage": bool(
                        args.source_document_coverage
                    ),
                    "source_document_coverage_gate": bool(
                        args.source_document_coverage_gate
                    ),
                    "request_timeout_seconds": args.request_timeout_seconds,
                    "stop_after_markor_source_exit": bool(
                        args.stop_after_markor_source_exit
                    ),
                },
                system_prompt=(
                    SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT
                    if (args.source_document_coverage or args.source_document_coverage_gate)
                    else (
                        EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT
                        if args.evidence_qualified_progress
                        else (
                            TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT
                            if args.transient_observation_carry
                            else OFFICIAL_SYSTEM_PROMPT
                        )
                    )
                ),
                history_policy=(
                    "source_document_coverage_action_ledger_v1"
                    if (args.source_document_coverage or args.source_document_coverage_gate)
                    else (
                        "official_text_action_summaries_only"
                        if args.evidence_qualified_progress
                        else (
                            "model_action_summaries_with_preregistered_transient_observation_carry"
                            if args.transient_observation_carry
                            else (
                                "transition_attested_action_summaries_v1"
                                if args.transition_attested_history
                                else "official_text_action_summaries_only"
                            )
                        )
                    )
                ),
                source_document_coverage_gate=(
                    SourceDocumentCoverageGate()
                    if args.source_document_coverage_gate
                    else None
                ),
                stop_after_markor_source_exit=args.stop_after_markor_source_exit,
            )
            episode_id = f"{task_name}_{episode_seed}_{uuid4().hex[:8]}"
            summaries.append(
                controller.run(
                    env=env,
                    task=task,
                    episode_id=episode_id,
                    episode_dir=suite_dir / "episodes" / episode_id,
                    seed=episode_seed,
                )
            )
    finally:
        env.close()

    aggregate = {
        "suite_id": suite_id,
        "model_health": health,
        "run_stage": args.run_stage,
        "diagnostic": bool(args.diagnostic),
        "held_out_eligible": held_out_eligible,
        "held_out_ineligible_reason": args.held_out_ineligible_reason,
        "hidden_observation_backend": args.observation_backend,
        "model_visible_observation": "current_screenshot_only",
        "transient_observation_carry": bool(args.transient_observation_carry),
        "transition_attested_history": bool(args.transition_attested_history),
        "evidence_qualified_progress": bool(args.evidence_qualified_progress),
        "request_timeout_seconds": args.request_timeout_seconds,
        "episode_count": len(summaries),
        "success_count": sum(int(item["success"]) for item in summaries),
        "success_rate": (
            sum(int(item["success"]) for item in summaries) / len(summaries)
            if summaries
            else None
        ),
        "episodes": [
            {
                "episode_id": item["episode_id"],
                "task_name": item["task_name"],
                "success": item["success"],
                "termination_reason": item["termination_reason"],
                "step_count": item["step_count"],
            }
            for item in summaries
        ],
    }
    (suite_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
