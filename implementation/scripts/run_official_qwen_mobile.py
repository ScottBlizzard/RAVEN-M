"""Run the faithful Qwen3-VL Mobile Agent baseline on AndroidWorld."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import random
import shutil
import subprocess
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
from raven_m.official_qwen_mobile.a1_contract import (  # noqa: E402
    A1_MANIFEST,
    A1_PREFLIGHT_REPORT,
    validate_preflight_report,
)
from raven_m.official_qwen_mobile.a2_contract import (  # noqa: E402
    A2_GUARD_REPLAY,
    A2_PREFLIGHT_REPORT,
    A2_REFERENCE_LEDGER,
    A2_RUNTIME_QUALIFICATION,
    current_source_freeze as current_a2_source_freeze,
    validate_preflight_report as validate_a2_preflight_report,
)
from raven_m.official_qwen_mobile.a2_suite import (  # noqa: E402
    episode_reference as a2_episode_reference,
    load_checkpoint as load_a2_checkpoint,
)
from raven_m.official_qwen_mobile.source_document_coverage_gate import (  # noqa: E402
    SourceDocumentCoverageGate,
)
from raven_m.official_qwen_mobile.protocol import (  # noqa: E402
    A1_WORKING_MEMORY_SYSTEM_PROMPT,
    A2_VERIFIED_PROGRESS_SYSTEM_PROMPT,
    A3_CONACT_SYSTEM_PROMPT,
    A4_WORKFLOW_SYSTEM_PROMPT,
    A5_VISUAL_GRAPH_SYSTEM_PROMPT,
    EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT,
    OFFICIAL_SYSTEM_PROMPT,
    SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT,
    TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT,
)
from raven_m.official_qwen_mobile.working_memory import ActionWorkingMemory  # noqa: E402
from raven_m.official_qwen_mobile.progress_memory import (  # noqa: E402
    RepeatedNoProgressGuard,
    VerifiedProgressMemory,
)
from raven_m.official_qwen_mobile.a345_memory import (  # noqa: E402
    FrozenWorkflowMemory,
    OnlinePageGraphMemory,
    ProactiveFoldedContextMemory,
)
from raven_m.official_qwen_mobile.a345_contract import (  # noqa: E402
    A345_GATE_TASKS,
    A345_REQUIRED_GATE_TASKS,
    A345_TERMINAL_CHECKPOINT_STATUSES,
    A4_WORKFLOW_BANK,
    activation_valid as _a345_activation_valid,
    validate_launch_receipt as validate_a345_launch_receipt,
    validate_preflight_report as validate_a345_preflight_report,
)
from raven_m.official_qwen_mobile.a678_memory import (  # noqa: E402
    ExactVisualRevisitActionOutcomeCache,
    GoalItemStatusLedger,
    ShortTransitionEpisodicBuffer,
)
from raven_m.official_qwen_mobile.a678_contract import (  # noqa: E402
    A0_PRESERVATION_TASKS,
    A7_CONTINUATION_CONFIG,
    A678_CONFIGS,
    A678_MECHANISMS,
    exact_completion_errors as a678_completion_errors,
    preservation_report as a678_preservation_report,
    validate_launch_receipt as validate_a678_launch_receipt,
    validate_preflight_report as validate_a678_preflight_report,
)
from raven_m.official_qwen_mobile.a7_continuation import (  # noqa: E402
    CONTINUATION_EXPERIMENT_ID as A7_CONTINUATION_EXPERIMENT_ID,
    canonicalize_summaries as canonicalize_a7_summaries,
    gate_report as a7_gate_report,
    validate_plan as validate_a7_continuation_plan,
)
from raven_m.official_qwen_mobile.a8_failure_aware_revisit import (  # noqa: E402
    FailureAwareExactRevisitMemory,
)
from raven_m.official_qwen_mobile.a9_recurrence_memory import (  # noqa: E402
    SparseRecurrenceCanaryMemory,
)
from raven_m.official_qwen_mobile.a89_diagnostic import (  # noqa: E402
    CLAIM_BOUNDARY as A89_DIAGNOSTIC_CLAIM_BOUNDARY,
    EXPERIMENT_IDS as A89_DIAGNOSTIC_EXPERIMENT_IDS,
    completion_errors as a89_diagnostic_completion_errors,
    report as a89_diagnostic_report,
    select_four_task_specs as select_a89_diagnostic_specs,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_official_public_v1"
A7_REMAINING_AFTER_GATE_TASKS = (
    "OsmAndMarker",
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)
def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_a4_workflows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("A4 canonical donor bank must be a JSON object")
    if payload.get("schema") != "a4.frozen_donor_workflow_bank.v1" or payload.get("status") != "ready":
        raise RuntimeError("A4 canonical donor bank is not ready or has wrong schema")
    if payload.get("generation_calls") != 0 or payload.get("scored_hard_inputs_used") is not False:
        raise RuntimeError("A4 canonical donor bank provenance is invalid")
    workflows = payload.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise RuntimeError("A4 canonical donor bank has no workflows")
    workflow_sha = sha256(json.dumps(workflows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if payload.get("bank_sha256") != workflow_sha:
        raise RuntimeError("A4 workflow payload hash drifted")
    return workflows


def _episode_infrastructure_valid(summary: dict) -> bool:
    return (
        summary.get("error") is None
        and summary.get("evaluator_reward") is not None
        and not summary.get("lifecycle_errors")
    )


def _usage_totals(summaries: list[dict]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for summary in summaries:
        for step in summary.get("steps", []):
            usage = (step.get("model_call") or {}).get("usage") or {}
            for key in totals:
                totals[key] += int(usage.get(key) or 0)
    return totals


def _json_digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
        "--a1-working-memory",
        action="store_true",
        help="Enable the preregistered bounded Action-record working memory.",
    )
    parser.add_argument(
        "--a2-verified-progress-memory",
        action="store_true",
        help="Enable compact verified-progress memory and the separately audited cost guard.",
    )
    parser.add_argument(
        "--a345-arm",
        choices=("a3", "a4", "a5"),
        help="Run one frozen A3/A4/A5 public-memory-kernel arm.",
    )
    parser.add_argument(
        "--a678-arm",
        choices=("a6", "a7", "a8", "a8v2", "a9"),
        help="Run one frozen controller-authored A6-A9 memory arm.",
    )
    parser.add_argument(
        "--a678-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a678-launch-receipt",
        type=Path,
        help="Live server receipt bound to the final A678 zero-generation preflight.",
    )
    parser.add_argument(
        "--a7-continuation-plan",
        type=Path,
        help="Zero-generation plan for the gated A7 continuation campaign.",
    )
    parser.add_argument(
        "--a7-parent-suite-dir",
        type=Path,
        help="Immutable seven-episode parent A7 suite referenced by the continuation plan.",
    )
    parser.add_argument(
        "--a7-post-gate-diagnostic",
        action="store_true",
        help=(
            "Run only SportsTrackerTotalDurationForCategoryThisWeek as an explicitly "
            "ineligible A7 diagnostic after a terminal preservation-gate failure."
        ),
    )
    parser.add_argument(
        "--a7-post-gate-remaining-diagnostic",
        action="store_true",
        help=(
            "Run the nine tasks remaining after the A7 preservation gate as an "
            "explicitly ineligible completion diagnostic."
        ),
    )
    parser.add_argument(
        "--a89-four-task-diagnostic-replication",
        action="store_true",
        help=(
            "Rerun all four A0-success tasks for A8-v2 or A9 without reward "
            "fail-fast. Diagnostic only: never repairs the original gate or "
            "releases the remaining fifteen tasks."
        ),
    )
    parser.add_argument(
        "--a345-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence" / "a345" / "A345_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a345-workflow-bank",
        type=Path,
        default=REPOSITORY_ROOT / "evidence" / "a345" / "A4_FROZEN_DONOR_WORKFLOW_BANK.json",
    )
    parser.add_argument(
        "--a345-launch-receipt",
        type=Path,
        help="Live frozen-server receipt created after GPU start and before the first scored call.",
    )
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
    parser.add_argument(
        "--resume-suite-dir",
        type=Path,
        help="Resume a checkpointed scored-memory suite without rerunning valid completed tasks.",
    )
    parser.add_argument(
        "--a1-preflight-report",
        type=Path,
        default=A1_PREFLIGHT_REPORT,
    )
    parser.add_argument(
        "--a2-preflight-report",
        type=Path,
        default=A2_PREFLIGHT_REPORT,
    )
    parser.add_argument(
        "--a2-reference-ledger", type=Path, default=A2_REFERENCE_LEDGER
    )
    parser.add_argument(
        "--a2-runtime-qualification", type=Path, default=A2_RUNTIME_QUALIFICATION
    )
    parser.add_argument(
        "--a2-launch-receipt",
        type=Path,
        help="Live GPU server launch receipt; mandatory for scored A2.",
    )
    args = parser.parse_args()

    if bool(args.a7_continuation_plan) != bool(args.a7_parent_suite_dir):
        parser.error(
            "--a7-continuation-plan and --a7-parent-suite-dir must be supplied together"
        )
    a7_gated_continuation = bool(args.a7_continuation_plan)
    if a7_gated_continuation and args.a678_arm != "a7":
        parser.error("A7 gated continuation requires --a678-arm a7")
    if args.a7_post_gate_diagnostic and args.a7_post_gate_remaining_diagnostic:
        parser.error("select only one A7 post-gate diagnostic schedule")
    a7_sports_diagnostic = bool(args.a7_post_gate_diagnostic)
    a7_remaining_diagnostic = bool(args.a7_post_gate_remaining_diagnostic)
    a7_post_gate_diagnostic = a7_sports_diagnostic or a7_remaining_diagnostic
    if a7_post_gate_diagnostic:
        if args.a678_arm != "a7" or not args.diagnostic:
            parser.error(
                "--a7-post-gate-diagnostic requires --a678-arm a7 and --diagnostic"
            )
        if a7_gated_continuation or args.task or args.manifest is None:
            parser.error(
                "A7 post-gate diagnostic requires only the frozen manifest, not a task or continuation plan"
            )
    a89_four_task_diagnostic = bool(args.a89_four_task_diagnostic_replication)
    if a89_four_task_diagnostic:
        if args.a678_arm not in {"a8v2", "a9"} or not args.diagnostic:
            parser.error(
                "--a89-four-task-diagnostic-replication requires "
                "--a678-arm a8v2/a9 and --diagnostic"
            )
        if (
            a7_gated_continuation
            or a7_post_gate_diagnostic
            or args.task
            or args.manifest is None
            or args.resume_suite_dir is not None
        ):
            parser.error(
                "A8/A9 four-task diagnostic requires a fresh suite using only "
                "the frozen manifest"
            )

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
            args.a1_working_memory,
            args.a2_verified_progress_memory,
            args.a345_arm,
            args.a678_arm,
        )
    )
    if diagnostic_modes > 1:
        parser.error(
            "--transient-observation-carry, --transition-attested-history, "
            "--evidence-qualified-progress, and --source-document-coverage "
            "--source-document-coverage-gate, --a1-working-memory, and "
            "--a2-verified-progress-memory, --a345-arm, and --a678-arm are mutually exclusive"
        )
    held_out_eligible = not bool(args.diagnostic) and not bool(
        args.held_out_ineligible_reason
    )
    a345_scored_arm = bool(args.a345_arm)
    a678_memory_arm = bool(args.a678_arm)
    a678_post_gate_diagnostic = a7_post_gate_diagnostic or a89_four_task_diagnostic
    a678_scored_arm = a678_memory_arm and not a678_post_gate_diagnostic
    prospective_gate_arm = (
        args.a678_arm in {"a8v2", "a9"} and not a89_four_task_diagnostic
    )
    held_out_ineligible_reason = args.held_out_ineligible_reason
    if a678_scored_arm:
        # This seed and its A0/A1/A2/A3-A5 outcomes have already been inspected.
        # A6-A8 are valid paired mechanism comparisons, not held-out evidence.
        held_out_eligible = False
        held_out_ineligible_reason = "post_observed_seed20260806_memory_mechanism_comparison"
    scored_memory_arm = bool(
        args.a1_working_memory
        or args.a2_verified_progress_memory
        or a345_scored_arm
        or a678_scored_arm
    )
    if (
        args.resume_suite_dir is not None
        and not scored_memory_arm
        and not a678_post_gate_diagnostic
    ):
        parser.error("--resume-suite-dir is restricted to scored memory arms")
    if scored_memory_arm:
        if args.task or args.manifest is None:
            parser.error("scored memory arms require the frozen 19-task manifest")
        if args.step_cap is not None or args.diagnostic or args.held_out_ineligible_reason:
            parser.error("scored memory runs forbid step caps, diagnostic mode, and ineligible labels")
        if args.generation_seed != 3407 or args.max_tokens != 32768:
            parser.error("scored memory generation seed/max tokens drifted")
        if args.observation_backend != "uiautomator":
            parser.error("scored memory hidden observation backend must match A0 uiautomator")
        if _sha256(args.manifest.resolve()) != _sha256(A1_MANIFEST.resolve()):
            parser.error("memory-arm manifest differs from the frozen A0 first-seed manifest")
        if a678_scored_arm:
            if not args.a678_preflight_report.is_file():
                parser.error(f"A6/A7/A8 preflight is missing: {args.a678_preflight_report}")
            try:
                validate_a678_preflight_report(args.a678_preflight_report.resolve())
            except Exception as exc:
                parser.error(str(exc))
            if args.a678_launch_receipt is None or not args.a678_launch_receipt.is_file():
                parser.error("A6/A7/A8 scored generation requires a live launch receipt")
            try:
                validate_a678_launch_receipt(
                    args.a678_launch_receipt.resolve(),
                    preflight_path=args.a678_preflight_report.resolve(),
                )
            except Exception as exc:
                parser.error(str(exc))
        elif a345_scored_arm:
            if not args.a345_preflight_report.is_file():
                parser.error(f"A3/A4/A5 preflight is missing: {args.a345_preflight_report}")
            try:
                preflight = validate_a345_preflight_report(args.a345_preflight_report.resolve())
            except Exception as exc:
                parser.error(str(exc))
            if args.a345_arm == "a4" and not args.a345_workflow_bank.is_file():
                parser.error("A4 requires the frozen independent-donor workflow bank")
            if args.a345_arm == "a4":
                if args.a345_workflow_bank.resolve() != A4_WORKFLOW_BANK.resolve():
                    parser.error("A4 scored run must use the canonical preflight-qualified workflow bank")
                expected_bank_sha = (preflight.get("checks") or {}).get(
                    "a4_workflow_bank_sha256"
                )
                if expected_bank_sha != _sha256(args.a345_workflow_bank.resolve()):
                    parser.error("A4 workflow bank drifted after zero-generation preflight")
            if args.a345_launch_receipt is None or not args.a345_launch_receipt.is_file():
                parser.error("A3/A4/A5 scored generation requires a live launch receipt")
            try:
                validate_a345_launch_receipt(
                    args.a345_launch_receipt.resolve(),
                    preflight_path=args.a345_preflight_report.resolve(),
                )
            except Exception as exc:
                parser.error(str(exc))
        elif args.a1_working_memory:
            validate_preflight_report(args.a1_preflight_report.resolve())
        else:
            validate_a2_preflight_report(args.a2_preflight_report.resolve())
            for evidence_path, label in (
                (args.a2_reference_ledger, "A0/A1 reference ledger"),
                (A2_GUARD_REPLAY, "A1 exact-guard replay"),
                (args.a2_runtime_qualification, "A2 runtime qualification"),
            ):
                if not evidence_path.is_file():
                    parser.error(f"{label} is missing: {evidence_path}")
            replay = json.loads(A2_GUARD_REPLAY.read_text(encoding="utf-8"))
            if replay.get("generation_calls") != 0 or not replay.get("qualification_pass"):
                parser.error("A1 exact-guard replay qualification failed")
            runtime = json.loads(args.a2_runtime_qualification.read_text(encoding="utf-8"))
            if runtime.get("status") != "pass" or runtime.get("generation_calls") != 0:
                parser.error("A2 runtime qualification failed")
            if args.a2_launch_receipt is None or not args.a2_launch_receipt.is_file():
                parser.error("scored A2 requires --a2-launch-receipt from the live frozen server")

    if a678_post_gate_diagnostic:
        if _sha256(args.manifest.resolve()) != _sha256(A1_MANIFEST.resolve()):
            parser.error("A678 diagnostic manifest differs from the frozen manifest")
        if args.generation_seed != 3407 or args.max_tokens != 32768:
            parser.error("A678 diagnostic generation parameters drifted")
        if args.observation_backend != "uiautomator":
            parser.error("A678 diagnostic must use uiautomator")
        if not args.a678_preflight_report.is_file():
            parser.error(f"A6-A9 preflight is missing: {args.a678_preflight_report}")
        try:
            validate_a678_preflight_report(args.a678_preflight_report.resolve())
        except Exception as exc:
            parser.error(str(exc))
        if args.a678_launch_receipt is None or not args.a678_launch_receipt.is_file():
            parser.error("A678 diagnostic requires a live launch receipt")
        try:
            validate_a678_launch_receipt(
                args.a678_launch_receipt.resolve(),
                preflight_path=args.a678_preflight_report.resolve(),
            )
        except Exception as exc:
            parser.error(str(exc))
        held_out_eligible = False
        held_out_ineligible_reason = (
            "post_terminal_A7_gate_failure_requested_diagnostic_only"
            if a7_post_gate_diagnostic
            else "A8_A9_four_task_diagnostic_replication_not_gate_repair"
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
    if a7_post_gate_diagnostic:
        selected_names = (
            {"SportsTrackerTotalDurationForCategoryThisWeek"}
            if a7_sports_diagnostic
            else set(A7_REMAINING_AFTER_GATE_TASKS)
        )
        specs = [
            item
            for item in specs
            if str(item["task_class"]) in selected_names
            and int(item["task_seed"]) == 20260806
        ]
        expected_diagnostic_count = 1 if a7_sports_diagnostic else 9
        if len(specs) != expected_diagnostic_count:
            raise RuntimeError(
                "A7 post-gate diagnostic resolved an unexpected frozen task count"
            )
    elif a89_four_task_diagnostic:
        specs = select_a89_diagnostic_specs(specs)
    if scored_memory_arm:
        specs = [item for item in specs if int(item["task_seed"]) == 20260806]
        if len(specs) != 19 or len({item["task_class"] for item in specs}) != 19:
            raise RuntimeError("memory-arm seed filter did not produce exactly 19 unique Hard tasks")
        if a345_scored_arm:
            by_name = {str(item["task_class"]): item for item in specs}
            missing_gate = sorted(set(A345_GATE_TASKS) - set(by_name))
            if missing_gate:
                raise RuntimeError(f"A3/A4/A5 gate tasks missing from manifest: {missing_gate}")
            remaining = [item for item in specs if str(item["task_class"]) not in A345_GATE_TASKS]
            specs = [by_name[name] for name in A345_GATE_TASKS] + remaining
        elif prospective_gate_arm:
            by_name = {str(item["task_class"]): item for item in specs}
            missing_gate = sorted(set(A0_PRESERVATION_TASKS) - set(by_name))
            if missing_gate:
                raise RuntimeError(
                    f"{str(args.a678_arm).upper()} gate tasks missing from manifest: {missing_gate}"
                )
            remaining = [
                item
                for item in specs
                if str(item["task_class"]) not in A0_PRESERVATION_TASKS
            ]
            specs = [by_name[name] for name in A0_PRESERVATION_TASKS] + remaining
    canonical_specs = list(specs)
    unknown = sorted(
        {str(item["task_class"]) for item in specs} - set(available)
    )
    if unknown:
        raise KeyError(f"Unknown AndroidWorld tasks: {unknown}")

    expected_keys = [
        (str(item["task_class"]), int(item["task_seed"])) for item in canonical_specs
    ]
    expected_keys_sha256 = _json_digest(expected_keys)
    a7_continuation_plan: dict | None = None
    a7_parent_snapshot: dict | None = None
    if a7_gated_continuation:
        a7_continuation_plan, a7_parent_snapshot = validate_a7_continuation_plan(
            plan_path=args.a7_continuation_plan.resolve(),
            parent_suite_dir=args.a7_parent_suite_dir.resolve(),
            canonical_specs=canonical_specs,
            manifest_path=args.manifest.resolve(),
        )
        by_key = {
            (str(item["task_class"]), int(item["task_seed"])): item
            for item in canonical_specs
        }
        scheduled_keys = [
            (str(item[0]), int(item[1]))
            for item in a7_continuation_plan["execution_schedule"]
        ]
        specs = [by_key[key] for key in scheduled_keys]
    a2_preflight = (
        json.loads(args.a2_preflight_report.read_text(encoding="utf-8"))
        if args.a2_verified_progress_memory else None
    )
    a2_runtime = (
        json.loads(args.a2_runtime_qualification.read_text(encoding="utf-8"))
        if args.a2_verified_progress_memory else None
    )
    a2_launch = (
        json.loads(args.a2_launch_receipt.read_text(encoding="utf-8"))
        if args.a2_verified_progress_memory else None
    )
    if args.a2_verified_progress_memory:
        remote_runtime = (a2_runtime or {}).get("remote_model") or {}
        if (
            a2_launch.get("status") != "pass"
            or a2_launch.get("generation_calls") != 0
            or a2_launch.get("model_realpath") != remote_runtime.get("model_realpath")
            or a2_launch.get("model_manifest_sha256") != remote_runtime.get("model_manifest_sha256")
            or a2_launch.get("remote_qualification_sha256") != a2_runtime.get("remote_model_report_sha256")
            or a2_launch.get("served_model_ids_observed") != [MODEL_ID]
            or remote_runtime.get("model_realpath") not in (a2_launch.get("process_cmdline") or [])
            or "serve" not in (a2_launch.get("process_cmdline") or [])
            or int(a2_launch.get("port", -1)) != 18000
        ):
            raise RuntimeError("live A2 server launch receipt is not bound to qualified model/runtime")

    run_signature = {
        "experiment_id": (
            (
                "A7_POST_GATE_SPORTS_DIAGNOSTIC_QWEN3VL32B_AW_HARD_S20260806_V1"
                if a7_sports_diagnostic
                else "A7_POST_GATE_REMAINING9_DIAGNOSTIC_QWEN3VL32B_AW_HARD_S20260806_V1"
            )
            if a7_post_gate_diagnostic
            else A89_DIAGNOSTIC_EXPERIMENT_IDS[str(args.a678_arm)]
            if a89_four_task_diagnostic
            else "A2_VERIFIED_PROGRESS_MEMORY_QWEN3VL32B_AW_HARD_S20260806_V1R1"
            if args.a2_verified_progress_memory
            else (
                f"{args.a345_arm.upper()}_PUBLIC_MEMORY_KERNEL_QWEN3VL32B_AW_HARD_S20260806_V1"
                if a345_scored_arm
                else (
                    (
                        A7_CONTINUATION_EXPERIMENT_ID
                        if a7_gated_continuation
                        else {
                            "a6": "A6_SHORT_EPISODIC_QWEN3VL32B_AW_HARD_S20260806_V1",
                            "a7": "A7_GOAL_ITEM_LEDGER_QWEN3VL32B_AW_HARD_S20260806_V1",
                            "a8": "A8_EXACT_REVISIT_CACHE_QWEN3VL32B_AW_HARD_S20260806_V1",
                            "a8v2": "A8_FAILURE_AWARE_EXACT_REVISIT_QWEN3VL32B_AW_HARD_S20260806_V2",
                            "a9": "A9_SPARSE_RECURRENCE_CANARY_QWEN3VL32B_AW_HARD_S20260806_V1",
                        }[args.a678_arm]
                    )
                    if a678_scored_arm else None
                )
            )
        ),
        "method": (
            A678_MECHANISMS[str(args.a678_arm)]
            if a678_post_gate_diagnostic
            else "a2_verified_progress_memory_v1r1"
            if args.a2_verified_progress_memory
            else (
                {
                    "a3": "a3_memgui_conact_folded_context_v1",
                    "a4": "a4_awm_frozen_donor_workflow_memory_v1",
                    "a5": "a5_hymem_online_visual_symbolic_graph_v1",
                }[args.a345_arm]
                if a345_scored_arm
                else (
                    A678_MECHANISMS[args.a678_arm]
                    if a678_scored_arm
                    else ("a1_action_working_memory_v1" if args.a1_working_memory else "a0")
                )
            )
        ),
        "manifest_sha256": _sha256(args.manifest) if args.manifest else None,
        "ordered_expected_keys": expected_keys,
        "ordered_expected_keys_sha256": expected_keys_sha256,
        "generation_seed": args.generation_seed,
        "max_tokens": args.max_tokens,
        "observation_backend": args.observation_backend,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "backend_id": BACKEND_ID,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.5,
        "repetition_penalty": 1.0,
        "request_timeout_seconds": args.request_timeout_seconds,
        "url": args.url,
        "console_port": args.console_port,
        "grpc_port": args.grpc_port,
        "adb_path": str(Path(args.adb_path).resolve()),
    }
    if a345_scored_arm:
        run_signature.update(
            {
                "qualification_gate_tasks": list(A345_GATE_TASKS),
                "qualification_gate_required_successes": 5,
                "qualification_gate_fail_fast": True,
                "schedule_note": "post-hoc capability-preservation gate, not new held-out evidence",
                "a345_preflight_sha256": _sha256(args.a345_preflight_report),
                "a345_launch_receipt_sha256": _sha256(args.a345_launch_receipt),
                "a4_workflow_bank_sha256": (
                    _sha256(args.a345_workflow_bank) if args.a345_arm == "a4" else None
                ),
            }
        )
    if a678_scored_arm:
        config_path = REPOSITORY_ROOT / (
            A7_CONTINUATION_CONFIG
            if a7_gated_continuation
            else A678_CONFIGS[str(args.a678_arm)]
        )
        run_signature.update(
            {
                "a678_arm": args.a678_arm,
                "a678_config_sha256": _sha256(config_path),
                "a678_preflight_sha256": _sha256(args.a678_preflight_report),
                "a678_launch_receipt_sha256": _sha256(args.a678_launch_receipt),
                "task_order": (
                    "retain_parent_7_then_missing_A0_gate_then_remaining_9"
                    if a7_gated_continuation
                    else (
                        "blocking_A0_4_task_gate_then_frozen_manifest_remainder"
                        if prospective_gate_arm
                        else "original_frozen_manifest_order_seed20260806"
                    )
                ),
                "reward_fail_fast": bool(
                    a7_gated_continuation or prospective_gate_arm
                ),
                "scientific_failure_rerun": False,
                "A0_preservation_tasks": list(A0_PRESERVATION_TASKS),
                "A0_preservation_required_for_continuation": bool(
                    a7_gated_continuation or prospective_gate_arm
                ),
                "controller_authored_memory": True,
                "response_prefix_required": False,
                "official_system_prompt_unchanged": True,
                "extra_model_calls": 0,
                "guard": False,
                "action_override": False,
            }
        )
        if a7_gated_continuation:
            run_signature.update(
                {
                    "protocol_amendment": (
                        "campaign_schedule_only_memory_mechanism_unchanged"
                    ),
                    "a7_continuation_plan_sha256": _sha256(
                        args.a7_continuation_plan
                    ),
                    "a7_parent_run_signature_sha256": a7_parent_snapshot[
                        "parent_run_signature_sha256"
                    ],
                    "a7_parent_checkpoint_sha256": a7_parent_snapshot[
                        "parent_checkpoint_sha256"
                    ],
                    "imported_parent_valid_episode_count": a7_parent_snapshot[
                        "parent_valid_episode_count"
                    ],
                    "execution_schedule": a7_continuation_plan[
                        "execution_schedule"
                    ],
                    "capability_gate_fail_fast": True,
                    "claim_boundary": a7_continuation_plan["claim_boundary"],
                }
            )
    if a7_post_gate_diagnostic:
        run_signature.update(
            {
                "a678_arm": "a7",
                "a678_config_sha256": _sha256(
                    REPOSITORY_ROOT / A678_CONFIGS["a7"]
                ),
                "a678_preflight_sha256": _sha256(args.a678_preflight_report),
                "a678_launch_receipt_sha256": _sha256(args.a678_launch_receipt),
                "task_order": (
                    "single_post_terminal_gate_diagnostic"
                    if a7_sports_diagnostic
                    else "remaining_9_after_terminal_gate_diagnostic"
                ),
                "claim_boundary": "diagnostic_only_not_gate_repair_not_scored_continuation",
                "controller_authored_memory": True,
                "response_prefix_required": False,
                "official_system_prompt_unchanged": True,
                "extra_model_calls": 0,
                "guard": False,
                "action_override": False,
            }
        )
    if a89_four_task_diagnostic:
        run_signature.update(
            {
                "a678_arm": args.a678_arm,
                "a678_config_sha256": _sha256(
                    REPOSITORY_ROOT / A678_CONFIGS[str(args.a678_arm)]
                ),
                "a678_preflight_sha256": _sha256(args.a678_preflight_report),
                "a678_launch_receipt_sha256": _sha256(args.a678_launch_receipt),
                "task_order": "A0_four_task_gate_order_seed20260806",
                "reward_fail_fast": False,
                "scientific_failure_rerun": True,
                "replication_index": 1,
                "A0_preservation_tasks": list(A0_PRESERVATION_TASKS),
                "A0_preservation_required_for_continuation": False,
                "remaining_15_released": False,
                "claim_boundary": A89_DIAGNOSTIC_CLAIM_BOUNDARY,
                "original_terminal_gate_suites_preserved": True,
                "controller_authored_memory": True,
                "response_prefix_required": False,
                "official_system_prompt_unchanged": True,
                "extra_model_calls": 0,
                "guard": False,
                "action_override": False,
            }
        )
    if args.a2_verified_progress_memory:
        source_freeze = current_a2_source_freeze()
        run_signature.update(
            {
                "repository_head": subprocess.check_output(
                    ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
                ).strip(),
                "preflight_sha256": _sha256(args.a2_preflight_report),
                "source_freeze_sha256": _json_digest(source_freeze),
                "a0_a1_reference_ledger_sha256": _sha256(args.a2_reference_ledger),
                "a1_exact_guard_replay_sha256": _sha256(A2_GUARD_REPLAY),
                "runtime_qualification_sha256": _sha256(args.a2_runtime_qualification),
                "live_server_stable_identity": {
                    "model_realpath": a2_launch["model_realpath"],
                    "model_manifest_sha256": a2_launch["model_manifest_sha256"],
                    "served_model_id": a2_launch["served_model_id"],
                    "packages": a2_launch["packages"],
                    "host": a2_launch["host"],
                    "port": a2_launch["port"],
                },
                "model_manifest_sha256": (a2_runtime["remote_model"]["model_manifest_sha256"]),
                "androidworld_identity": {
                    "commit": a2_runtime["local_android"]["androidworld_commit"],
                    "source_tree_sha256": a2_runtime["local_android"]["androidworld_source_tree_sha256"],
                    "emulator_serial": a2_runtime["local_android"]["emulator_serial"],
                    "resolution": a2_runtime["local_android"]["resolution"],
                },
                "transport_policy": "single_http_attempt_no_automatic_retry",
            }
        )
    run_signature_sha256 = _json_digest(run_signature)
    invalid_attempts: list[dict] = []
    valid_entries: list[dict] = []
    orphan_episode_directories: list[str] = []
    if args.resume_suite_dir is not None:
        suite_dir = args.resume_suite_dir.resolve()
        if not suite_dir.is_dir():
            raise RuntimeError(f"resume suite does not exist: {suite_dir}")
        frozen_signature = json.loads(
            (suite_dir / "run_signature.json").read_text(encoding="utf-8")
        )
        # JSON serialisation turns tuple-valued expected keys into lists.  Compare
        # their canonical JSON digests so a byte-equivalent frozen signature can
        # resume without being rejected solely for that in-memory type change.
        if _json_digest(frozen_signature) != run_signature_sha256:
            raise RuntimeError("resume run signature differs from the frozen scored-memory suite")
        if args.a2_verified_progress_memory:
            summaries, valid_entries, invalid_attempts, orphan_episode_directories = load_a2_checkpoint(
                suite_dir=suite_dir,
                expected_keys=expected_keys,
                run_signature_sha256=run_signature_sha256,
            )
        else:
            checkpoint = json.loads(
                (suite_dir / "checkpoint.json").read_text(encoding="utf-8")
            )
            if a345_scored_arm and checkpoint.get("status") in A345_TERMINAL_CHECKPOINT_STATUSES:
                raise RuntimeError("A3/A4/A5 scientific or activation gate failure is terminal and cannot be resumed")
            if (
                a7_gated_continuation
                and checkpoint.get("status") == "stopped_capability_gate_failure"
            ):
                raise RuntimeError(
                    "A7 capability-preservation failure is terminal and cannot be resumed"
                )
            if (
                prospective_gate_arm
                and checkpoint.get("status") == "stopped_capability_gate_failure"
            ):
                raise RuntimeError(
                    f"{str(args.a678_arm).upper()} capability-preservation failure is terminal and cannot be resumed"
                )
            summaries = list(checkpoint.get("valid_summaries") or [])
            invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
        suite_id = suite_dir.name
    else:
        suite_id = f"official_qwen_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
        suite_dir = args.output_root / suite_id
        suite_dir.mkdir(parents=True, exist_ok=False)
        summaries: list[dict] = (
            list(a7_parent_snapshot["summaries"])
            if a7_gated_continuation
            else []
        )
        if a7_gated_continuation:
            invalid_attempts = list(a7_parent_snapshot["invalid_attempts"])
        _atomic_json(suite_dir / "run_signature.json", run_signature)
        if a7_gated_continuation:
            _atomic_json(
                suite_dir / "imported_parent_evidence.json",
                {
                    key: value
                    for key, value in a7_parent_snapshot.items()
                    if key not in {"summaries", "invalid_attempts"}
                },
            )
            shutil.copy2(
                args.a7_continuation_plan,
                suite_dir / "A7_GATED_CONTINUATION_PLAN.snapshot.json",
            )
        if args.manifest:
            shutil.copy2(args.manifest, suite_dir / "manifest.snapshot.json")

    def checkpoint(status: str) -> None:
        if args.a2_verified_progress_memory:
            payload = {
                "suite_id": suite_id,
                "status": status,
                "updated_at": datetime.now().isoformat(),
                "run_signature_sha256": run_signature_sha256,
                "valid_entries": valid_entries,
                "invalid_attempts": invalid_attempts,
                "orphan_episode_directories": orphan_episode_directories,
            }
        else:
            payload = {
                "suite_id": suite_id,
                "status": status,
                "updated_at": datetime.now().isoformat(),
                "valid_summaries": summaries,
                "invalid_attempts": invalid_attempts,
            }
            if a7_gated_continuation:
                payload.update(
                    {
                        "protocol_amendment": (
                            "campaign_schedule_only_memory_mechanism_unchanged"
                        ),
                        "imported_parent_valid_episode_count": a7_parent_snapshot[
                            "parent_valid_episode_count"
                        ],
                        "capability_gate": a7_gate_report(summaries),
                    }
                )
            elif prospective_gate_arm:
                payload["capability_gate"] = a7_gate_report(summaries)
            elif a89_four_task_diagnostic:
                payload.update(
                    {
                        "claim_boundary": A89_DIAGNOSTIC_CLAIM_BOUNDARY,
                        "four_task_diagnostic": a89_diagnostic_report(summaries),
                    }
                )
        _atomic_json(
            suite_dir / "checkpoint.json",
            payload,
        )

    checkpoint("running")
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
        retry_transient_errors=not (
            args.a2_verified_progress_memory or a345_scored_arm or a678_memory_arm
        ),
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
    completed_keys = {
        (str(item["task_name"]), int(item["seed"])) for item in summaries
    }
    suite_lifecycle_errors: list[dict] = []
    active_exception: BaseException | None = None
    try:
        for spec in specs:
            task_name = str(spec["task_class"])
            episode_seed = int(spec["task_seed"])
            if (task_name, episode_seed) in completed_keys:
                continue
            if (
                (a7_gated_continuation or prospective_gate_arm)
                and task_name not in A0_PRESERVATION_TASKS
            ):
                gate = a7_gate_report(summaries)
                if gate["status"] != "passed":
                    checkpoint("stopped_capability_gate_incomplete")
                    raise RuntimeError(
                        f"{str(args.a678_arm).upper()} remaining tasks are locked until the A0 preservation gate is 4/4"
                    )
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
            a678_memory = None
            if args.a678_arm == "a6":
                a678_memory = ShortTransitionEpisodicBuffer(capacity=2, max_chars=240)
            elif args.a678_arm == "a7":
                a678_memory = GoalItemStatusLedger(
                    max_items=6, max_item_chars=48, max_chars=320
                )
            elif args.a678_arm == "a8":
                a678_memory = ExactVisualRevisitActionOutcomeCache(
                    max_entries=12, max_matches=2, max_chars=260
                )
            elif args.a678_arm == "a8v2":
                a678_memory = FailureAwareExactRevisitMemory(
                    max_states=12,
                    max_actions_per_state=4,
                    max_transitions=24,
                    max_rendered_actions=3,
                    max_chars=360,
                )
            elif args.a678_arm == "a9":
                a678_memory = SparseRecurrenceCanaryMemory(
                    max_chars=280,
                    query_window_steps=12,
                    max_query_keys=8,
                    max_occurrences_per_query=4,
                    max_trace_screens=13,
                    max_cycle_period=3,
                    pending_capacity=2,
                    event_log_capacity=16,
                )
            controller = OfficialQwenMobileController(
                client,
                max_steps=effective_limit,
                max_tokens=args.max_tokens,
                run_metadata={
                    "run_stage": args.run_stage,
                    "diagnostic": bool(args.diagnostic),
                    "held_out_eligible": held_out_eligible,
                    "held_out_ineligible_reason": held_out_ineligible_reason,
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
                    "run_signature_sha256": run_signature_sha256,
                    "live_server_receipt_sha256": (
                        _sha256(args.a2_launch_receipt)
                        if args.a2_verified_progress_memory
                        else (
                            _sha256(args.a678_launch_receipt)
                            if a678_memory_arm else None
                        )
                    ),
                    "stop_after_markor_source_exit": bool(
                        args.stop_after_markor_source_exit
                    ),
                    "memory_intervention": (
                        "a2_verified_progress_memory_v1r1"
                        if args.a2_verified_progress_memory
                        else (
                            run_signature["method"]
                            if (a345_scored_arm or a678_memory_arm)
                            else ("a1_action_working_memory_v1" if args.a1_working_memory else None)
                        )
                    ),
                    "cost_guard": (
                        "a2_repeated_no_progress_cost_guard_v1r1"
                        if args.a2_verified_progress_memory
                        else None
                    ),
                },
                system_prompt=(
                    A2_VERIFIED_PROGRESS_SYSTEM_PROMPT
                    if args.a2_verified_progress_memory
                    else (
                    A3_CONACT_SYSTEM_PROMPT if args.a345_arm == "a3" else (
                    A4_WORKFLOW_SYSTEM_PROMPT if args.a345_arm == "a4" else (
                    A5_VISUAL_GRAPH_SYSTEM_PROMPT if args.a345_arm == "a5" else (
                    A1_WORKING_MEMORY_SYSTEM_PROMPT
                    if args.a1_working_memory
                    else (
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
                    )))))
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
                working_memory=(
                    a678_memory
                    if a678_memory_arm
                    else (
                    VerifiedProgressMemory(max_chars=1200)
                    if args.a2_verified_progress_memory
                    else (
                        ProactiveFoldedContextMemory(max_chars=1800)
                        if args.a345_arm == "a3"
                        else (
                            FrozenWorkflowMemory(
                                bank=_load_a4_workflows(args.a345_workflow_bank),
                                max_chars=1800,
                            )
                            if args.a345_arm == "a4"
                            else (
                                OnlinePageGraphMemory(
                                    max_edges=12, max_chars=1800, max_hamming=6
                                )
                                if args.a345_arm == "a5"
                                else (
                        ActionWorkingMemory(max_items=6, max_chars=3000)
                        if args.a1_working_memory
                        else None
                                )
                            )
                        )
                    )
                    )
                ),
                cost_guard=(
                    RepeatedNoProgressGuard(
                        no_progress_threshold=2,
                        max_ignored_block_warnings=2,
                    )
                    if args.a2_verified_progress_memory
                    else None
                ),
            )
            episode_id = f"{task_name}_{episode_seed}_{uuid4().hex[:8]}"
            result = controller.run(
                env=env,
                task=task,
                episode_id=episode_id,
                episode_dir=suite_dir / "episodes" / episode_id,
                seed=episode_seed,
            )
            if not _episode_infrastructure_valid(result):
                invalid_attempts.append(
                    {
                        "episode_id": episode_id,
                        "task_name": task_name,
                        "seed": episode_seed,
                        "reason": "controller_or_lifecycle_invalid",
                        "error": result.get("error"),
                        "lifecycle_errors": result.get("lifecycle_errors"),
                    }
                )
                checkpoint("stopped_invalid_episode")
                raise RuntimeError(
                    f"Scored memory arm stopped after infrastructure-invalid episode {episode_id}; "
                    "resume will rerun only this task"
                )
            for attempt in invalid_attempts:
                if (
                    str(attempt.get("task_name")) == task_name
                    and int(attempt.get("seed", -1)) == episode_seed
                    and not attempt.get("resolved_by_episode_id")
                ):
                    attempt["resolved_by_episode_id"] = episode_id
            summaries.append(result)
            if args.a2_verified_progress_memory:
                valid_entries.append(
                    a2_episode_reference(
                        suite_dir=suite_dir,
                        episode_dir=suite_dir / "episodes" / episode_id,
                        summary=result,
                        run_signature_sha256=run_signature_sha256,
                    )
                )
            completed_keys.add((task_name, episode_seed))
            if a345_scored_arm and len(summaries) == 1 and not _a345_activation_valid(
                result, str(args.a345_arm)
            ):
                checkpoint("stopped_memory_activation_failure")
                raise RuntimeError(
                    f"{args.a345_arm.upper()} first task did not prove memory exposure; "
                    "the suite is invalid and must not continue"
                )
            if a345_scored_arm and task_name in A345_REQUIRED_GATE_TASKS and not bool(
                result.get("success")
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"{args.a345_arm.upper()} capability-preservation gate failed on "
                    f"{task_name}; scientific failures are terminal and cannot be rerun"
                )
            if (
                (a7_gated_continuation or prospective_gate_arm)
                and task_name in A0_PRESERVATION_TASKS
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"{str(args.a678_arm).upper()} capability-preservation gate failed on "
                    f"{task_name}; scientific failures are terminal and cannot be rerun"
                )
            checkpoint("running")
    except BaseException as exc:
        active_exception = exc
        raise
    finally:
        try:
            env.close()
        except Exception as exc:
            lifecycle_error = {
                "stage": "env.close", "type": type(exc).__name__, "message": str(exc)
            }
            suite_lifecycle_errors.append(lifecycle_error)
            invalid_attempts.append(
                {"reason": "suite_lifecycle_error", "error": lifecycle_error}
            )
            checkpoint("stopped_invalid_episode")
            if active_exception is None:
                raise
        else:
            for attempt in invalid_attempts:
                if (
                    attempt.get("reason") == "suite_lifecycle_error"
                    and not attempt.get("resolved_by_episode_id")
                ):
                    attempt["resolved_by_episode_id"] = "suite_close_success_on_resume"

    if args.a2_verified_progress_memory:
        completed_ordered_keys = [
            (str(item["task_name"]), int(item["seed"])) for item in summaries
        ]
        if (
            completed_ordered_keys != expected_keys
            or len(valid_entries) != 19
            or any(not item.get("resolved_by_episode_id") for item in invalid_attempts)
            or suite_lifecycle_errors
            or any(not _episode_infrastructure_valid(item) for item in summaries)
            or any(item.get("evaluator_reward") is None for item in summaries)
            or any(
                int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1
                for item in summaries for step in item.get("steps", [])
            )
        ):
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError("A2 cannot aggregate: exact 19-task validity closure failed")
    if a345_scored_arm:
        completed_ordered_keys = [
            (str(item["task_name"]), int(item["seed"])) for item in summaries
        ]
        if (
            completed_ordered_keys != expected_keys
            or len(summaries) != 19
            or any(not item.get("resolved_by_episode_id") for item in invalid_attempts)
            or suite_lifecycle_errors
            or any(not _episode_infrastructure_valid(item) for item in summaries)
            or any(item.get("evaluator_reward") is None for item in summaries)
            or any(
                int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1
                for item in summaries for step in item.get("steps", [])
            )
        ):
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(
                f"{args.a345_arm.upper()} cannot aggregate: exact 19-task validity closure failed"
            )
    if a678_scored_arm:
        if a7_gated_continuation:
            summaries = canonicalize_a7_summaries(summaries, expected_keys)
            gate = a7_gate_report(summaries)
            if gate["status"] != "passed":
                checkpoint("stopped_capability_gate_incomplete")
                raise RuntimeError(
                    "A7 cannot aggregate before the blocking 4/4 preservation gate passes"
                )
        closure_errors = a678_completion_errors(
            summaries=summaries,
            expected_keys=expected_keys,
            invalid_attempts=invalid_attempts,
            lifecycle_errors=suite_lifecycle_errors,
        )
        if closure_errors:
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(
                f"{args.a678_arm.upper()} cannot aggregate: {closure_errors}"
            )
    if a89_four_task_diagnostic:
        closure_errors = a89_diagnostic_completion_errors(
            summaries=summaries,
            expected_keys=expected_keys,
            invalid_attempts=invalid_attempts,
            lifecycle_errors=suite_lifecycle_errors,
        )
        if closure_errors:
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(
                f"{str(args.a678_arm).upper()} four-task diagnostic cannot "
                f"aggregate: {closure_errors}"
            )

    aggregate = {
        "suite_id": suite_id,
        "model_health": health,
        "run_stage": args.run_stage,
        "diagnostic": bool(args.diagnostic),
        "held_out_eligible": held_out_eligible,
        "held_out_ineligible_reason": held_out_ineligible_reason,
        "hidden_observation_backend": args.observation_backend,
        "model_visible_observation": "current_screenshot_only",
        "transient_observation_carry": bool(args.transient_observation_carry),
        "transition_attested_history": bool(args.transition_attested_history),
        "evidence_qualified_progress": bool(args.evidence_qualified_progress),
        "request_timeout_seconds": args.request_timeout_seconds,
        "memory_intervention": (
            "a2_verified_progress_memory_v1r1"
            if args.a2_verified_progress_memory
            else (
                run_signature["method"]
                if (a345_scored_arm or a678_memory_arm)
                else ("a1_action_working_memory_v1" if args.a1_working_memory else None)
            )
        ),
        "cost_guard": (
            "a2_repeated_no_progress_cost_guard_v1r1"
            if args.a2_verified_progress_memory
            else None
        ),
        "memory_active_episode_count": sum(
            int(bool((item.get("memory_mechanism") or {}).get("active")))
            for item in summaries
        ),
        "A0_preservation_monitor": (
            a89_diagnostic_report(summaries)
            if a89_four_task_diagnostic
            else
            (
                a7_gate_report(summaries)
                if (a7_gated_continuation or prospective_gate_arm)
                else a678_preservation_report(summaries)
            )
            if a678_scored_arm
            else None
        ),
        "token_usage": _usage_totals(summaries),
        "memory_write_success_count": sum(
            int((item.get("memory_mechanism") or {}).get("write_success_count") or 0)
            for item in summaries
        ),
        "memory_nonempty_read_count": sum(
            int((item.get("memory_mechanism") or {}).get("nonempty_read_count") or 0)
            for item in summaries
        ),
        "cost_guard_trigger_count": sum(
            int((item.get("cost_guard") or {}).get("trigger_count") or 0)
            for item in summaries
        ),
        "cost_guard_block_count": sum(
            int((item.get("cost_guard") or {}).get("block_count") or 0)
            for item in summaries
        ),
        "cost_guard_stop_count": sum(
            int((item.get("cost_guard") or {}).get("cost_stop_count") or 0)
            for item in summaries
        ),
        "run_signature_sha256": run_signature_sha256,
        "live_server_receipt_sha256s": sorted(
            {
                str((item.get("run_metadata") or {}).get("live_server_receipt_sha256"))
                for item in summaries
                if (item.get("run_metadata") or {}).get("live_server_receipt_sha256")
            }
        ),
        "ordered_expected_keys_sha256": expected_keys_sha256,
        "valid_episode_count": len(summaries),
        "invalid_episode_count": len(invalid_attempts),
        "orphan_episode_directories": orphan_episode_directories,
        "total_model_calls": sum(int(item.get("model_call_count") or 0) for item in summaries),
        "total_executed_actions": sum(int(item.get("executed_action_count") or 0) for item in summaries),
        "progress_prefix_attempt_count": sum(
            int((item.get("memory_mechanism") or {}).get("progress_prefix_attempt_count") or 0)
            for item in summaries
        ),
        "progress_prefix_valid_count": sum(
            int((item.get("memory_mechanism") or {}).get("progress_prefix_valid_count") or 0)
            for item in summaries
        ),
        "cost_guard_warning_count": sum(
            int((item.get("cost_guard") or {}).get("warning_count") or 0)
            for item in summaries
        ),
        "cost_guard_affected_task_ids": [
            str(item["task_name"]) for item in summaries
            if int((item.get("cost_guard") or {}).get("block_count") or 0) > 0
        ],
        "exact_valid_elapsed_seconds": sum(
            (datetime.fromisoformat(item["finished_at"]) - datetime.fromisoformat(item["started_at"])).total_seconds()
            for item in summaries
        ),
        "transport_attempt_total": sum(
            int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)
            for item in summaries for step in item.get("steps", [])
        ),
        "transport_attempt_max": max(
            [int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)
             for item in summaries for step in item.get("steps", [])] or [0]
        ),
        "per_task": [
            {
                "task_name": item["task_name"],
                "seed": item["seed"],
                "episode_id": item["episode_id"],
                "success": item["success"],
                "reward": item["evaluator_reward"],
                "model_calls": item["model_call_count"],
                "executed_actions": item["executed_action_count"],
                "token_usage": _usage_totals([item]),
                "elapsed_seconds": (
                    datetime.fromisoformat(item["finished_at"]) - datetime.fromisoformat(item["started_at"])
                ).total_seconds(),
                "progress_prefix_attempt_count": int((item.get("memory_mechanism") or {}).get("progress_prefix_attempt_count") or 0),
                "progress_prefix_valid_count": int((item.get("memory_mechanism") or {}).get("progress_prefix_valid_count") or 0),
                "memory_write_success_count": int(
                    (item.get("memory_mechanism") or {}).get("memory_write_success_count")
                    or (item.get("memory_mechanism") or {}).get("write_success_count")
                    or 0
                ),
                "guard_blocks": int((item.get("cost_guard") or {}).get("block_count") or 0),
                "guard_warnings": int((item.get("cost_guard") or {}).get("warning_count") or 0),
                "guard_cost_stops": int((item.get("cost_guard") or {}).get("cost_stop_count") or 0),
            }
            for item in summaries
        ],
        "invalid_attempts": invalid_attempts,
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
    _atomic_json(suite_dir / "aggregate.json", aggregate)
    checkpoint("complete")
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
