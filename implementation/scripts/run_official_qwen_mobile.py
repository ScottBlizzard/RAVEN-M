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


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_official_public_v1"
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
        )
    )
    if diagnostic_modes > 1:
        parser.error(
            "--transient-observation-carry, --transition-attested-history, "
            "--evidence-qualified-progress, and --source-document-coverage "
            "--source-document-coverage-gate, --a1-working-memory, and "
            "--a2-verified-progress-memory and --a345-arm are mutually exclusive"
        )
    held_out_eligible = not bool(args.diagnostic) and not bool(
        args.held_out_ineligible_reason
    )
    a345_scored_arm = bool(args.a345_arm)
    scored_memory_arm = bool(
        args.a1_working_memory or args.a2_verified_progress_memory or a345_scored_arm
    )
    if args.resume_suite_dir is not None and not scored_memory_arm:
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
        if a345_scored_arm:
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
    unknown = sorted(
        {str(item["task_class"]) for item in specs} - set(available)
    )
    if unknown:
        raise KeyError(f"Unknown AndroidWorld tasks: {unknown}")

    expected_keys = [(str(item["task_class"]), int(item["task_seed"])) for item in specs]
    expected_keys_sha256 = _json_digest(expected_keys)
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
            "A2_VERIFIED_PROGRESS_MEMORY_QWEN3VL32B_AW_HARD_S20260806_V1R1"
            if args.a2_verified_progress_memory
            else (
                f"{args.a345_arm.upper()}_PUBLIC_MEMORY_KERNEL_QWEN3VL32B_AW_HARD_S20260806_V1"
                if a345_scored_arm else None
            )
        ),
        "method": (
            "a2_verified_progress_memory_v1r1"
            if args.a2_verified_progress_memory
            else (
                {
                    "a3": "a3_memgui_conact_folded_context_v1",
                    "a4": "a4_awm_frozen_donor_workflow_memory_v1",
                    "a5": "a5_hymem_online_visual_symbolic_graph_v1",
                }[args.a345_arm]
                if a345_scored_arm
                else ("a1_action_working_memory_v1" if args.a1_working_memory else "a0")
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
        if frozen_signature != run_signature:
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
            summaries = list(checkpoint.get("valid_summaries") or [])
            invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
        suite_id = suite_dir.name
    else:
        suite_id = f"official_qwen_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
        suite_dir = args.output_root / suite_id
        suite_dir.mkdir(parents=True, exist_ok=False)
        summaries: list[dict] = []
        _atomic_json(suite_dir / "run_signature.json", run_signature)
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
        retry_transient_errors=not (args.a2_verified_progress_memory or a345_scored_arm),
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
                    "run_signature_sha256": run_signature_sha256,
                    "live_server_receipt_sha256": (
                        _sha256(args.a2_launch_receipt)
                        if args.a2_verified_progress_memory else None
                    ),
                    "stop_after_markor_source_exit": bool(
                        args.stop_after_markor_source_exit
                    ),
                    "memory_intervention": (
                        "a2_verified_progress_memory_v1r1"
                        if args.a2_verified_progress_memory
                        else (
                            run_signature["method"]
                            if a345_scored_arm
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
        "memory_intervention": (
            "a2_verified_progress_memory_v1r1"
            if args.a2_verified_progress_memory
            else (
                run_signature["method"]
                if a345_scored_arm
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
