"""Run the faithful Qwen3-VL Mobile Agent baseline on AndroidWorld."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
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
    A1R1_BPR_V2_SYSTEM_PROMPT,
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
from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (  # noqa: E402
    EvidenceCalibratedObligationBranchFrontierMemory,
)
from raven_m.official_qwen_mobile.a10_contract import (  # noqa: E402
    CONFIG_PATH as A10_CONFIG_PATH,
    EXPERIMENT_ID as A10_EXPERIMENT_ID,
    MECHANISM_ID as A10_MECHANISM_ID,
    MODEL_REALPATH as A10_MODEL_REALPATH,
    PARENT_EVIDENCE_COMMIT as A10_PARENT_EVIDENCE_COMMIT,
    TASK_SEED as A10_TASK_SEED,
    current_source_freeze as current_a10_source_freeze,
    json_sha256 as a10_json_sha256,
    exact_completion_errors as a10_completion_errors,
    preservation_report as a10_preservation_report,
    validate_launch_receipt as validate_a10_launch_receipt,
    validate_preflight_report as validate_a10_preflight_report,
)
from raven_m.official_qwen_mobile.a89_diagnostic import (  # noqa: E402
    CLAIM_BOUNDARY as A89_DIAGNOSTIC_CLAIM_BOUNDARY,
    EXPERIMENT_IDS as A89_DIAGNOSTIC_EXPERIMENT_IDS,
    completion_errors as a89_diagnostic_completion_errors,
    report as a89_diagnostic_report,
    select_four_task_specs as select_a89_diagnostic_specs,
)
from raven_m.official_qwen_mobile import enriched_diagnostic_contract as diag6_contract  # noqa: E402


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


# New prospective arms are loaded only after CLI selection.  This keeps the
# historical A10-v1 runner importable while A10-v2/A11/A12 maintain independent
# mechanism and contract modules, and makes it impossible to compose multiple
# memories in one controller.
DUAL_ARM_SPECS = {
    "a1r13": {
        "flag": "a1r13_evr",
        "label": "A1-R13 EVR",
        "memory_module": "raven_m.official_qwen_mobile.a1r13_evidence_value_register",
        "memory_class": "EvidenceValueRegisterMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r13_contract",
        "entry_key": "a1r13_valid_entries",
        "checkpoint_schema": "a1r13_evr_checkpoint_v1",
        "result_key": "a1r13_result",
        "result_schema": "a1r13_evr_result_v1",
        "reference_segments_path": REPOSITORY_ROOT
        / "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json",
        "system_prompt_identity": "a1_working_memory",
    },
    "a1r13d": {
        "flag": "a1r13d_evr",
        "label": "A1-R13D EVR target-first",
        "memory_module": "raven_m.official_qwen_mobile.a1r13_evidence_value_register",
        "memory_class": "EvidenceValueRegisterMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r13d_contract",
        "entry_key": "a1r13d_valid_entries",
        "checkpoint_schema": "a1r13d_evr_target_first_checkpoint_v1",
        "result_key": "a1r13d_result",
        "result_schema": "a1r13d_evr_target_first_result_v1",
        "reference_segments_path": REPOSITORY_ROOT
        / "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json",
        "system_prompt_identity": "a1_working_memory",
    },
    "a1r14": {
        "flag": "a1r14_rgvr",
        "label": "A1-R14 response-grounded value register",
        "memory_module": "raven_m.official_qwen_mobile.a1r14_response_value_register",
        "memory_class": "ResponseGroundedValueRegisterMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r14_contract",
        "entry_key": "a1r14_valid_entries",
        "checkpoint_schema": "a1r14_rgvr_checkpoint_v1",
        "result_key": "a1r14_result",
        "result_schema": "a1r14_rgvr_result_v1",
        "reference_segments_path": REPOSITORY_ROOT
        / "evidence/a1r14/A1R14_RGVR_REPLAY_FIXTURE.json",
        "system_prompt_identity": "a1_working_memory",
    },
    "a1r15": {
        "flag": "a1r15_eovr",
        "label": "A1-R15 explicit-observation value register",
        "memory_module": "raven_m.official_qwen_mobile.a1r15_explicit_observation_value_register",
        "memory_class": "ExplicitObservationValueRegisterMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r15_contract",
        "entry_key": "a1r15_valid_entries",
        "checkpoint_schema": "a1r15_eovr_checkpoint_v1",
        "result_key": "a1r15_result",
        "result_schema": "a1r15_eovr_result_v1",
        "reference_segments_path": REPOSITORY_ROOT
        / "evidence/a1r15/A1R15_EOVR_REPLAY_FIXTURE.json",
        "system_prompt_identity": "a1_working_memory",
    },
    "sys_nag": {
        "flag": "sys_nag",
        "label": "SYS-NAG V4 R2 Route-Recurrence Composite",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.sys_nag_contract",
        "entry_key": "sys_nag_valid_entries",
        "checkpoint_schema": "sys_nag_v4_checkpoint_v1",
        "result_key": "sys_nag_v4_result",
        "result_schema": "sys_nag_v4_result_v1",
        "system_prompt_identity": "a1_working_memory",
    },
    "sys_trrc_base": {
        "flag": "sys_trrc_mode", "label": "SYS-TRRC-V2-R2-BASE", "recovery_mode": "base",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.sys_trrc_contract",
        "entry_key": "sys_trrc_valid_entries", "checkpoint_schema": "sys_trrc_v2_checkpoint_v1",
        "result_key": "sys_trrc_result", "result_schema": "sys_trrc_v2_result_v1",
    },
    "sys_trrc_detector": {
        "flag": "sys_trrc_mode", "label": "SYS-TRRC-V2-R2-DETECTOR", "recovery_mode": "detector",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.sys_trrc_contract",
        "entry_key": "sys_trrc_valid_entries", "checkpoint_schema": "sys_trrc_v2_checkpoint_v1",
        "result_key": "sys_trrc_result", "result_schema": "sys_trrc_v2_result_v1",
    },
    "sys_trrc_generic": {
        "flag": "sys_trrc_mode", "label": "SYS-TRRC-V2-R2-GENERIC", "recovery_mode": "generic",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.sys_trrc_contract",
        "entry_key": "sys_trrc_valid_entries", "checkpoint_schema": "sys_trrc_v2_checkpoint_v1",
        "result_key": "sys_trrc_result", "result_schema": "sys_trrc_v2_result_v1",
    },
    "sys_trrc_full": {
        "flag": "sys_trrc_mode", "label": "SYS-TRRC-V2-R2-FULL", "recovery_mode": "full",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.sys_trrc_contract",
        "entry_key": "sys_trrc_valid_entries", "checkpoint_schema": "sys_trrc_v2_checkpoint_v1",
        "result_key": "sys_trrc_result", "result_schema": "sys_trrc_v2_result_v1",
    },
    "a1r3v3": {
        "flag": "a1r3v3_oscnr",
        "label": "A1-R3-v3 OSCNR",
        "memory_module": "raven_m.official_qwen_mobile.a1r3v3_one_shot_cnr",
        "memory_class": "OneShotControllerNonprogressReceiptMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r3v3_contract",
        "entry_key": "a1r3v3_valid_entries",
        "checkpoint_schema": "a1r3v3_oscnr_checkpoint_v1",
        "result_key": "a1r3v3_result",
        "result_schema": "a1r3v3_oscnr_result_v1",
        "system_prompt_identity": "a1_working_memory",
    },
    "a1r12": {"flag":"a1r12_chp","label":"A1-R12 CHP","memory_module":"raven_m.official_qwen_mobile.a1r12_compacted_history_pending","memory_class":"CompactedHistoryPendingMemory","contract_module":"raven_m.official_qwen_mobile.a1r12_contract","entry_key":"a1r12_valid_entries","checkpoint_schema":"a1r12_chp_checkpoint_v1","result_key":"a1r12_result","result_schema":"a1r12_chp_result_v1"},
    "a1r11": {"flag":"a1r11_cscp","label":"A1-R11 CSCP","memory_module":"raven_m.official_qwen_mobile.a1r11_coordinate_self_check_pending","memory_class":"CoordinateSelfCheckPendingMemory","contract_module":"raven_m.official_qwen_mobile.a1r11_contract","entry_key":"a1r11_valid_entries","checkpoint_schema":"a1r11_cscp_checkpoint_v1","result_key":"a1r11_result","result_schema":"a1r11_cscp_result_v1"},
    "a1r10": {"flag":"a1r10_pacp","label":"A1-R10 PACP","memory_module":"raven_m.official_qwen_mobile.a1r10_pre_action_calibrated_pending","memory_class":"PreActionCalibratedPendingMemory","contract_module":"raven_m.official_qwen_mobile.a1r10_contract","entry_key":"a1r10_valid_entries","checkpoint_schema":"a1r10_pacp_checkpoint_v1","result_key":"a1r10_result","result_schema":"a1r10_pacp_result_v1"},
    "a1r9": {"flag":"a1r9_rlcr","label":"A1-R9 RLCR","memory_module":"raven_m.official_qwen_mobile.a1r9_run_length_cycle_recovery","memory_class":"RunLengthCycleRecoveryMemory","contract_module":"raven_m.official_qwen_mobile.a1r9_contract","entry_key":"a1r9_valid_entries","checkpoint_schema":"a1r9_rlcr_checkpoint_v1","result_key":"a1r9_result","result_schema":"a1r9_rlcr_result_v1"},
    "a1r8": {"flag":"a1r8_rcrp","label":"A1-R8 RCRP","memory_module":"raven_m.official_qwen_mobile.a1r8_route_cycle_recovery_pending","memory_class":"RouteCycleRecoveryPendingMemory","contract_module":"raven_m.official_qwen_mobile.a1r8_contract","entry_key":"a1r8_valid_entries","checkpoint_schema":"a1r8_rcrp_checkpoint_v1","result_key":"a1r8_result","result_schema":"a1r8_rcrp_result_v1"},
    "a1r7": {"flag":"a1r7_grpl","label":"A1-R7 GRPL","memory_module":"raven_m.official_qwen_mobile.a1r7_grounding_recovery_pending","memory_class":"GroundingRecoveryPendingMemory","contract_module":"raven_m.official_qwen_mobile.a1r7_contract","entry_key":"a1r7_valid_entries","checkpoint_schema":"a1r7_grpl_checkpoint_v1","result_key":"a1r7_result","result_schema":"a1r7_grpl_result_v1"},
    "a1r6": {
        "flag": "a1r6_gapl", "label": "A1-R6 GAPL",
        "memory_module": "raven_m.official_qwen_mobile.a1r6_goal_anchored_pending",
        "memory_class": "GoalAnchoredPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r6_contract",
        "entry_key": "a1r6_valid_entries", "checkpoint_schema": "a1r6_gapl_checkpoint_v1",
        "result_key": "a1r6_result", "result_schema": "a1r6_gapl_result_v1",
    },
    "a1r5": {
        "flag": "a1r5_tipl",
        "label": "A1-R5 TIPL",
        "memory_module": "raven_m.official_qwen_mobile.a1r5_transition_invalidated_pending",
        "memory_class": "TransitionInvalidatedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r5_contract",
        "entry_key": "a1r5_valid_entries",
        "checkpoint_schema": "a1r5_tipl_checkpoint_v1",
        "result_key": "a1r5_result",
        "result_schema": "a1r5_tipl_result_v1",
    },
    "a1r4": {
        "flag": "a1r4_wrpl",
        "label": "A1-R4 WRPL",
        "memory_module": "raven_m.official_qwen_mobile.a1r4_writer_resilient_pending",
        "memory_class": "WriterResilientPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r4_contract",
        "entry_key": "a1r4_valid_entries",
        "checkpoint_schema": "a1r4_wrpl_checkpoint_v1",
        "result_key": "a1r4_result",
        "result_schema": "a1r4_wrpl_result_v1",
    },
    "a1r3": {
        "flag": "a1r3_srpl",
        "label": "A1-R3 SRPL",
        "memory_module": "raven_m.official_qwen_mobile.a1r3_stale_resistant_pending",
        "memory_class": "StaleResistantPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r3_contract",
        "entry_key": "a1r3_valid_entries",
        "checkpoint_schema": "a1r3_srpl_checkpoint_v1",
        "result_key": "a1r3_result",
        "result_schema": "a1r3_srpl_result_v1",
    },
    "a1r2": {
        "flag": "a1r2_cvp",
        "label": "A1-R2 CVP",
        "memory_module": "raven_m.official_qwen_mobile.a1r2_compact_verified_pending",
        "memory_class": "CompactVerifiedPendingMemory",
        "contract_module": "raven_m.official_qwen_mobile.a1r2_contract",
        "entry_key": "a1r2_valid_entries",
        "checkpoint_schema": "a1r2_cvp_checkpoint_v1",
        "result_key": "a1r2_result",
        "result_schema": "a1r2_cvp_result_v1",
    },
    "bprv2": {
        "flag": "a1r1_bpr_v2_mode",
        "label": "A1-R1 BPR-v2",
        "memory_module": "raven_m.official_qwen_mobile.a1r1_bpr_v2",
        "memory_class": "BoundedPendingReceiptV2",
        "contract_module": "raven_m.official_qwen_mobile.a1r1_bpr_v2_contract",
        "entry_key": "a1r1_valid_entries",
        "checkpoint_schema": "a1r1_bpr_v2_primary_checkpoint_v1",
        "result_key": "a1r1_bpr_v2_result",
        "result_schema": "a1r1_bpr_v2_primary_result_v1",
    },
    "a10v2": {
        "flag": "a10_v2_emobf",
        "label": "A10-v2",
        "memory_module": "raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier",
        "memory_class": "EvidenceMaturedObligationBranchFrontierMemory",
        "contract_module": "raven_m.official_qwen_mobile.a10_v2_contract",
        "entry_key": "a10v2_valid_entries",
        "checkpoint_schema": "a10_v2_emobf_checkpoint_v1",
        "result_key": "a10v2_result",
        "result_schema": "a10_v2_emobf_result_v1",
    },
    "a11": {
        "flag": "a11_crc_ecobf",
        "label": "A11",
        "memory_module": "raven_m.official_qwen_mobile.a11_confirmed_route_contraction",
        "memory_class": "ConfirmedRouteContractionECOBFMemory",
        "contract_module": "raven_m.official_qwen_mobile.a11_contract",
        "entry_key": "a11_valid_entries",
        "checkpoint_schema": "a11_crc_ecobf_checkpoint_v1",
        "result_key": "a11_result",
        "result_schema": "a11_crc_ecobf_result_v1",
    },
    "a12": {
        "flag": "a12_madm",
        "label": "A12",
        "memory_module": "raven_m.official_qwen_mobile.a12_minimal_action_divergence",
        "memory_class": "MinimalActionDivergenceMemory",
        "contract_module": "raven_m.official_qwen_mobile.a12_contract",
        "entry_key": "a12_valid_entries",
        "checkpoint_schema": "a12_suite_checkpoint_v1",
        "result_key": "a12_result",
        "result_schema": "a12_madm_result_v1",
        "reference_segments_path": REPOSITORY_ROOT
        / "evidence/a12/A12_REFERENCE_SEGMENTS.json",
    },
}


def _contract_preservation_report(contract: object, summaries: list[dict]) -> dict:
    report = getattr(contract, "preservation_report", None)
    if report is not None:
        # Prospective mechanisms expose the immutable intervention boundary in
        # their memory audit.  Present a flat compatibility projection to arm
        # contracts without changing the stored episode evidence.
        projected: list[dict] = []
        for summary in summaries:
            audit = summary.get("memory_mechanism") or {}
            boundary = (
                audit.get("decision_boundary")
                or audit.get("causal_boundary")
                or {}
            )
            item = dict(summary)
            item.setdefault(
                "memory_added_model_calls",
                audit.get("model_calls_added", boundary.get("model_calls_added", 0)),
            )
            item.setdefault(
                "guard_enabled",
                audit.get("guard_enabled", boundary.get("guard_enabled", False)),
            )
            item.setdefault(
                "action_override_count",
                audit.get(
                    "action_override_count", boundary.get("action_override_count", 0)
                ),
            )
            item.setdefault(
                "forced_termination_count",
                audit.get(
                    "forced_termination_count",
                    boundary.get("forced_termination_count", 0),
                ),
            )
            projected.append(item)
        return report(projected)
    task_names = tuple(
        getattr(
            contract,
            "A0_PRESERVATION_TASKS",
            getattr(contract, "A0_GATE_TASKS", A0_PRESERVATION_TASKS),
        )
    )
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = [
        {
            "task_name": name,
            "reward": (observed.get(name) or {}).get("evaluator_reward"),
            "pass": (observed.get(name) or {}).get("evaluator_reward") == 1.0,
        }
        for name in task_names
    ]
    successes = sum(int(item["pass"]) for item in tasks)
    return {
        "status": "pass" if successes == len(task_names) else "fail",
        "success_count": successes,
        "required": len(task_names),
        "tasks": tasks,
    }


def _load_dual_arm(arm: str) -> dict:
    from importlib import import_module

    spec = dict(DUAL_ARM_SPECS[arm])
    memory_module = import_module(spec["memory_module"])
    contract = import_module(spec["contract_module"])
    sys_binding = contract.binding(spec["recovery_mode"]) if arm.startswith("sys_trrc_") else None
    spec.update(
        {
            "arm": arm,
            "memory_class_object": getattr(memory_module, spec["memory_class"]),
            "contract": contract,
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": sys_binding["experiment_id"] if sys_binding else contract.EXPERIMENT_ID,
            "config_path": sys_binding["config_path"] if sys_binding else contract.CONFIG_PATH,
            "parent_evidence_commit": getattr(
                contract,
                "PARENT_EVIDENCE_COMMIT",
                getattr(contract, "DESIGN_PARENT_COMMIT", None),
            ),
            "review_commit": getattr(
                contract,
                "REVIEW_COMMIT",
                getattr(contract, "DESIGN_REVIEW_COMMIT", None),
            ),
            "task_seed": contract.TASK_SEED,
            "gate_tasks": tuple(
                getattr(
                    contract,
                    "CAPABILITY_GATE_TASKS",
                    getattr(contract, "GATE5_TASKS", A0_PRESERVATION_TASKS),
                )
            ),
            "model_realpath": getattr(contract, "MODEL_REALPATH", A10_MODEL_REALPATH),
            "preservation_report": lambda summaries: _contract_preservation_report(
                contract, summaries
            ),
            "completion_errors": contract.exact_completion_errors,
            "validate_preflight": contract.validate_preflight_report,
            "validate_receipt": contract.validate_launch_receipt,
        }
    )
    if arm == "bprv2":
        spec["completion_errors"] = contract.exact_completion_errors
        spec["preservation_report"] = contract.preservation_report
    if sys_binding:
        spec["arm_id"] = sys_binding["arm_id"]
        spec["gate_tasks"] = tuple(contract.CAPABILITY_GATE_TASKS)
        spec["preservation_report"] = contract.preservation_report
    return spec


def _gate_passed(report: dict) -> bool:
    return str(report.get("status")) in {"pass", "passed"}


def _memory_protocol_violation(summary: dict) -> bool:
    audit = summary.get("memory_mechanism") or {}
    boundary = audit.get("decision_boundary") or audit.get("causal_boundary") or {}
    return bool(
        int(audit.get("model_calls_added", boundary.get("model_calls_added", 0)) or 0)
        or bool(audit.get("guard_enabled", boundary.get("guard_enabled", False)))
        or int(
            audit.get(
                "action_override_count", boundary.get("action_override_count", 0)
            )
            or 0
        )
        or int(
            audit.get(
                "forced_termination_count",
                boundary.get("forced_termination_count", 0),
            )
            or 0
        )
        or bool(boundary.get("hidden_ui_used_for_decision"))
        or bool(boundary.get("evaluator_used_for_decision"))
        or bool(boundary.get("future_information_used"))
    )


def _memory_active(summary: dict) -> bool:
    audit = summary.get("memory_mechanism") or {}
    counters = audit.get("counters") or {}
    return bool(
        audit.get("active")
        or int(audit.get("nonempty_read_count") or 0)
        or int(counters.get("nonempty_read_count") or 0)
        or any(bool(item.get("actual_nonempty")) for item in audit.get("read_events") or [])
    )


def _a12_memory_record_mismatch(summary: dict) -> bool:
    audit = summary.get("memory_mechanism") or {}
    steps = {
        int(item.get("step_index", item.get("step", -1))): item
        for item in summary.get("steps", [])
    }
    for event in audit.get("read_events") or []:
        if event.get("actual_nonempty") is not True:
            continue
        read_step = int(event.get("read_step", event.get("step", -1)))
        actual = str(
            ((steps.get(read_step) or {}).get("memory_read") or {}).get(
                "exact_injected_text"
            )
            or ""
        )
        expected = str(event.get("exact_injected_text") or "")
        if not actual or actual != expected:
            return True
    return False


def _diag6_completion_errors(
    summaries: list[dict],
    invalid_attempts: list[dict],
    lifecycle_errors: list[dict],
) -> list[str]:
    errors: list[str] = []
    observed = tuple((str(item.get("task_name")), int(item.get("seed", -1))) for item in summaries)
    expected = tuple((name, diag6_contract.TASK_SEED) for name in diag6_contract.TASKS)
    if observed != expected:
        errors.append("ordered_six_task_closure_failed")
    if lifecycle_errors:
        errors.append("suite_lifecycle_errors_present")
    if any(
        not _episode_infrastructure_valid(item, require_single_transport=True)
        for item in summaries
    ):
        errors.append("valid_episode_infrastructure_closure_failed")
    if any(_memory_protocol_violation(item) for item in summaries):
        errors.append("memory_intervention_boundary_violation")
    valid_by_id = {str(item.get("episode_id")): item for item in summaries}
    for task in diag6_contract.TASKS:
        attempts = [
            item for item in invalid_attempts
            if str(item.get("task_name")) == task
            and int(item.get("seed", -1)) == diag6_contract.TASK_SEED
        ]
        if len(attempts) > 2:
            errors.append("infrastructure_invalid_attempt_limit_exceeded")
        for attempt in attempts:
            replacement_id = str(attempt.get("resolved_by_episode_id") or "")
            replacement = valid_by_id.get(replacement_id)
            if replacement is None:
                errors.append("unresolved_infrastructure_invalid_attempt")
                continue
            if str(attempt.get("episode_id")) not in (
                replacement.get("resolves_invalid_episode_ids") or []
            ):
                errors.append("invalid_replacement_bidirectional_link_mismatch")
    return sorted(set(errors))


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_bpr_checkpoint(suite_dir: Path, payload: dict) -> None:
    """Persist the authoritative append-only BPR checkpoint and a mutable pointer."""
    checkpoint_dir = suite_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(checkpoint_dir.glob("A1R1_BPR_V2_CHECKPOINT_*.json"))
    ordinal = len(existing)
    previous = _sha256(existing[-1]) if existing else None
    authoritative = dict(payload)
    authoritative.update(
        {
            "checkpoint_ordinal": ordinal,
            "previous_checkpoint_file_sha256": previous,
            "content_sha256": None,
        }
    )
    authoritative["content_sha256"] = sha256(
        json.dumps(
            {key: value for key, value in authoritative.items() if key != "content_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    path = checkpoint_dir / f"A1R1_BPR_V2_CHECKPOINT_{ordinal:04d}.json"
    _atomic_json(path, authoritative)
    pointer = {
        "schema": "a1r1_bpr_v2_checkpoint_pointer_v1",
        "latest_checkpoint": str(path.relative_to(suite_dir)).replace("\\", "/"),
        "latest_checkpoint_file_sha256": _sha256(path),
    }
    _atomic_json(suite_dir / "checkpoint.json", pointer)


def _load_bpr_checkpoint_pointer(suite_dir: Path) -> dict:
    pointer = json.loads((suite_dir / "checkpoint.json").read_text(encoding="utf-8"))
    if pointer.get("schema") != "a1r1_bpr_v2_checkpoint_pointer_v1":
        raise RuntimeError("BPR-v2 checkpoint pointer schema mismatch")
    path = suite_dir / str(pointer.get("latest_checkpoint") or "")
    if not path.is_file() or _sha256(path) != pointer.get("latest_checkpoint_file_sha256"):
        raise RuntimeError("BPR-v2 checkpoint pointer hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = sha256(
        json.dumps(
            {key: value for key, value in payload.items() if key != "content_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if payload.get("content_sha256") != canonical:
        raise RuntimeError("BPR-v2 checkpoint content hash mismatch")
    return payload


def _append_a1r3v3_checkpoint(suite_dir: Path, payload: dict) -> None:
    checkpoint_dir = suite_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(checkpoint_dir.glob("A1R3V3_OSCNR_CHECKPOINT_*.json"))
    ordinal = len(existing)
    authoritative = dict(payload)
    authoritative.update(
        {
            "checkpoint_ordinal": ordinal,
            "previous_checkpoint_file_sha256": (
                _sha256(existing[-1]) if existing else None
            ),
            "content_sha256": None,
        }
    )
    authoritative["content_sha256"] = sha256(
        json.dumps(
            {key: value for key, value in authoritative.items() if key != "content_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    path = checkpoint_dir / f"A1R3V3_OSCNR_CHECKPOINT_{ordinal:04d}.json"
    _atomic_json(path, authoritative)
    _atomic_json(
        suite_dir / "checkpoint.json",
        {
            "schema": "a1r3v3_oscnr_checkpoint_pointer_v1",
            "latest_checkpoint": str(path.relative_to(suite_dir)).replace("\\", "/"),
            "latest_checkpoint_file_sha256": _sha256(path),
        },
    )


def _load_a1r3v3_checkpoint_pointer(suite_dir: Path) -> dict:
    pointer = json.loads((suite_dir / "checkpoint.json").read_text(encoding="utf-8"))
    if pointer.get("schema") != "a1r3v3_oscnr_checkpoint_pointer_v1":
        raise RuntimeError("A1-R3-v3 checkpoint pointer schema mismatch")
    path = suite_dir / str(pointer.get("latest_checkpoint") or "")
    if not path.is_file() or _sha256(path) != pointer.get("latest_checkpoint_file_sha256"):
        raise RuntimeError("A1-R3-v3 checkpoint pointer hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = sha256(
        json.dumps(
            {key: value for key, value in payload.items() if key != "content_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if payload.get("content_sha256") != canonical:
        raise RuntimeError("A1-R3-v3 checkpoint content hash mismatch")
    return payload


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


def _episode_infrastructure_valid(
    summary: dict, *, require_single_transport: bool = False
) -> bool:
    try:
        finite_reward = math.isfinite(float(summary.get("evaluator_reward")))
    except (TypeError, ValueError):
        finite_reward = False
    calls = [
        (step.get("model_call") or {}) for step in summary.get("steps", [])
    ] + [
        (attempt.get("model_call") or {})
        for attempt in summary.get("auxiliary_model_call_attempts", [])
        if attempt.get("model_call") is not None
    ]
    single_transport = not require_single_transport or all(
        int(
            ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                "transport_attempts"
            )
            or 0
        ) == 1
        for step in ({"model_call": call} for call in calls)
    )
    return (
        summary.get("error") is None
        and finite_reward
        and not summary.get("lifecycle_errors")
        and single_transport
    )


def _all_model_call_audits(summary: dict) -> list[dict]:
    """Return normal executor plus separately recorded SYS-TRRC auxiliary calls."""
    calls = [(step.get("model_call") or {}) for step in summary.get("steps", [])]
    calls.extend(
        (attempt.get("model_call") or {})
        for attempt in summary.get("auxiliary_model_call_attempts", [])
        if attempt.get("model_call") is not None
    )
    return calls


def _usage_totals(summaries: list[dict]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for summary in summaries:
        calls = _all_model_call_audits(summary)
        for call in calls:
            usage = call.get("usage") or {}
            for key in totals:
                totals[key] += int(usage.get(key) or 0)
    return totals


def _a10_memory_token_counts(
    summaries: list[dict],
    *,
    per_read: dict[tuple[str, int], int] | None = None,
) -> dict[str, int]:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        A10_MODEL_REALPATH, local_files_only=True, trust_remote_code=True
    )
    counts: dict[str, int] = {}
    for summary in summaries:
        total = 0
        for step in summary.get("steps", []):
            text = str((step.get("memory_read") or {}).get("exact_injected_text") or "")
            if text:
                token_count = len(tokenizer.encode(text, add_special_tokens=False))
                total += token_count
                if per_read is not None:
                    per_read[
                        (
                            str(summary["episode_id"]),
                            int(step.get("step_index", step.get("step", -1))),
                        )
                    ] = token_count
        counts[str(summary["episode_id"])] = total
    return counts


def _a10_pairwise(
    summaries: list[dict], reference_arm: str, reference: dict
) -> dict[str, float | int]:
    current = {str(item["task_name"]): item for item in summaries}
    reference_tasks = {
        str(item["task_name"]): item[reference_arm]
        for item in reference.get("tasks") or []
    }
    wins = losses = ties = 0
    for task_name, summary in current.items():
        ref = reference_tasks[task_name]
        delta = int(bool(summary.get("success"))) - int(bool(ref.get("success")))
        wins += int(delta > 0)
        losses += int(delta < 0)
        ties += int(delta == 0)
    usage = _usage_totals(summaries)
    ref_summary = reference["summaries"][reference_arm]
    elapsed = sum(
        (
            datetime.fromisoformat(item["finished_at"])
            - datetime.fromisoformat(item["started_at"])
        ).total_seconds()
        for item in summaries
    )
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "success_delta": sum(int(bool(item.get("success"))) for item in summaries) - int(ref_summary["success_count"]),
        "reward_delta": sum(float(item["evaluator_reward"]) for item in summaries) - float(ref_summary["reward_sum"]),
        "action_delta": sum(int(item["executed_action_count"]) for item in summaries) - int(ref_summary["executed_actions"]),
        "call_delta": sum(int(item["model_call_count"]) for item in summaries) - int(ref_summary["model_calls"]),
        "prompt_token_delta": usage["prompt_tokens"] - int(ref_summary["prompt_tokens"]),
        "total_token_delta": usage["total_tokens"] - int(ref_summary["total_tokens"]),
        "elapsed_delta": elapsed - float(ref_summary["valid_elapsed_seconds"]),
    }


def _diag6_pairwise(
    summaries: list[dict], reference_arm: str, reference: dict
) -> dict[str, float | int]:
    current = {str(item["task_name"]): item for item in summaries}
    references = {
        str(item["task_name"]): item[reference_arm]
        for item in reference.get("tasks") or []
        if str(item["task_name"]) in current
    }
    if set(current) != set(references):
        raise RuntimeError(f"DIAG6 paired {reference_arm} task identity mismatch")
    wins = losses = ties = 0
    for task_name, summary in current.items():
        delta = int(bool(summary.get("success"))) - int(bool(references[task_name].get("success")))
        wins += int(delta > 0); losses += int(delta < 0); ties += int(delta == 0)
    def total(key: str) -> float:
        return sum(float(item.get(key) or 0) for item in references.values())
    usage = _usage_totals(summaries)
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "success_delta": sum(int(bool(item.get("success"))) for item in summaries) - int(total("success")),
        "reward_delta": sum(float(item.get("evaluator_reward") or 0) for item in summaries) - total("reward"),
        "action_delta": sum(int(item.get("executed_action_count") or 0) for item in summaries) - int(total("executed_actions")),
        "call_delta": sum(int(item.get("model_call_count") or 0) for item in summaries) - int(total("model_calls")),
        "prompt_token_delta": usage["prompt_tokens"] - int(total("prompt_tokens")),
        "total_token_delta": usage["total_tokens"] - int(total("total_tokens")),
    }


def _a1r3_failure_causal_analysis(summaries: list[dict]) -> list[dict]:
    from raven_m.official_qwen_mobile.a1r3_stale_resistant_pending import (
        canonical_action_family,
    )

    records: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    for summary in summaries:
        steps = list(summary.get("steps") or [])
        for index, step in enumerate(steps):
            read = step.get("memory_read") or {}
            if not read.get("failure_evidence_injected"):
                continue
            failed_family = str(read.get("failed_action_family") or "")
            support_step = int(read.get("failure_second_support_step") or -1)
            signature = (str(summary["episode_id"]), support_step, failed_family)
            if not failed_family or signature in seen:
                continue
            seen.add(signature)
            current = canonical_action_family(
                (step.get("decision") or {}).get("canonical_action")
            )
            current_family = current[0] if current else None
            diverged = current_family is not None and current_family != failed_family
            executed_after_read: list[dict] = []
            for later in steps[index:]:
                if later.get("executed"):
                    executed_after_read.append(later)
                if len(executed_after_read) >= 8:
                    break
            progress_index = None
            progress_step = None
            for offset, later in enumerate(executed_after_read[:4]):
                transition = later.get("transition") or {}
                try:
                    fraction = float(transition.get("changed_pixel_fraction_gt_5") or 0)
                except (TypeError, ValueError):
                    fraction = 0.0
                if transition.get("same_shape") is False or fraction > 0.001:
                    progress_index = offset
                    progress_step = int(later.get("step", -1))
                    break
            relapse_step = None
            if progress_index is not None:
                for later in executed_after_read[progress_index + 1 : progress_index + 5]:
                    family = canonical_action_family(
                        (later.get("decision") or {}).get("canonical_action")
                    )
                    transition = later.get("transition") or {}
                    try:
                        fraction = float(transition.get("changed_pixel_fraction_gt_5") or 0)
                    except (TypeError, ValueError):
                        fraction = 0.0
                    no_progress = transition.get("same_shape") is True and fraction <= 0.001
                    if family and family[0] == failed_family and no_progress:
                        relapse_step = int(later.get("step", -1))
                        break
            records.append(
                {
                    "episode_id": summary["episode_id"],
                    "task_name": summary["task_name"],
                    "failure_second_support_step": support_step,
                    "first_injection_step": int(step.get("step", -1)),
                    "failed_action_family": failed_family,
                    "next_action_family": current_family,
                    "next_action_diverged": diverged,
                    "material_progress_step_within_4": progress_step,
                    "same_failure_relapse_step_within_4": relapse_step,
                    "productive_signal": bool(
                        diverged and progress_step is not None and relapse_step is None
                    ),
                }
            )
    return records


def _a1r3v3_causal_analysis(summaries: list[dict]) -> list[dict]:
    """Classify the primary arm without pretending the ablation already ran."""

    from raven_m.official_qwen_mobile.a1r3v3_one_shot_cnr import (
        canonical_action_family,
    )

    records: list[dict] = []
    for summary in summaries:
        steps = list(summary.get("steps") or [])
        creation_count = int(
            ((summary.get("memory_mechanism") or {}).get("counters") or {}).get(
                "cnr_receipt_creation_count"
            )
            or 0
        )
        committed: tuple[int, dict, dict] | None = None
        for index, step in enumerate(steps):
            read = step.get("memory_read") or {}
            commit = read.get("injection_commit") or {}
            if commit.get("failure_evidence_injected"):
                committed = (index, step, commit)
                break
        if committed is None:
            records.append(
                {
                    "episode_id": summary["episode_id"],
                    "task_name": summary["task_name"],
                    "receipt_created": creation_count > 0,
                    "receipt_committed": False,
                    "classification": (
                        "CREATED_NOT_COMMITTED" if creation_count else "NO_OPPORTUNITY"
                    ),
                    "success": bool(summary.get("success")),
                }
            )
            continue
        index, step, commit = committed
        read = step.get("memory_read") or {}
        failed_family = str(read.get("failed_action_family") or "")
        next_family_record = canonical_action_family(
            (step.get("decision") or {}).get("canonical_action")
        )
        next_family = next_family_record[0] if next_family_record else None
        action_diverged = bool(next_family and next_family != failed_family)
        action_sha = _json_digest(
            (step.get("decision") or {}).get("canonical_action")
        )
        executed_after = [item for item in steps[index:] if item.get("executed")][:8]
        visible_step = None
        for later in executed_after[:4]:
            transition = later.get("transition") or {}
            try:
                fraction = float(transition.get("changed_pixel_fraction_gt_5"))
            except (TypeError, ValueError):
                fraction = 0.0
            if transition.get("same_shape") is False or fraction > 0.001:
                visible_step = int(later.get("step", -1))
                break
        relapse_step = None
        if visible_step is not None:
            for later in executed_after:
                if int(later.get("step", -1)) <= visible_step:
                    continue
                transition = later.get("transition") or {}
                try:
                    fraction = float(transition.get("changed_pixel_fraction_gt_5"))
                except (TypeError, ValueError):
                    fraction = 1.0
                if transition.get("same_shape") is True and fraction <= 0.001:
                    relapse_step = int(later.get("step", -1))
                    break
        if not action_diverged:
            classification = "COMMITTED_NO_ACTION_DIVERGENCE"
        elif visible_step is None:
            classification = "DIVERGENCE_NO_VISIBLE_CHANGE"
        elif relapse_step is not None:
            classification = "VISIBLE_CHANGE_RELAPSED"
        elif summary.get("success"):
            classification = "QUALIFYING_NEW_WIN_ABLATION_UNRESOLVED"
        else:
            classification = "VISIBLE_CHANGE_NO_SUCCESS"
        records.append(
            {
                "episode_id": summary["episode_id"],
                "task_name": summary["task_name"],
                "receipt_created": True,
                "receipt_committed": True,
                "read_step": int(step.get("step", -1)),
                "receipt_id": commit.get("cnr_receipt_id"),
                "exact_injected_text_sha256": commit.get(
                    "exact_injected_text_sha256"
                ),
                "post_read_action_sha256": action_sha,
                "failed_action_family": failed_family,
                "post_read_action_family": next_family,
                "post_read_action_diverged_from_failed_family": action_diverged,
                "visible_screen_change_step_within_4": visible_step,
                "relapse_step_within_4_after_change": relapse_step,
                "classification": classification,
                "success": bool(summary.get("success")),
            }
        )
    return records


def _a10_causal_read_analysis(summaries: list[dict]) -> list[dict]:
    records: list[dict] = []
    for summary in summaries:
        audit = summary.get("memory_mechanism") or {}
        anchors = ((audit.get("goal") or {}).get("anchors") or [])
        frontiers = {
            str(item.get("frontier_id")): item
            for item in ((audit.get("frontiers") or {}).get("records") or [])
        }
        steps = {int(item.get("step", -1)): item for item in summary.get("steps", [])}
        for event in ((audit.get("reads") or {}).get("read_events") or []):
            read_step = int(event.get("step", -1))
            step = steps.get(read_step) or {}
            mask = int(event.get("open_anchor_mask") or 0)
            frontier = frontiers.get(str(event.get("frontier_id"))) or {}
            branches = list((frontier.get("branches") or {}).values())
            delta = event.get("open_anchor_confidence_delta_within_4")
            productive = bool(
                event.get("next_action_was_novel")
                and event.get("escaped_frontier_within_3")
                and not event.get("returned_within_4")
                and ((delta is not None and float(delta) >= .15) or summary.get("success"))
            )
            negative = bool(
                not event.get("next_action_was_novel")
                and event.get("returned_within_4")
                and float(delta or 0.0) < .15
                and not summary.get("success")
            )
            records.append(
                {
                    "task": summary.get("task_name"),
                    "episode": summary.get("episode_id"),
                    "read_step": read_step,
                    "trigger_kind": event.get("trigger_kind"),
                    "trigger_score": event.get("score"),
                    "open_obligations_before_read": [
                        item.get("literal")
                        for index, item in enumerate(anchors)
                        if mask & (1 << index)
                    ],
                    "locally_supported_obligations": [
                        item.get("literal")
                        for item in anchors
                        if item.get("status") == "LOCALLY_SUPPORTED"
                    ],
                    "matching_frontier": event.get("frontier_id"),
                    "prior_branches": [item.get("branch_id") for item in branches],
                    "prior_branch_outcomes": [
                        {
                            "branch_id": item.get("branch_id"),
                            "no_progress": item.get("raw_no_progress_count"),
                            "local_change": item.get("raw_local_change_count"),
                            "return": item.get("raw_return_count"),
                            "durable": item.get("raw_durable_count"),
                            "failure_confidence": item.get("failure_confidence"),
                            "escape_confidence": item.get("escape_confidence"),
                        }
                        for item in branches
                    ],
                    "exact_injected_text": (step.get("memory_read") or {}).get(
                        "exact_injected_text"
                    ),
                    "rendered_sha256": event.get("rendered_sha256"),
                    "next_action": (step.get("decision") or {}).get(
                        "canonical_action"
                    ),
                    "next_branch_id": event.get("next_action_branch_id"),
                    "next_branch_was_novel": event.get("next_action_was_novel"),
                    "screen_left_frontier_within_3": event.get(
                        "escaped_frontier_within_3"
                    ),
                    "screen_returned_within_4": event.get("returned_within_4"),
                    "anchor_confidence_delta_within_4": delta,
                    "episode_reward": summary.get("evaluator_reward"),
                    "final_success": summary.get("success"),
                    "analysis_class": (
                        "trace_grounded_productive_divergence_hypothesis"
                        if productive
                        else "activation_without_productive_divergence"
                        if negative
                        else "no_causal_classification"
                    ),
                }
            )
    return records


def _dual_causal_read_analysis(summaries: list[dict]) -> list[dict]:
    """Join arm-native read audits to the exact injected prompt and next action.

    The two mechanisms intentionally have different internal frontier schemas,
    so shared integration records the stable causal boundary without guessing
    or rewriting arm-native evidence fields.
    """
    records: list[dict] = []
    for summary in summaries:
        audit = summary.get("memory_mechanism") or {}
        steps = {int(item.get("step_index", item.get("step", -1))): item for item in summary.get("steps", [])}
        read_events = ((audit.get("reads") or {}).get("read_events") or audit.get("read_events") or [])
        for event in read_events:
            read_step = int(event.get("step", event.get("step_index", -1)))
            step = steps.get(read_step) or {}
            memory_read = step.get("memory_read") or {}
            records.append(
                {
                    "task": summary.get("task_name"),
                    "episode": summary.get("episode_id"),
                    "read_step": read_step,
                    "trigger_kind": event.get("trigger_kind", event.get("kind")),
                    "trigger_score": event.get("score"),
                    "exact_injected_text": memory_read.get("exact_injected_text"),
                    "rendered_sha256": event.get("rendered_sha256", memory_read.get("rendered_sha256")),
                    "next_action": (step.get("decision") or {}).get("canonical_action"),
                    "episode_reward": summary.get("evaluator_reward"),
                    "final_success": summary.get("success"),
                    "arm_native_event": event,
                    "analysis_class": event.get("analysis_class", "requires_arm_native_causal_review"),
                }
            )
    return records


def _a12_causal_read_analysis(
    summaries: list[dict],
    per_read_token_counts: dict[tuple[str, int], int] | None = None,
) -> list[dict]:
    """Join A12 read events, post-read watches, executed actions and reward.

    Post-read fields are audit-only. Missing watch evidence is retained as
    unknown/false and can never be promoted into productive memory evidence by
    the result aggregator.
    """
    records: list[dict] = []
    for summary in summaries:
        audit = summary.get("memory_mechanism") or {}
        read_events = list(audit.get("read_events") or [])
        watches = list(audit.get("post_read_watches") or [])
        watches_by_read = {
            str(item.get("read_id")): item
            for item in watches
            if item.get("read_id")
        }
        steps = {
            int(item.get("step_index", item.get("step", -1))): item
            for item in summary.get("steps", [])
        }
        for event in read_events:
            read_step = int(event.get("read_step", event.get("step", -1)))
            watch = watches_by_read.get(str(event.get("read_id"))) or {}
            step = steps.get(read_step) or {}
            memory_read = step.get("memory_read") or {}
            support_steps = [int(value) for value in event.get("support_steps") or []]
            next_diverged = watch.get("next_action_diverged") is True
            material_progress = watch.get("material_progress_within_2") is True
            relapsed = watch.get("same_failed_action_within_4") is True
            productive = bool(
                event.get("actual_nonempty") is True
                and next_diverged
                and material_progress
                and not relapsed
                and summary.get("success") is True
            )
            # The controller record is the authoritative prompt-side evidence;
            # the arm-native event remains a deterministic cross-check.
            exact_text = memory_read.get("exact_injected_text") or event.get(
                "exact_injected_text"
            )
            exact_text = str(exact_text or "")
            records.append(
                {
                    "task": summary.get("task_name"),
                    "episode_id": summary.get("episode_id"),
                    "read_step": read_step,
                    "failed_screen_descriptor": watch.get("failed_screen_descriptor"),
                    "failed_action_family": watch.get("failed_action_family", event.get("action_family")),
                    "failed_action_label": event.get("action_label"),
                    "first_support_step": support_steps[0] if support_steps else None,
                    "second_support_step": support_steps[1] if len(support_steps) > 1 else None,
                    "support_count": int(event.get("support_count") or 0),
                    "maturity_step": event.get("maturity_step"),
                    "eligible_read_step": event.get("eligible_read_step"),
                    "actual_nonempty": bool(event.get("actual_nonempty")),
                    "exact_injected_text": exact_text,
                    "rendered_sha256": sha256(exact_text.encode("utf-8")).hexdigest(),
                    "rendered_chars": len(exact_text),
                    "rendered_tokens": (
                        event.get("rendered_tokens")
                        if event.get("rendered_tokens") is not None
                        else (per_read_token_counts or {}).get(
                            (str(summary.get("episode_id")), read_step)
                        )
                    ),
                    "next_action_step": watch.get("next_action_step"),
                    "next_action_family": watch.get("next_action_family"),
                    "next_action_diverged": watch.get("next_action_diverged"),
                    "material_progress_within_2": watch.get("material_progress_within_2"),
                    "context_loss_within_2": watch.get("context_loss_within_2"),
                    "same_failed_action_within_4": watch.get("same_failed_action_within_4"),
                    "episode_reward": summary.get("evaluator_reward"),
                    "episode_success": summary.get("success"),
                    "productive_divergence_hypothesis": productive,
                    "analysis_class": (
                        "trace_grounded_productive_divergence_hypothesis"
                        if productive
                        else "activation_without_productive_divergence"
                    ),
                }
            )
    return records


def _diag6_causal_read_analysis(arm: str, summaries: list[dict]) -> list[dict]:
    if arm == "a12":
        return _a12_causal_read_analysis(summaries)
    records = _dual_causal_read_analysis(summaries)
    for record in records:
        event = record.get("arm_native_event") or {}
        diverged = event.get("next_action_was_novel") is True
        escaped = event.get("escaped_frontier_within_3") is True
        relapsed = event.get("returned_within_4") is True
        productive = bool(diverged and escaped and not relapsed)
        record.update(
            {
                "next_action_diverged": event.get("next_action_was_novel"),
                "short_horizon_escape_or_progress": event.get("escaped_frontier_within_3"),
                "relapse_within_4": event.get("returned_within_4"),
                "productive_divergence_hypothesis": productive,
                "analysis_class": (
                    "trace_grounded_productive_divergence_hypothesis"
                    if productive
                    else "activation_without_productive_divergence"
                ),
            }
        )
    return records


def _json_digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _a10_episode_entry(
    *, suite_dir: Path, summary: dict, run_signature_sha256: str
) -> dict:
    episode_id = str(summary["episode_id"])
    episode_path = suite_dir / "episodes" / episode_id / "episode.json"
    if not episode_path.is_file():
        raise RuntimeError(f"A10 episode artifact missing: {episode_path}")
    on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
    if _json_digest(on_disk) != _json_digest(summary):
        raise RuntimeError(f"A10 checkpoint summary differs from episode artifact: {episode_id}")
    return {
        "task_name": str(summary["task_name"]),
        "seed": int(summary["seed"]),
        "episode_id": episode_id,
        "episode_json_sha256": _sha256(episode_path),
        "summary_sha256": _json_digest(summary),
        "run_signature_sha256": run_signature_sha256,
    }


def _load_a10_checkpoint(
    *, suite_dir: Path, checkpoint: dict, run_signature_sha256: str
) -> tuple[list[dict], list[dict], list[dict]]:
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a10_valid_entries") or [])
    invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
    if len(entries) != len(summaries):
        raise RuntimeError("A10 checkpoint entry/summary cardinality mismatch")
    for summary, entry in zip(summaries, entries, strict=True):
        if entry.get("run_signature_sha256") != run_signature_sha256:
            raise RuntimeError("A10 checkpoint entry signature drift")
        expected_identity = (
            str(summary.get("task_name")),
            int(summary.get("seed", -1)),
            str(summary.get("episode_id")),
        )
        entry_identity = (
            str(entry.get("task_name")),
            int(entry.get("seed", -1)),
            str(entry.get("episode_id")),
        )
        if entry_identity != expected_identity:
            raise RuntimeError("A10 checkpoint entry identity mismatch")
        episode_path = suite_dir / "episodes" / entry_identity[2] / "episode.json"
        if not episode_path.is_file() or _sha256(episode_path) != entry.get("episode_json_sha256"):
            raise RuntimeError("A10 checkpoint episode artifact hash mismatch")
        on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
        if (
            _json_digest(on_disk) != entry.get("summary_sha256")
            or _json_digest(summary) != entry.get("summary_sha256")
            or not _episode_infrastructure_valid(on_disk, require_single_transport=True)
        ):
            raise RuntimeError("A10 checkpoint episode validity closure failed")
    return summaries, entries, invalid_attempts


def _load_dual_arm_checkpoint(
    *,
    suite_dir: Path,
    checkpoint: dict,
    run_signature_sha256: str,
    arm: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    if (
        checkpoint.get("schema") != arm["checkpoint_schema"]
        or checkpoint.get("prospective_arm") != arm["arm"]
        or checkpoint.get("experiment_id") != arm["experiment_id"]
        or checkpoint.get("mechanism_id") != arm["mechanism_id"]
    ):
        raise RuntimeError(
            f"{arm['label']} checkpoint identity mismatch; cross-arm resume is forbidden"
        )
    if arm["arm"] == "sys_nag" and checkpoint.get("system_id") != arm[
        "contract"
    ].SYSTEM_ID:
        raise RuntimeError(f"{arm['label']} checkpoint system identity mismatch")
    if (arm["arm"].startswith("sys_trrc_") or arm["arm"] in {"sys_nag", "a1r13", "a1r13d", "a1r14", "a1r15"}) and checkpoint.get(
        "content_sha256"
    ) != arm["contract"].content_sha256(checkpoint):
        raise RuntimeError(f"{arm['label']} checkpoint content hash mismatch")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get(arm["entry_key"]) or [])
    invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
    if len(entries) != len(summaries):
        raise RuntimeError(f"{arm['label']} checkpoint entry/summary cardinality mismatch")
    for summary, entry in zip(summaries, entries, strict=True):
        if entry.get("run_signature_sha256") != run_signature_sha256:
            raise RuntimeError(f"{arm['label']} checkpoint entry signature drift")
        expected_identity = (
            str(summary.get("task_name")),
            int(summary.get("seed", -1)),
            str(summary.get("episode_id")),
        )
        entry_identity = (
            str(entry.get("task_name")),
            int(entry.get("seed", -1)),
            str(entry.get("episode_id")),
        )
        if entry_identity != expected_identity:
            raise RuntimeError(f"{arm['label']} checkpoint entry identity mismatch")
        episode_path = suite_dir / "episodes" / entry_identity[2] / "episode.json"
        if not episode_path.is_file() or _sha256(episode_path) != entry.get("episode_json_sha256"):
            raise RuntimeError(f"{arm['label']} checkpoint episode artifact hash mismatch")
        on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
        if (
            _json_digest(on_disk) != entry.get("summary_sha256")
            or _json_digest(summary) != entry.get("summary_sha256")
            or not _episode_infrastructure_valid(on_disk, require_single_transport=True)
        ):
            raise RuntimeError(f"{arm['label']} checkpoint episode validity closure failed")
    return summaries, entries, invalid_attempts


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
        "--a10-ecobf",
        action="store_true",
        help="Run the preregistered A10 Evidence-Calibrated Obligation-Branch Frontier arm.",
    )
    parser.add_argument(
        "--a10-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a10/A10_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a10-launch-receipt",
        type=Path,
        help="Fresh A10 live receipt bound to the A10 zero-generation preflight.",
    )
    parser.add_argument(
        "--a10-v2-emobf",
        action="store_true",
        help="Run the independently frozen A10-v2 EM-OBF prospective arm.",
    )
    parser.add_argument(
        "--a10-v2-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a10_v2/A10_V2_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a10-v2-launch-receipt",
        type=Path,
        help="Fresh A10-v2 receipt bound only to its own preflight.",
    )
    parser.add_argument(
        "--a11-crc-ecobf",
        action="store_true",
        help="Run the independently frozen A11 CRC-ECOBF prospective arm.",
    )
    parser.add_argument(
        "--a11-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a11-launch-receipt",
        type=Path,
        help="Fresh A11 receipt bound only to its own preflight.",
    )
    parser.add_argument(
        "--a12-madm",
        action="store_true",
        help="Run the independently frozen A12 Minimal Action-Divergence Memory arm.",
    )
    parser.add_argument(
        "--a12-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a12/A12_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a12-launch-receipt",
        type=Path,
        help="Fresh A12 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r13-evr", action="store_true", help="Run prospective A1-R13 evidence-value register."
    )
    parser.add_argument("--a1r13-preflight-report", type=Path, default=REPOSITORY_ROOT / "evidence/a1r13/A1R13_EVR_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r13-launch-receipt", type=Path)
    parser.add_argument(
        "--a1r13d-evr", action="store_true", help="Run A1-R13D target-first EVR diagnostic."
    )
    parser.add_argument("--a1r13d-preflight-report", type=Path, default=REPOSITORY_ROOT / "evidence/a1r13d/A1R13D_EVR_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r13d-launch-receipt", type=Path)
    parser.add_argument(
        "--a1r14-rgvr", action="store_true", help="Run prospective A1-R14 response-grounded value register."
    )
    parser.add_argument("--a1r14-preflight-report", type=Path, default=REPOSITORY_ROOT / "evidence/a1r14/A1R14_RGVR_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r14-launch-receipt", type=Path)
    parser.add_argument(
        "--a1r15-eovr", action="store_true", help="Run prospective A1-R15 explicit-observation value register."
    )
    parser.add_argument("--a1r15-preflight-report", type=Path, default=REPOSITORY_ROOT / "evidence/a1r15/A1R15_EOVR_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r15-launch-receipt", type=Path)
    parser.add_argument(
        "--a1r12-chp",action="store_true",help="Run prospective A1-R12 compacted-history composite."
    )
    parser.add_argument("--a1r12-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r12/A1R12_CHP_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r12-launch-receipt",type=Path)
    parser.add_argument(
        "--sys-nag",
        action="store_true",
        help="Run R2 with the SYS-NAG V4 composite route-recurrence guards.",
    )
    parser.add_argument(
        "--sys-nag-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument("--sys-nag-launch-receipt", type=Path)
    parser.add_argument(
        "--a1r11-cscp",action="store_true",help="Run prospective A1-R11 coordinate self-check composite."
    )
    parser.add_argument("--a1r11-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r11/A1R11_CSCP_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r11-launch-receipt",type=Path)
    parser.add_argument(
        "--a1r10-pacp",action="store_true",help="Run prospective A1-R10 pre-action calibrated composite."
    )
    parser.add_argument("--a1r10-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r10/A1R10_PACP_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r10-launch-receipt",type=Path)
    parser.add_argument(
        "--a1r9-rlcr",action="store_true",help="Run prospective A1-R9 run-length cycle recovery."
    )
    parser.add_argument("--a1r9-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r9/A1R9_RLCR_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r9-launch-receipt",type=Path)
    parser.add_argument(
        "--a1r8-rcrp",action="store_true",help="Run prospective A1-R8 route-cycle recovery ledger."
    )
    parser.add_argument("--a1r8-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r8/A1R8_RCRP_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r8-launch-receipt",type=Path)
    parser.add_argument(
        "--a1r7-grpl", action="store_true", help="Run prospective A1-R7 grounding-recovery ledger."
    )
    parser.add_argument("--a1r7-preflight-report",type=Path,default=REPOSITORY_ROOT/"evidence/a1r7/A1R7_GRPL_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r7-launch-receipt",type=Path)
    parser.add_argument(
        "--a1r6-gapl", action="store_true",
        help="Run the prospective A1-R6 goal-anchored pending ledger arm.",
    )
    parser.add_argument("--a1r6-preflight-report", type=Path, default=REPOSITORY_ROOT / "evidence/a1r6/A1R6_GAPL_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--a1r6-launch-receipt", type=Path, help="Fresh A1-R6 receipt.")
    parser.add_argument(
        "--a1r5-tipl",
        action="store_true",
        help="Run the prospective A1-R5 transition-invalidated pending ledger arm.",
    )
    parser.add_argument(
        "--a1r5-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r5/A1R5_TIPL_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r5-launch-receipt",
        type=Path,
        help="Fresh A1-R5 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r4-wrpl",
        action="store_true",
        help="Run the prospective A1-R4 writer-resilient pending ledger arm.",
    )
    parser.add_argument(
        "--a1r4-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r4/A1R4_WRPL_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r4-launch-receipt",
        type=Path,
        help="Fresh A1-R4 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r3v3-oscnr",
        action="store_true",
        help="Run the prospective A1-R3-v3 one-shot controller nonprogress receipt arm.",
    )
    parser.add_argument(
        "--sys-trrc-mode", choices=("base", "detector", "generic", "full"),
        help="Run exactly one independent SYS-TRRC D/G/F arm on frozen A1-R2.",
    )
    parser.add_argument(
        "--sys-trrc-stage", choices=("l1", "l2", "l3", "l4"),
        help="Execute exactly one frozen SYS-TRRC campaign stage.",
    )
    parser.add_argument(
        "--sys-trrc-preflight-report", type=Path,
        help="Mode-bound zero-generation SYS-TRRC preflight report.",
    )
    parser.add_argument(
        "--sys-trrc-launch-receipt", type=Path,
        help="Fresh mode-bound SYS-TRRC live server receipt.",
    )
    parser.add_argument(
        "--sys-trrc-campaign-ledger", type=Path,
        help="Hash-chained ledger authorizing the next global campaign stage.",
    )
    parser.add_argument(
        "--sys-trrc-processor-path", type=Path,
        help="Local same-hash Qwen processor snapshot for pre-HTTP token projection.",
    )
    parser.add_argument(
        "--sys-trrc-processor-python", type=Path,
        help="Isolated Python with Torch/Torchvision for exact AutoProcessor calls.",
    )
    parser.add_argument(
        "--a1r3v3-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r3v3-launch-receipt",
        type=Path,
        help="Fresh A1-R3-v3 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r3-srpl",
        action="store_true",
        help="Run the prospective A1-R3 stale-resistant pending ledger arm.",
    )
    parser.add_argument(
        "--a1r3-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r3/A1R3_SRPL_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r3-launch-receipt",
        type=Path,
        help="Fresh A1-R3 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r2-cvp",
        action="store_true",
        help="Run the prospective A1-R2 compact verified/pending ledger arm.",
    )
    parser.add_argument(
        "--a1r2-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r2/A1R2_CVP_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r2-launch-receipt",
        type=Path,
        help="Fresh A1-R2 receipt bound only to its own preflight and process.",
    )
    parser.add_argument(
        "--a1r1-bpr-v2-mode",
        choices=("primary", "empty_read"),
        help="Run the frozen A1-R1 BPR-v2 primary or five-task empty-read arm.",
    )
    parser.add_argument(
        "--a1r1-bpr-v2-preflight-report",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json",
    )
    parser.add_argument(
        "--a1r1-bpr-v2-launch-receipt",
        type=Path,
        help="Fresh arm-specific BPR-v2 live receipt.",
    )
    parser.add_argument(
        "--a1r1-bpr-v2-primary-result",
        type=Path,
        help="Immutable complete primary result required before empty-read generation.",
    )
    parser.add_argument(
        "--enriched-memory-diagnostic",
        choices=diag6_contract.ARM_ORDER,
        help=(
            "Run one source mechanism on the frozen post-hoc enriched six-task "
            "diagnostic panel; this never repairs the formal arm status."
        ),
    )
    parser.add_argument(
        "--enriched-diagnostic-preflight-report",
        type=Path,
        default=diag6_contract.PREFLIGHT_PATH,
    )
    parser.add_argument(
        "--enriched-diagnostic-launch-receipt",
        type=Path,
        help="Shared live server receipt bound only to the diagnostic preflight.",
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
            args.a10_ecobf,
            args.a10_v2_emobf,
            args.a11_crc_ecobf,
            args.a12_madm,
            args.a1r12_chp,
            args.a1r13_evr,
            args.a1r13d_evr,
            args.a1r14_rgvr,
            args.a1r15_eovr,
            args.sys_nag,
            args.a1r11_cscp,
            args.a1r10_pacp,
            args.a1r9_rlcr,
            args.a1r8_rcrp,
            args.a1r7_grpl,
            args.a1r6_gapl,
            args.a1r5_tipl,
            args.a1r4_wrpl,
            args.a1r3v3_oscnr,
            args.sys_trrc_mode,
            args.a1r3_srpl,
            args.a1r2_cvp,
            args.a1r1_bpr_v2_mode,
            args.enriched_memory_diagnostic,
        )
    )
    if diagnostic_modes > 1:
        parser.error(
            "--transient-observation-carry, --transition-attested-history, "
            "--evidence-qualified-progress, and --source-document-coverage "
            "--source-document-coverage-gate, --a1-working-memory, and "
            "--a2-verified-progress-memory, --a345-arm, --a678-arm, --a10-ecobf, "
            "--a10-v2-emobf, --a11-crc-ecobf, --a12-madm, --a1r13-evr, --a1r13d-evr, --a1r14-rgvr, --a1r15-eovr, --a1r12-chp, --a1r11-cscp, --a1r10-pacp, --a1r9-rlcr, --a1r8-rcrp, --a1r7-grpl, --a1r6-gapl, --a1r5-tipl, --a1r4-wrpl, --a1r3v3-oscnr, --a1r3-srpl, --a1r2-cvp, --a1r1-bpr-v2-mode, and "
            "--enriched-memory-diagnostic are mutually exclusive"
        )
    held_out_eligible = not bool(args.diagnostic) and not bool(
        args.held_out_ineligible_reason
    )
    a345_scored_arm = bool(args.a345_arm)
    a678_memory_arm = bool(args.a678_arm)
    a10_scored_arm = bool(args.a10_ecobf)
    enriched_diag_arm = str(args.enriched_memory_diagnostic or "") or None
    dual_arm_name = enriched_diag_arm or next(
        (
            name
            for name, selected in (
                ("a10v2", args.a10_v2_emobf),
                ("a11", args.a11_crc_ecobf),
                ("a12", args.a12_madm),
                ("a1r13", args.a1r13_evr),
                ("a1r13d", args.a1r13d_evr),
                ("a1r14", args.a1r14_rgvr),
                ("a1r15", args.a1r15_eovr),
                ("a1r12", args.a1r12_chp),
                ("sys_nag", args.sys_nag),
                ("a1r11", args.a1r11_cscp),
                ("a1r10", args.a1r10_pacp),
                ("a1r9", args.a1r9_rlcr),
                ("a1r8", args.a1r8_rcrp),
                ("a1r7", args.a1r7_grpl),
                ("a1r6", args.a1r6_gapl),
                ("a1r5", args.a1r5_tipl),
                ("a1r4", args.a1r4_wrpl),
                ("a1r3v3", args.a1r3v3_oscnr),
                (f"sys_trrc_{args.sys_trrc_mode}", args.sys_trrc_mode),
                ("a1r3", args.a1r3_srpl),
                ("a1r2", args.a1r2_cvp),
                ("bprv2", args.a1r1_bpr_v2_mode),
            )
            if selected
        ),
        None,
    )
    dual_arm = _load_dual_arm(dual_arm_name) if dual_arm_name else None
    sys_trrc_token_projector = None
    sys_trrc_text_delta_counter = None
    sys_trrc_local_processor_identity: dict | None = None
    sys_trrc_arm = bool(dual_arm_name and dual_arm_name.startswith("sys_trrc_"))
    sys_trrc_campaign_id = None
    if sys_trrc_arm:
        if args.sys_trrc_stage is None:
            parser.error("--sys-trrc-stage is required for a SYS-TRRC arm")
        if args.sys_trrc_mode in {"base", "detector"} and args.sys_trrc_stage not in {"l1", "l3"}:
            parser.error("SYS-TRRC Base/Detector-only permit only stages l1 and l3")
        if args.sys_trrc_stage != "l1" and args.resume_suite_dir is None:
            parser.error("SYS-TRRC stages after l1 require --resume-suite-dir for the same arm")
        if args.sys_trrc_campaign_ledger is None or not args.sys_trrc_campaign_ledger.is_file():
            parser.error("SYS-TRRC requires an initialized campaign ledger")
        try:
            campaign_ledger = dual_arm["contract"].validate_campaign_ledger(
                args.sys_trrc_campaign_ledger.resolve()
            )
            ledger_entries = list(campaign_ledger.get("entries") or [])
            if len(ledger_entries) >= len(dual_arm["contract"].CAMPAIGN_INVOCATION_ORDER):
                raise RuntimeError("campaign already complete")
            expected_invocation = dual_arm["contract"].CAMPAIGN_INVOCATION_ORDER[
                len(ledger_entries)
            ]
            if (args.sys_trrc_mode, args.sys_trrc_stage) != expected_invocation:
                raise RuntimeError(f"next campaign invocation is {expected_invocation}")
            if ledger_entries and ledger_entries[-1].get("advancement_authorized") is not True:
                raise RuntimeError("prior campaign stage is terminal")
            sys_trrc_campaign_id = str(campaign_ledger.get("campaign_id") or "")
            if not sys_trrc_campaign_id:
                raise RuntimeError("campaign id missing")
        except Exception as exc:
            parser.error(f"SYS-TRRC campaign ledger rejected: {exc}")
        if args.sys_trrc_processor_path is None:
            parser.error("SYS-TRRC requires --sys-trrc-processor-path")
        processor_python = (
            args.sys_trrc_processor_python
            if args.sys_trrc_processor_python is not None
            else Path(getattr(sys, "_base_executable", sys.executable))
        )
        from raven_m.official_qwen_mobile.sys_trrc_token_budget import (
            SubprocessExactQwenMultimodalTokenProjector,
            SubprocessExactQwenTextDeltaCounter,
        )
        try:
            sys_trrc_token_projector = SubprocessExactQwenMultimodalTokenProjector(
                processor_python, args.sys_trrc_processor_path,
                expected_revision=MODEL_REVISION,
            )
            if dual_arm["recovery_mode"] in {"generic", "full"}:
                sys_trrc_text_delta_counter = SubprocessExactQwenTextDeltaCounter(
                    sys_trrc_token_projector
                )
        except Exception as exc:
            parser.error(str(exc))
        sys_trrc_local_processor_identity = {
            "topology": "isolated_local_processor_subprocess_before_remote_http",
            "python_executable": str(Path(processor_python).resolve()),
            "python_executable_sha256": _sha256(Path(processor_python).resolve()),
            "processor_path": str(args.sys_trrc_processor_path.resolve()),
            "processor_files_sha256": dict(
                sys_trrc_token_projector.processor_files_sha256
            ),
            "runtime_identity": dict(sys_trrc_token_projector.runtime_identity),
        }
    elif args.sys_trrc_stage is not None:
        parser.error("--sys-trrc-stage requires --sys-trrc-mode")
    bpr_mode = str(args.a1r1_bpr_v2_mode or "") or None
    if dual_arm_name == "bprv2":
        assert dual_arm is not None and bpr_mode is not None
        bpr_contract = dual_arm["contract"]
        is_primary = bpr_mode == "primary"
        dual_arm.update(
            {
                "arm": f"bprv2_{bpr_mode}",
                "label": f"A1-R1 BPR-v2 {bpr_mode}",
                "experiment_id": bpr_contract.PRIMARY_EXPERIMENT_ID if is_primary else bpr_contract.EMPTY_EXPERIMENT_ID,
                "config_path": bpr_contract.PRIMARY_CONFIG_PATH if is_primary else bpr_contract.EMPTY_CONFIG_PATH,
                "checkpoint_schema": bpr_contract.PRIMARY_CHECKPOINT_SCHEMA if is_primary else bpr_contract.EMPTY_CHECKPOINT_SCHEMA,
                "result_schema": bpr_contract.PRIMARY_RESULT_SCHEMA if is_primary else bpr_contract.EMPTY_RESULT_SCHEMA,
                "result_key": "a1r1_bpr_v2_primary_result" if is_primary else "a1r1_bpr_v2_empty_read_result",
                "read_enabled": is_primary,
                "expected_count": 19 if is_primary else 5,
            }
        )
    dual_memory_arm = dual_arm is not None
    dual_scored_arm = dual_memory_arm and enriched_diag_arm is None
    dual_preflight_path = (
        args.enriched_diagnostic_preflight_report
        if enriched_diag_arm
        else args.sys_trrc_preflight_report
        if dual_arm_name and dual_arm_name.startswith("sys_trrc_")
        else args.a10_v2_preflight_report
        if dual_arm_name == "a10v2"
        else args.a11_preflight_report
        if dual_arm_name == "a11"
        else args.a12_preflight_report
        if dual_arm_name == "a12"
        else args.a1r13_preflight_report
        if dual_arm_name == "a1r13"
        else args.a1r13d_preflight_report
        if dual_arm_name == "a1r13d"
        else args.a1r14_preflight_report
        if dual_arm_name == "a1r14"
        else args.a1r15_preflight_report
        if dual_arm_name == "a1r15"
        else args.a1r12_preflight_report
        if dual_arm_name == "a1r12"
        else args.sys_nag_preflight_report
        if dual_arm_name == "sys_nag"
        else args.a1r11_preflight_report
        if dual_arm_name == "a1r11"
        else args.a1r10_preflight_report
        if dual_arm_name == "a1r10"
        else args.a1r9_preflight_report
        if dual_arm_name == "a1r9"
        else args.a1r8_preflight_report
        if dual_arm_name == "a1r8"
        else args.a1r7_preflight_report
        if dual_arm_name == "a1r7"
        else args.a1r6_preflight_report
        if dual_arm_name == "a1r6"
        else args.a1r5_preflight_report
        if dual_arm_name == "a1r5"
        else args.a1r4_preflight_report
        if dual_arm_name == "a1r4"
        else args.a1r3v3_preflight_report
        if dual_arm_name == "a1r3v3"
        else args.a1r3_preflight_report
        if dual_arm_name == "a1r3"
        else args.a1r2_preflight_report
        if dual_arm_name == "a1r2"
        else args.a1r1_bpr_v2_preflight_report
        if dual_arm_name == "bprv2"
        else None
    )
    dual_receipt_path = (
        args.enriched_diagnostic_launch_receipt
        if enriched_diag_arm
        else args.sys_trrc_launch_receipt
        if dual_arm_name and dual_arm_name.startswith("sys_trrc_")
        else args.a10_v2_launch_receipt
        if dual_arm_name == "a10v2"
        else args.a11_launch_receipt
        if dual_arm_name == "a11"
        else args.a12_launch_receipt
        if dual_arm_name == "a12"
        else args.a1r13_launch_receipt
        if dual_arm_name == "a1r13"
        else args.a1r13d_launch_receipt
        if dual_arm_name == "a1r13d"
        else args.a1r14_launch_receipt
        if dual_arm_name == "a1r14"
        else args.a1r15_launch_receipt
        if dual_arm_name == "a1r15"
        else args.a1r12_launch_receipt
        if dual_arm_name == "a1r12"
        else args.sys_nag_launch_receipt
        if dual_arm_name == "sys_nag"
        else args.a1r11_launch_receipt
        if dual_arm_name == "a1r11"
        else args.a1r10_launch_receipt
        if dual_arm_name == "a1r10"
        else args.a1r9_launch_receipt
        if dual_arm_name == "a1r9"
        else args.a1r8_launch_receipt
        if dual_arm_name == "a1r8"
        else args.a1r7_launch_receipt
        if dual_arm_name == "a1r7"
        else args.a1r6_launch_receipt
        if dual_arm_name == "a1r6"
        else args.a1r5_launch_receipt
        if dual_arm_name == "a1r5"
        else args.a1r4_launch_receipt
        if dual_arm_name == "a1r4"
        else args.a1r3v3_launch_receipt
        if dual_arm_name == "a1r3v3"
        else args.a1r3_launch_receipt
        if dual_arm_name == "a1r3"
        else args.a1r2_launch_receipt
        if dual_arm_name == "a1r2"
        else args.a1r1_bpr_v2_launch_receipt
        if dual_arm_name == "bprv2"
        else None
    )
    dual_preflight: dict | None = None
    dual_launch: dict | None = None
    a10_launch: dict | None = None
    a10_preflight: dict | None = None
    controller_memory_arm = a678_memory_arm or a10_scored_arm or dual_memory_arm
    a678_post_gate_diagnostic = a7_post_gate_diagnostic or a89_four_task_diagnostic
    a678_scored_arm = a678_memory_arm and not a678_post_gate_diagnostic
    prospective_gate_arm = (
        (args.a678_arm in {"a8v2", "a9"} and not a89_four_task_diagnostic)
        or a10_scored_arm
        or (dual_scored_arm and not sys_trrc_arm)
    ) and not (dual_arm_name == "bprv2" and bpr_mode == "empty_read")
    held_out_ineligible_reason = args.held_out_ineligible_reason
    if a678_scored_arm or a10_scored_arm or dual_scored_arm:
        # This seed and its A0/A1/A2/A3-A5 outcomes have already been inspected.
        # A6-A8 are valid paired mechanism comparisons, not held-out evidence.
        held_out_eligible = False
        held_out_ineligible_reason = (
            "post_observed_seed20260806_composite_system_comparison"
            if sys_trrc_arm else
            "post_observed_seed20260806_memory_mechanism_comparison"
        )
    scored_memory_arm = bool(
        args.a1_working_memory
        or args.a2_verified_progress_memory
        or a345_scored_arm
        or a678_scored_arm
        or a10_scored_arm
        or dual_scored_arm
    )
    if (
        args.resume_suite_dir is not None
        and not scored_memory_arm
        and not a678_post_gate_diagnostic
        and not enriched_diag_arm
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
        if dual_scored_arm:
            assert dual_arm is not None
            assert dual_preflight_path is not None
            if not dual_preflight_path.is_file():
                parser.error(
                    f"{dual_arm['label']} preflight is missing: {dual_preflight_path}"
                )
            try:
                preflight_kwargs = {}
                if dual_arm_name.startswith("sys_trrc_"):
                    preflight_kwargs["expected_mode"] = dual_arm["recovery_mode"]
                    preflight_kwargs["projector"] = sys_trrc_token_projector
                    preflight_kwargs["recompute_projection"] = True
                dual_preflight = dual_arm["validate_preflight"](
                    dual_preflight_path.resolve(), **preflight_kwargs
                )
            except Exception as exc:
                parser.error(str(exc))
            if dual_receipt_path is None or not dual_receipt_path.is_file():
                parser.error(
                    f"{dual_arm['label']} scored generation requires its own fresh live receipt"
                )
            try:
                receipt_kwargs = {"preflight_path": dual_preflight_path.resolve()}
                if dual_arm_name.startswith("sys_trrc_"):
                    receipt_kwargs["expected_mode"] = dual_arm["recovery_mode"]
                    receipt_kwargs["projector"] = sys_trrc_token_projector
                    receipt_kwargs["recompute_projection"] = True
                if dual_arm_name == "bprv2":
                    receipt_kwargs.update(
                        expected_read_enabled=dual_arm["read_enabled"],
                        expected_experiment_id=dual_arm["experiment_id"],
                    )
                dual_launch = dual_arm["validate_receipt"](
                    dual_receipt_path.resolve(), **receipt_kwargs
                )
            except Exception as exc:
                parser.error(str(exc))
            if (
                dual_arm_name.startswith("sys_trrc_")
                and args.url.rstrip("/") != "http://127.0.0.1:18000"
            ):
                parser.error("SYS-TRRC runner URL must match its qualified 127.0.0.1:18000 receipt")
            if dual_arm_name.startswith("sys_trrc_"):
                expected_processor_hashes = (
                    ((dual_preflight.get("checks") or {}).get(
                        "eight_opportunity_token_projection"
                    ) or {}).get("processor_files_sha256") or {}
                )
                if sys_trrc_token_projector.processor_files_sha256 != expected_processor_hashes:
                    parser.error("SYS-TRRC local processor snapshot differs from preflight")
                sys_trrc_local_processor_identity["processor_files_sha256"] = dict(
                    expected_processor_hashes
                )
            if dual_arm_name == "bprv2" and bpr_mode == "empty_read":
                if args.a1r1_bpr_v2_primary_result is None or not args.a1r1_bpr_v2_primary_result.is_file():
                    parser.error("BPR-v2 empty-read requires the immutable complete primary aggregate")
                primary_aggregate = json.loads(
                    args.a1r1_bpr_v2_primary_result.read_text(encoding="utf-8")
                )
                primary_result = primary_aggregate.get("a1r1_bpr_v2_primary_result") or {}
                if (
                    primary_result.get("schema") != dual_arm["contract"].PRIMARY_RESULT_SCHEMA
                    or primary_result.get("completion_status") != "COMPLETE_19"
                    or primary_result.get("valid_episode_count") != 19
                    or primary_result.get("mechanism_id") != dual_arm["mechanism_id"]
                ):
                    parser.error("BPR-v2 primary aggregate is not an immutable complete 19-task result")
        elif a10_scored_arm:
            if not args.a10_preflight_report.is_file():
                parser.error(f"A10 preflight is missing: {args.a10_preflight_report}")
            try:
                a10_preflight = validate_a10_preflight_report(
                    args.a10_preflight_report.resolve()
                )
            except Exception as exc:
                parser.error(str(exc))
            if args.a10_launch_receipt is None or not args.a10_launch_receipt.is_file():
                parser.error("A10 scored generation requires a fresh A10 live receipt")
            try:
                a10_launch = validate_a10_launch_receipt(
                    args.a10_launch_receipt.resolve(),
                    preflight_path=args.a10_preflight_report.resolve(),
                )
            except Exception as exc:
                parser.error(str(exc))
        elif a678_scored_arm:
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

    if enriched_diag_arm:
        if not args.diagnostic:
            parser.error("--enriched-memory-diagnostic requires --diagnostic")
        if args.task or args.manifest is None:
            parser.error("enriched diagnostic requires its frozen six-task manifest")
        if args.step_cap is not None:
            parser.error("enriched diagnostic forbids altered native task budgets")
        if args.generation_seed != diag6_contract.GENERATION_SEED or args.max_tokens != 32768:
            parser.error("enriched diagnostic generation parameters drifted")
        if args.observation_backend != "uiautomator":
            parser.error("enriched diagnostic must use uiautomator")
        if _sha256(args.manifest.resolve()) != _sha256(diag6_contract.MANIFEST_PATH.resolve()):
            parser.error("enriched diagnostic manifest drifted")
        assert dual_preflight_path is not None
        try:
            dual_preflight = diag6_contract.validate_preflight_report(
                dual_preflight_path.resolve()
            )
        except Exception as exc:
            parser.error(str(exc))
        if dual_receipt_path is None or not dual_receipt_path.is_file():
            parser.error("enriched diagnostic requires its qualified live receipt")
        try:
            dual_launch = diag6_contract.validate_launch_receipt(
                dual_receipt_path.resolve(),
                preflight_path=dual_preflight_path.resolve(),
            )
        except Exception as exc:
            parser.error(str(exc))
        held_out_eligible = False
        held_out_ineligible_reason = (
            "post_hoc_common_memory_opportunity_enriched_diagnostic_not_formal_arm_repair"
        )

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
    elif enriched_diag_arm:
        keys = tuple(
            (str(item["task_class"]), int(item["task_seed"])) for item in specs
        )
        expected_diag_keys = tuple(
            (name, diag6_contract.TASK_SEED) for name in diag6_contract.TASKS
        )
        if keys != expected_diag_keys:
            raise RuntimeError(
                "enriched diagnostic did not resolve the exact ordered six-task panel"
            )
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
        elif dual_arm_name in {"bprv2", "a1r2", "a1r3v3"} or dual_arm_name == "sys_nag" or (dual_arm_name and dual_arm_name.startswith("sys_trrc_")) or dual_arm_name in {"a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15"}:
            by_name = {str(item["task_class"]): item for item in specs}
            if sys_trrc_arm:
                campaign_order = (
                    dual_arm["contract"].CONTROL_TASK_ORDER
                    if dual_arm["recovery_mode"] in {"base", "detector"}
                    else dual_arm["contract"].FULL_TASK_ORDER
                )
                missing = sorted(set(campaign_order) - set(by_name))
                if missing:
                    raise RuntimeError(f"{dual_arm['label']} campaign tasks missing: {missing}")
                canonical_specs = [by_name[name] for name in campaign_order]
                stage_order = dual_arm["contract"].stage_contract(
                    dual_arm["recovery_mode"], str(args.sys_trrc_stage)
                )["tasks"]
                specs = [by_name[name] for name in stage_order]
                # The run signature binds the complete arm campaign, never the
                # currently authorized stage, so the same suite can advance.
                sys_trrc_canonical_specs = canonical_specs
            else:
                sys_trrc_canonical_specs = None
            gate_tasks = dual_arm["gate_tasks"]
            missing_gate = sorted(set(gate_tasks) - set(by_name))
            if missing_gate:
                raise RuntimeError(f"{dual_arm['label']} capability gate missing from manifest: {missing_gate}")
            remaining = [
                item for item in specs
                if str(item["task_class"]) not in gate_tasks
            ]
            gate_specs = [by_name[name] for name in gate_tasks]
            specs = (
                [by_name[name] for name in dual_arm["contract"].FULL_TASK_ORDER]
                if dual_arm_name in {"a1r13d", "a1r14", "a1r15"}
                else gate_specs + remaining
                if dual_arm_name in {"a1r2", "a1r3v3", "a1r3"} or dual_arm_name == "sys_nag" or (dual_arm_name and dual_arm_name.startswith("sys_trrc_")) or dual_arm_name in {"a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13"} or bpr_mode == "primary"
                else gate_specs
            )
            if sys_trrc_arm:
                specs = [by_name[name] for name in stage_order]
        elif prospective_gate_arm:
            by_name = {str(item["task_class"]): item for item in specs}
            missing_gate = sorted(set(A0_PRESERVATION_TASKS) - set(by_name))
            if missing_gate:
                raise RuntimeError(
                    f"{dual_arm['label'] if dual_scored_arm else 'A10' if a10_scored_arm else str(args.a678_arm).upper()} gate tasks missing from manifest: {missing_gate}"
                )
            remaining = [
                item
                for item in specs
                if str(item["task_class"]) not in A0_PRESERVATION_TASKS
            ]
            specs = [by_name[name] for name in A0_PRESERVATION_TASKS] + remaining
    canonical_specs = (
        list(sys_trrc_canonical_specs)
        if sys_trrc_arm
        else list(specs)
    )
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
            diag6_contract.ARM_BINDINGS[enriched_diag_arm]["experiment_id"]
            if enriched_diag_arm
            else (
                "A7_POST_GATE_SPORTS_DIAGNOSTIC_QWEN3VL32B_AW_HARD_S20260806_V1"
                if a7_sports_diagnostic
                else "A7_POST_GATE_REMAINING9_DIAGNOSTIC_QWEN3VL32B_AW_HARD_S20260806_V1"
            )
            if a7_post_gate_diagnostic
            else A89_DIAGNOSTIC_EXPERIMENT_IDS[str(args.a678_arm)]
            if a89_four_task_diagnostic
            else "A2_VERIFIED_PROGRESS_MEMORY_QWEN3VL32B_AW_HARD_S20260806_V1R1"
            if args.a2_verified_progress_memory
            else dual_arm["experiment_id"]
            if dual_scored_arm
            else A10_EXPERIMENT_ID
            if a10_scored_arm
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
            else diag6_contract.ARM_BINDINGS[enriched_diag_arm]["source_mechanism_id"]
            if enriched_diag_arm
            else dual_arm["mechanism_id"]
            if dual_scored_arm
            else A10_MECHANISM_ID
            if a10_scored_arm
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
    if enriched_diag_arm:
        assert dual_preflight is not None and dual_preflight_path is not None
        assert dual_launch is not None
        run_signature.update(
            {
                "diagnostic_protocol_id": diag6_contract.PROTOCOL_ID,
                "diagnostic_arm": enriched_diag_arm,
                "source_mechanism_id": diag6_contract.ARM_BINDINGS[enriched_diag_arm]["source_mechanism_id"],
                "formal_arm_status_repaired": False,
                "selection_rule": "post_hoc_common_memory_opportunity_enrichment",
                "task_order": list(diag6_contract.TASKS),
                "diagnostic_preflight_sha256": _sha256(dual_preflight_path),
                "implementation_commit": dual_preflight["implementation_commit"],
                "source_sha256": dual_preflight["source_sha256"],
                "evidence_sha256": dual_preflight["evidence_sha256"],
                "live_server_identity": {
                    "served_model_id": dual_launch["served_model_id"],
                    "model_realpath": dual_launch["model_realpath"],
                    "model_manifest_sha256": dual_launch["model_manifest_sha256"],
                    "packages": dual_launch["packages"],
                    "port": dual_launch["port"],
                },
                "transport_policy": "single_http_attempt_no_automatic_retry",
            }
        )
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
    if dual_scored_arm:
        assert dual_arm is not None
        assert dual_preflight_path is not None
        assert dual_launch is not None
        run_signature.update(
            {
                "prospective_arm": dual_arm["arm"],
                "mechanism_id": dual_arm["mechanism_id"],
                "experiment_id": dual_arm["experiment_id"],
                "prospective_config_sha256": _sha256(dual_arm["config_path"]),
                "prospective_preflight_sha256": _sha256(dual_preflight_path),
                "prospective_source_freeze_sha256": dual_preflight.get(
                    "source_freeze_content_sha256",
                    dual_preflight.get(
                        "source_freeze_sha256",
                        dual_preflight.get("source_freeze_payload_sha256"),
                    ),
                ),
                "prospective_live_server_stable_identity": {
                    "served_model_id": dual_launch["served_model_id"],
                    "model_realpath": dual_launch["model_realpath"],
                    "model_manifest_sha256": dual_launch["model_manifest_sha256"],
                    "port": dual_launch["port"],
                    "packages": dual_launch.get("packages") or {
                        "vllm": dual_launch.get("vllm_version"),
                        "torch": dual_launch.get("torch_version"),
                        "transformers": dual_launch.get("transformers_version"),
                    },
                },
                "task_order": (
                    "blocking_A1R2_success_6_then_frozen_manifest_remainder"
                    if dual_arm_name in {"a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "sys_nag"}
                    else "blocking_A0_4_then_Recipe_1_then_frozen_manifest_remainder"
                    if dual_arm_name == "a1r2" or (dual_arm_name == "bprv2" and bpr_mode == "primary")
                    else "fixed_five_task_non_fail_fast_after_primary_complete"
                    if dual_arm_name == "bprv2"
                    else "blocking_A0_4_task_gate_then_frozen_manifest_remainder"
                ),
                "reward_fail_fast": not (dual_arm_name == "bprv2" and bpr_mode == "empty_read"),
                "scientific_failure_rerun": False,
                "A0_preservation_tasks": list(A0_PRESERVATION_TASKS),
                "A0_preservation_required_for_continuation": True,
                "controller_authored_memory": True,
                "response_prefix_required": False,
                "official_system_prompt_unchanged": True,
                "extra_model_calls": 0,
                "guard": False,
                "action_override": False,
                "forced_termination": False,
            }
        )
        if dual_arm_name == "bprv2":
            run_signature.update(
                {
                    "bpr_mode": bpr_mode,
                    "read_enabled": dual_arm["read_enabled"],
                    "expected_valid_episode_count": dual_arm["expected_count"],
                    "gate5_tasks": list(dual_arm["contract"].GATE5_TASKS),
                    "primary_result_sha256": (
                        _sha256(args.a1r1_bpr_v2_primary_result)
                        if bpr_mode == "empty_read" else None
                    ),
                    "ordinary_history_deduplicated": True,
                    "response_prefix_required": True,
                }
            )
        elif dual_arm_name == "a1r2":
            run_signature.update(
                {
                    "gate5_tasks": list(dual_arm["contract"].GATE5_TASKS),
                    "ordinary_history_deduplicated": True,
                    "response_prefix_required": True,
                    "official_system_prompt_unchanged": False,
                    "system_prompt_identity": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
                }
            )
        elif dual_arm_name == "sys_nag":
            run_signature.update(
                {
                    "task_order": "blocking_A1R2_success_6_then_frozen_manifest_remainder",
                    "system_id": dual_arm["contract"].SYSTEM_ID,
                    "capability_gate_tasks": list(dual_arm["gate_tasks"]),
                    "ordinary_history_deduplicated": True,
                    "response_prefix_required": True,
                    "official_system_prompt_unchanged": False,
                    "system_prompt_identity": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
                    "auxiliary_model_calls": 0,
                    "guard_induced_continuation_normal_requests": "at_most_one_per_episode",
                    "guard": True,
                    "action_override": True,
                    "numeric_answer_override": True,
                    "pending_terminal_suppression": True,
                    "route_recurrence_suppression": True,
                    "pending_terminal_rule": {
                        "same_request_exact_r2_pending_nonempty": True,
                        "previous_executed_action_type": "wait",
                        "minimum_remaining_native_decision_slots": 1,
                        "max_blocks_per_episode": 1,
                    },
                    "forced_termination": False,
                    "a1r2_successes_required_for_continuation": True,
                }
            )
        elif dual_arm_name.startswith("sys_trrc_"):
            run_signature.update(
                {
                    "protocol_id": dual_arm["contract"].PROTOCOL_ID,
                    "campaign_id": sys_trrc_campaign_id,
                    "sys_trrc_arm_id": dual_arm["arm_id"],
                    "sys_trrc_mode": dual_arm["recovery_mode"],
                    "task_order": "staged_B1_D1_G1_F1_G2_F2_B3_D3_G3_F3_G4_F4_campaign",
                    "campaign_stage_is_not_part_of_scientific_signature": True,
                    "capability_gate_tasks": list(dual_arm["contract"].PRESERVATION_TASKS),
                    "activation_gate_task": dual_arm["contract"].ACTIVATION_TASK,
                    "r2_mechanism_id": "a1r2_compact_verified_pending_v1",
                    "r2_exact_prompt": True,
                    "ordinary_history_deduplicated": True,
                    "response_prefix_required": True,
                    "official_system_prompt_unchanged": False,
                    "system_prompt_identity": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
                    "extra_model_calls": 0 if dual_arm["recovery_mode"] in {"base", "detector"} else "at_most_one_per_episode",
                    "aux_retry": False,
                    "aux_max_tokens": 192,
                    "transport_policy": "single_http_attempt_no_automatic_retry",
                    "local_token_projection": sys_trrc_local_processor_identity,
                }
            )
        elif dual_arm_name in {"a1r3v3", "a1r3", "a1r4"} or dual_arm_name in {"a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15"}:
            run_signature.update(
                {
                    "capability_gate_tasks": list(dual_arm["gate_tasks"]),
                    "ordinary_history_deduplicated": True,
                    "response_prefix_required": True,
                    "official_system_prompt_unchanged": False,
                    "system_prompt_identity": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
                    "a1r2_successes_required_for_continuation": True,
                }
            )
            if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}:
                run_signature.update(
                    {
                        "task_order": (
                            "Browser_target_then_blocking_A1R2_success_6_then_remainder"
                            if dual_arm_name in {"a1r13d", "a1r14", "a1r15"}
                            else "blocking_A1R2_success_6_then_Browser_target_then_remainder"
                        ),
                        "target_gate_task": dual_arm["contract"].TARGET_GATE_TASK,
                        "evr_model_authored_values_only": True,
                        "evr_max_values": 6,
                        "evr_extra_model_calls": 0,
                        "guard": False,
                        "action_override": False,
                        "forced_termination": False,
                        "target_first": dual_arm_name in {"a1r13d", "a1r14", "a1r15"},
                    }
                )
    if a10_scored_arm:
        run_signature.update(
            {
                "a10_config_sha256": _sha256(A10_CONFIG_PATH),
                "a10_preflight_sha256": _sha256(args.a10_preflight_report),
                # The scientific signature binds the stable server identity,
                # not a process-specific receipt.  A crash may be resumed only
                # after a newly qualified process produces a fresh receipt.
                "a10_live_server_stable_identity": {
                    "served_model_id": a10_launch["served_model_id"],
                    "model_realpath": a10_launch["model_realpath"],
                    "model_manifest_sha256": a10_launch["model_manifest_sha256"],
                    "port": a10_launch["port"],
                    "packages": a10_launch["packages"],
                },
                "task_order": "blocking_A0_4_task_gate_then_frozen_manifest_remainder",
                "reward_fail_fast": True,
                "scientific_failure_rerun": False,
                "A0_preservation_tasks": list(A0_PRESERVATION_TASKS),
                "A0_preservation_required_for_continuation": True,
                "controller_authored_memory": True,
                "response_prefix_required": False,
                "official_system_prompt_unchanged": True,
                "extra_model_calls": 0,
                "guard": False,
                "action_override": False,
                "forced_termination": False,
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
    suite_lifecycle_errors: list[dict] = []
    valid_entries: list[dict] = []
    a10_valid_entries: list[dict] = []
    dual_valid_entries: list[dict] = []
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
            checkpoint = (
                _load_bpr_checkpoint_pointer(suite_dir)
                if dual_arm_name == "bprv2"
                else _load_a1r3v3_checkpoint_pointer(suite_dir)
                if dual_arm_name == "a1r3v3"
                else json.loads((suite_dir / "checkpoint.json").read_text(encoding="utf-8"))
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
                    f"{dual_arm['label'] if dual_scored_arm else 'A10' if a10_scored_arm else str(args.a678_arm).upper()} capability-preservation failure is terminal and cannot be resumed"
                )
            if dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
                if checkpoint.get("status") in {
                    "stopped_preservation_gate_failure",
                    "stopped_activation_gate_failure",
                    "stopped_preservation_gate_incomplete",
                    "stopped_activation_gate_incomplete",
                }:
                    raise RuntimeError(
                        f"{dual_arm['label']} valid scientific gate failure is terminal and cannot be resumed"
                    )
                if checkpoint.get("status") == "infrastructure_incomplete":
                    raise RuntimeError(
                        f"{dual_arm['label']} exhausted its infrastructure replacement budget"
                    )
                stage = str(args.sys_trrc_stage)
                prior_required = dual_arm["contract"].stage_contract(
                    dual_arm["recovery_mode"], stage
                )["required_prior_status"]
                checkpoint_stage = checkpoint.get("sys_trrc_stage")
                continuing_same_stage = (
                    checkpoint_stage == stage
                    and checkpoint.get("status") in {"running", "stopped_invalid_episode"}
                )
                if prior_required is not None and not (
                    checkpoint.get("status") == prior_required
                    or continuing_same_stage
                ):
                    raise RuntimeError(
                        f"{dual_arm['label']} {stage} requires {prior_required}; stage skipping is forbidden"
                    )
            if (
                dual_arm_name in {"a1r13d", "a1r14", "a1r15"}
                and checkpoint.get("status")
                in {
                    "stopped_target_gate_failure",
                    "stopped_target_gate_incomplete",
                    "stopped_capability_gate_failure",
                    "stopped_capability_gate_incomplete",
                }
            ):
                raise RuntimeError(
                    f"{dual_arm['label']} target/capability gate terminal state cannot be resumed"
                )
            if enriched_diag_arm:
                expected_diag_identity = {
                    "schema": "enriched_memory_diagnostic6_checkpoint_v1",
                    "run_signature_sha256": run_signature_sha256,
                    "diagnostic_protocol_id": diag6_contract.PROTOCOL_ID,
                    "diagnostic_arm": enriched_diag_arm,
                    "experiment_id": diag6_contract.ARM_BINDINGS[enriched_diag_arm]["experiment_id"],
                    "formal_arm_status_repaired": False,
                }
                if any(checkpoint.get(key) != value for key, value in expected_diag_identity.items()):
                    raise RuntimeError("DIAG6 checkpoint identity mismatch")
                if checkpoint.get("status") == "infrastructure_incomplete":
                    raise RuntimeError("DIAG6 infrastructure-invalid attempt limit is terminal")
                summaries = list(checkpoint.get("valid_summaries") or [])
                invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
            elif dual_scored_arm:
                if (
                    dual_arm_name in {"a12", "bprv2"}
                    and checkpoint.get("status") == "infrastructure_incomplete"
                ):
                    raise RuntimeError(
                        f"{dual_arm['label']} exceeded the frozen infrastructure-invalid attempt limit; resume is forbidden"
                    )
                summaries, dual_valid_entries, invalid_attempts = _load_dual_arm_checkpoint(
                    suite_dir=suite_dir,
                    checkpoint=checkpoint,
                    run_signature_sha256=run_signature_sha256,
                    arm=dual_arm,
                )
            elif a10_scored_arm:
                summaries, a10_valid_entries, invalid_attempts = _load_a10_checkpoint(
                    suite_dir=suite_dir,
                    checkpoint=checkpoint,
                    run_signature_sha256=run_signature_sha256,
                )
            else:
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
            if enriched_diag_arm:
                payload.update(
                    {
                        "schema": "enriched_memory_diagnostic6_checkpoint_v1",
                        "run_signature_sha256": run_signature_sha256,
                        "diagnostic_protocol_id": diag6_contract.PROTOCOL_ID,
                        "diagnostic_arm": enriched_diag_arm,
                        "experiment_id": diag6_contract.ARM_BINDINGS[enriched_diag_arm]["experiment_id"],
                        "formal_arm_status_repaired": False,
                        "live_server_receipt_sha256s": sorted(
                            {
                                str((item.get("run_metadata") or {}).get("live_server_receipt_sha256"))
                                for item in summaries
                                if (item.get("run_metadata") or {}).get("live_server_receipt_sha256")
                            }
                            | {_sha256(dual_receipt_path)}
                        ),
                    }
                )
            elif dual_scored_arm:
                payload.update(
                    {
                        "run_signature_sha256": run_signature_sha256,
                        "schema": dual_arm["checkpoint_schema"],
                        "prospective_arm": dual_arm["arm"],
                        "experiment_id": dual_arm["experiment_id"],
                        "mechanism_id": dual_arm["mechanism_id"],
                        "system_id": (
                            dual_arm["contract"].SYSTEM_ID
                            if dual_arm_name == "sys_nag"
                            else None
                        ),
                        "sys_trrc_stage": args.sys_trrc_stage if sys_trrc_arm else None,
                        dual_arm["entry_key"]: dual_valid_entries,
                        "live_server_receipt_sha256s": sorted(
                            {
                                str((item.get("run_metadata") or {}).get("live_server_receipt_sha256"))
                                for item in summaries
                                if (item.get("run_metadata") or {}).get("live_server_receipt_sha256")
                            }
                            | {_sha256(dual_receipt_path)}
                        ),
                    }
                )
                if sys_trrc_arm:
                    payload["lifecycle_errors"] = list(suite_lifecycle_errors)
            elif a10_scored_arm:
                payload.update(
                    {
                        "run_signature_sha256": run_signature_sha256,
                        "a10_valid_entries": a10_valid_entries,
                        "live_server_receipt_sha256s": sorted(
                            {
                                str((item.get("run_metadata") or {}).get("live_server_receipt_sha256"))
                                for item in summaries
                                if (item.get("run_metadata") or {}).get("live_server_receipt_sha256")
                            }
                            | {_sha256(args.a10_launch_receipt)}
                        ),
                    }
                )
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
            elif dual_arm_name == "bprv2":
                payload["capability_gate"] = dual_arm["preservation_report"](summaries)
                payload["gate5"] = dual_arm["contract"].gate5_report(summaries)
            elif prospective_gate_arm:
                payload["capability_gate"] = (
                    dual_arm["preservation_report"](summaries)
                    if dual_scored_arm
                    else a10_preservation_report(summaries)
                    if a10_scored_arm
                    else a7_gate_report(summaries)
                )
            elif a89_four_task_diagnostic:
                payload.update(
                    {
                        "claim_boundary": A89_DIAGNOSTIC_CLAIM_BOUNDARY,
                        "four_task_diagnostic": a89_diagnostic_report(summaries),
                    }
                )
        if sys_trrc_arm or dual_arm_name in {"sys_nag", "a1r13", "a1r13d", "a1r14", "a1r15"}:
            payload["content_sha256"] = dual_arm["contract"].content_sha256(payload)
        if dual_arm_name == "bprv2":
            _append_bpr_checkpoint(suite_dir, payload)
        elif dual_arm_name == "a1r3v3":
            _append_a1r3v3_checkpoint(suite_dir, payload)
        else:
            _atomic_json(suite_dir / "checkpoint.json", payload)
        if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}:
            completed = {str(item.get("task_name")): item for item in summaries}
            task_rows = []
            for expected_task in dual_arm["contract"].FULL_TASK_ORDER:
                item = completed.get(expected_task)
                task_rows.append(
                    {
                        "task_name": expected_task,
                        "seed": dual_arm["contract"].TASK_SEED,
                        "execution_status": (
                            "VALID_SUCCESS"
                            if item and item.get("success")
                            else "VALID_SCIENTIFIC_FAILURE"
                            if item
                            else "NOT_RUN_BY_PROTOCOL"
                        ),
                        "episode_id": item.get("episode_id") if item else None,
                        "reward": item.get("evaluator_reward") if item else None,
                        "success": item.get("success") if item else None,
                    }
                )
            terminal = status.startswith("stopped_") or status == "infrastructure_incomplete"
            formal_payload = {
                "schema": dual_arm["result_schema"],
                "status": (
                    "COMPLETE" if status == "complete"
                    else f"TERMINAL_{status.upper()}" if terminal
                    else "RUNNING_PARTIAL"
                ),
                "source_checkpoint_status": status,
                "identity": {
                    "suite_id": suite_id,
                    "mechanism_id": dual_arm["mechanism_id"],
                    "experiment_id": dual_arm["experiment_id"],
                    "implementation_commit": dual_preflight.get("implementation_commit"),
                    "run_signature_sha256": run_signature_sha256,
                },
                "closure": {
                    "valid_episode_count": len(summaries),
                    "invalid_attempt_count": len(invalid_attempts),
                    "not_run_by_protocol_count": sum(
                        row["execution_status"] == "NOT_RUN_BY_PROTOCOL"
                        for row in task_rows
                    ),
                    "checkpoint_content_sha256": payload.get("content_sha256"),
                },
                "capability_gate": dual_arm["preservation_report"](summaries),
                "target_gate": dual_arm["contract"].target_gate_report(summaries),
                "performance": {
                    "success_count": sum(int(bool(item.get("success"))) for item in summaries),
                    "reward_sum": sum(float(item.get("evaluator_reward") or 0.0) for item in summaries),
                    "model_calls": sum(int(item.get("model_call_count") or 0) for item in summaries),
                    "executed_actions": sum(int(item.get("executed_action_count") or 0) for item in summaries),
                },
                "tasks": task_rows,
                "invalid_attempts": list(invalid_attempts),
                "errors": [],
            }
            formal_payload["content_sha256"] = dual_arm["contract"].content_sha256(
                formal_payload
            )
            _atomic_json(
                suite_dir / (
                    "a1r15_result.json"
                    if dual_arm_name == "a1r15"
                    else "a1r14_result.json"
                    if dual_arm_name == "a1r14"
                    else "a1r13d_result.json"
                    if dual_arm_name == "a1r13d"
                    else "a1r13_result.json"
                ),
                formal_payload,
            )
        if dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
            checkpoint_path = suite_dir / "checkpoint.json"
            if status == "complete":
                formal_status = "COMPLETE"
            elif status == "control_complete":
                formal_status = "CONTROL_COMPLETE"
            elif status.startswith("stage_") and status.endswith("_complete"):
                formal_status = status.upper()
            elif "gate" in status or status.startswith("stopped_scientific"):
                formal_status = f"TERMINAL_SCIENTIFIC_FAILURE_{status.upper()}"
            elif status in {"infrastructure_incomplete", "stopped_invalid_episode"}:
                formal_status = f"INFRASTRUCTURE_{status.upper()}"
            else:
                formal_status = "RUNNING_PARTIAL"
            formal = dual_arm["contract"].result_payload(
                mode=dual_arm["recovery_mode"], status=formal_status,
                summaries=summaries, invalid_attempts=invalid_attempts,
                lifecycle_errors=suite_lifecycle_errors,
                run_signature_sha256=run_signature_sha256,
                preflight=dual_preflight,
                preflight_file_sha256=_sha256(dual_preflight_path),
                receipt_file_sha256s=sorted(
                    {
                        str((item.get("run_metadata") or {}).get("live_server_receipt_sha256"))
                        for item in summaries
                        if (item.get("run_metadata") or {}).get("live_server_receipt_sha256")
                    }
                    | {_sha256(dual_receipt_path)}
                ),
                checkpoint_sha256=_sha256(checkpoint_path),
                campaign_stage=str(args.sys_trrc_stage),
            )
            sys_result_path = suite_dir / "sys_trrc_result.json"
            _atomic_json(sys_result_path, formal)
            dual_arm["contract"].validate_result_payload(
                json.loads(sys_result_path.read_text(encoding="utf-8")),
                mode=dual_arm["recovery_mode"], checkpoint_path=checkpoint_path,
                run_signature_sha256=run_signature_sha256, preflight=dual_preflight,
                preflight_path=dual_preflight_path,
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
            args.a2_verified_progress_memory
            or a345_scored_arm
            or a678_memory_arm
            or a10_scored_arm
            or dual_memory_arm
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
    active_exception: BaseException | None = None
    try:
        for spec in specs:
            task_name = str(spec["task_class"])
            episode_seed = int(spec["task_seed"])
            if (task_name, episode_seed) in completed_keys:
                continue
            if dual_arm_name == "bprv2" and bpr_mode == "primary" and task_name not in A0_PRESERVATION_TASKS:
                gate = dual_arm["preservation_report"](summaries)
                if not _gate_passed(gate):
                    checkpoint("stopped_capability_gate_incomplete")
                    raise RuntimeError(
                        "BPR-v2 Recipe and remaining tasks are locked until the A0 gate is 4/4"
                    )
                if task_name != dual_arm["contract"].RECIPE_TASK:
                    gate5 = dual_arm["contract"].gate5_report(summaries)
                    if not _gate_passed(gate5):
                        checkpoint("stopped_gate5_incomplete")
                        raise RuntimeError("BPR-v2 remaining fourteen tasks are locked until Gate5 is 5/5")
            elif dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
                pass  # Stage progression, not within-stage outcome, authorizes tasks.
            elif dual_arm_name in {"a1r13d", "a1r14", "a1r15"}:
                target_passed = _gate_passed(
                    dual_arm["contract"].target_gate_report(summaries)
                )
                if task_name != dual_arm["contract"].TARGET_GATE_TASK and not target_passed:
                    checkpoint("stopped_target_gate_incomplete")
                    raise RuntimeError(
                        f"{dual_arm['label']} tasks after Browser are locked until its target gate passes"
                    )
                if (
                    task_name not in dual_arm["gate_tasks"]
                    and task_name != dual_arm["contract"].TARGET_GATE_TASK
                    and not _gate_passed(dual_arm["preservation_report"](summaries))
                ):
                    checkpoint("stopped_capability_gate_incomplete")
                    raise RuntimeError(
                        f"{dual_arm['label']} remaining twelve tasks are locked until its six-task preservation gate passes"
                    )
            elif dual_arm_name in {"a1r2", "a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13"} or dual_arm_name == "sys_nag":
                if task_name not in dual_arm["gate_tasks"]:
                    gate = dual_arm["preservation_report"](summaries)
                    if not _gate_passed(gate):
                        checkpoint("stopped_capability_gate_incomplete")
                        raise RuntimeError(
                            f"{dual_arm['label']} remaining tasks are locked until "
                            f"its capability gate is {len(dual_arm['gate_tasks'])}/{len(dual_arm['gate_tasks'])}"
                        )
                    if (
                        dual_arm_name == "a1r13"
                        and task_name != dual_arm["contract"].TARGET_GATE_TASK
                        and not _gate_passed(
                            dual_arm["contract"].target_gate_report(summaries)
                        )
                    ):
                        checkpoint("stopped_target_gate_incomplete")
                        raise RuntimeError(
                            "A1-R13 remaining tasks are locked until the Browser target gate passes"
                        )
            elif (
                (a7_gated_continuation or prospective_gate_arm)
                and task_name not in A0_PRESERVATION_TASKS
            ):
                gate = (
                    dual_arm["preservation_report"](summaries)
                    if dual_scored_arm
                    else a10_preservation_report(summaries)
                    if a10_scored_arm
                    else a7_gate_report(summaries)
                )
                if not _gate_passed(gate):
                    checkpoint("stopped_capability_gate_incomplete")
                    raise RuntimeError(
                        f"{dual_arm['label'] if dual_scored_arm else 'A10' if a10_scored_arm else str(args.a678_arm).upper()} remaining tasks are locked until the A0 preservation gate is 4/4"
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
            recovery_policy = None
            answer_consistency_guard = None
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
            elif a10_scored_arm:
                a678_memory = EvidenceCalibratedObligationBranchFrontierMemory(
                    max_anchors=8,
                    max_anchor_events=6,
                    max_frontiers=16,
                    max_branches_per_frontier=5,
                    max_attempt_receipts=32,
                    max_pending_routes=4,
                    max_escape_watches=2,
                    max_trigger_candidates=8,
                    max_nonempty_reads=5,
                    max_reads_per_phase=2,
                    read_cooldown_steps=4,
                    max_chars=420,
                    max_utf8_bytes=720,
                )
            elif dual_memory_arm:
                # A fresh instance per episode; state is never shared across
                # tasks and prospective arms can never be composed.
                if dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
                    a678_memory = dual_arm["memory_class_object"](
                        ttl_requests=8, max_render_chars=1100
                    )
                    if dual_arm["recovery_mode"] != "base":
                        from raven_m.official_qwen_mobile.sys_trrc_recovery import (
                            OneShotTriggeredRecoveryPolicy,
                        )
                        recovery_policy = OneShotTriggeredRecoveryPolicy(
                            mode=dual_arm["recovery_mode"],
                            token_projector=sys_trrc_token_projector,
                            text_delta_counter=sys_trrc_text_delta_counter,
                        )
                elif dual_arm_name == "bprv2":
                    a678_memory = dual_arm["memory_class_object"](
                        read_enabled=dual_arm["read_enabled"]
                    )
                elif dual_arm_name == "a1r3v3":
                    config = json.loads(
                        dual_arm["config_path"].read_text(encoding="utf-8")
                    )
                    memory_config = config.get("memory") or {}
                    expected = {
                        "parent_ttl_requests": 8,
                        "max_render_chars": 1200,
                        "no_progress_pixel_fraction": 0.001,
                        "consecutive_supports": 2,
                        "max_receipt_creations": 1,
                        "max_receipt_committed_reads": 1,
                        "receipt_render_mode": "enabled",
                    }
                    if any(memory_config.get(key) != value for key, value in expected.items()):
                        raise RuntimeError("A1-R3-v3 runtime config drift")
                    a678_memory = dual_arm["memory_class_object"](
                        ttl_requests=8,
                        max_render_chars=1200,
                        receipt_render_mode="enabled",
                    )
                elif dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}:
                    config = json.loads(
                        dual_arm["config_path"].read_text(encoding="utf-8")
                    )
                    if config != dual_arm["contract"].EXPECTED_CONFIG:
                        raise RuntimeError("A1-R13 runtime config drift")
                    a678_memory = dual_arm["memory_class_object"](
                        ttl_requests=8,
                        max_render_chars=1100,
                        evidence_ttl_requests=8,
                        max_evidence_values=6,
                        min_values_to_render=2,
                    )
                else:
                    a678_memory = dual_arm["memory_class_object"]()
            if dual_arm_name == "sys_nag":
                from raven_m.official_qwen_mobile.numeric_answer_guard import (
                    NumericAnswerConsistencyGuard,
                )
                answer_consistency_guard = NumericAnswerConsistencyGuard()
            controller = OfficialQwenMobileController(
                client,
                max_steps=effective_limit,
                max_tokens=args.max_tokens,
                run_metadata={
                    "run_stage": args.run_stage,
                    "diagnostic": bool(args.diagnostic),
                    "diagnostic_protocol_id": (
                        diag6_contract.PROTOCOL_ID if enriched_diag_arm else None
                    ),
                    "diagnostic_arm": enriched_diag_arm,
                    "formal_arm_status_repaired": False if enriched_diag_arm else None,
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
                            _sha256(args.a10_launch_receipt)
                            if a10_scored_arm
                            else (
                                _sha256(dual_receipt_path)
                                if dual_memory_arm
                                else (
                                    _sha256(args.a678_launch_receipt)
                                    if a678_memory_arm else None
                                )
                            )
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
                            if (a345_scored_arm or controller_memory_arm)
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
                    A1R1_BPR_V2_SYSTEM_PROMPT
                    if dual_arm_name == "bprv2"
                    else A1_WORKING_MEMORY_SYSTEM_PROMPT
                    if dual_arm_name in {"a1r2", "a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15", "sys_nag"} or (dual_arm_name and dual_arm_name.startswith("sys_trrc_"))
                    else A1_WORKING_MEMORY_SYSTEM_PROMPT
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
                    if controller_memory_arm
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
                recovery_policy=recovery_policy,
                answer_consistency_guard=answer_consistency_guard,
            )
            episode_id = f"{task_name}_{episode_seed}_{uuid4().hex[:8]}"
            result = controller.run(
                env=env,
                task=task,
                episode_id=episode_id,
                episode_dir=suite_dir / "episodes" / episode_id,
                seed=episode_seed,
            )
            if sys_trrc_arm and dual_arm["recovery_mode"] == "base":
                # Base deliberately has no recovery policy.  The controller's
                # legacy no-policy path omits split call/cost fields, so seal
                # explicit zero-recovery accounting before validity and hashes.
                normal_calls = int(result.get("model_call_count") or 0)
                result.update({
                    "normal_decision_call_count": normal_calls,
                    "aux_recovery_call_count": 0,
                    "model_call_breakdown": {
                        "normal_decision": normal_calls,
                        "aux_recovery": 0,
                        "total": normal_calls,
                    },
                    "auxiliary_model_call_attempts": [],
                    "recovery_detector_cpu_seconds": 0.0,
                    "recovery_projection_cpu_seconds": 0.0,
                })
                _atomic_json(
                    suite_dir / "episodes" / episode_id / "episode.json",
                    result,
                )
            if not _episode_infrastructure_valid(
                result,
                require_single_transport=(a10_scored_arm or dual_memory_arm),
            ):
                invalid_episode_path = (
                    suite_dir / "episodes" / episode_id / "episode.json"
                )
                invalid_attempt = {
                    "episode_id": episode_id,
                    "task_name": task_name,
                    "seed": episode_seed,
                    "reason": "controller_or_lifecycle_invalid",
                    "error": result.get("error"),
                    "lifecycle_errors": result.get("lifecycle_errors"),
                }
                if sys_trrc_arm:
                    if not invalid_episode_path.is_file():
                        _atomic_json(invalid_episode_path, result)
                    invalid_attempt["artifact"] = {
                        "episode_json_sha256": _sha256(invalid_episode_path),
                        "summary_sha256": _json_digest(result),
                        "model_call_count": int(result.get("model_call_count") or 0),
                        "normal_decision_call_count": int(
                            result.get("normal_decision_call_count") or 0
                        ),
                        "aux_recovery_call_count": int(
                            result.get("aux_recovery_call_count") or 0
                        ),
                    }
                invalid_attempts.append(invalid_attempt)
                same_task_invalid_count = sum(
                    int(
                        str(attempt.get("task_name")) == task_name
                        and int(attempt.get("seed", -1)) == episode_seed
                    )
                    for attempt in invalid_attempts
                )
                bpr_arm_invalid_count = sum(
                    int(attempt.get("reason") == "controller_or_lifecycle_invalid")
                    for attempt in invalid_attempts
                )
                attempt_limit_exceeded = bool(
                    ((dual_arm_name == "bprv2" and bpr_arm_invalid_count > 2)
                    or (
                        (dual_arm_name == "a1r3v3" or (dual_arm_name and dual_arm_name.startswith("sys_trrc_")))
                        and (
                            same_task_invalid_count > 1
                            or (
                                len(invalid_attempts) > 2
                                if sys_trrc_arm
                                else bpr_arm_invalid_count > 2
                            )
                        )
                    )
                    or ((dual_arm_name == "a12" or enriched_diag_arm) and same_task_invalid_count > 2))
                )
                checkpoint(
                    "infrastructure_incomplete"
                    if attempt_limit_exceeded
                    else "stopped_invalid_episode"
                )
                if attempt_limit_exceeded:
                    raise RuntimeError(
                        f"{('DIAG6 ' + str(enriched_diag_arm)) if enriched_diag_arm else dual_arm['label']} "
                        f"task {task_name} exceeded its frozen infrastructure-invalid "
                        "replacement budget; the suite is terminally infrastructure-incomplete"
                    )
                raise RuntimeError(
                    f"Memory run stopped after infrastructure-invalid episode {episode_id}; "
                    "resume will rerun only this task"
                )
            resolved_invalid_ids = [
                str(attempt.get("episode_id"))
                for attempt in invalid_attempts
                if (
                    str(attempt.get("task_name")) == task_name
                    and int(attempt.get("seed", -1)) == episode_seed
                    and not attempt.get("resolved_by_episode_id")
                )
            ]
            if resolved_invalid_ids:
                result["resolves_invalid_episode_id"] = resolved_invalid_ids[-1]
                result["resolves_invalid_episode_ids"] = resolved_invalid_ids
            for attempt in invalid_attempts:
                if (
                    str(attempt.get("task_name")) == task_name
                    and int(attempt.get("seed", -1)) == episode_seed
                    and not attempt.get("resolved_by_episode_id")
                ):
                    attempt["resolved_by_episode_id"] = episode_id
            if a10_scored_arm or dual_memory_arm:
                _atomic_json(
                    suite_dir / "episodes" / episode_id / "episode.json",
                    result,
                )
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
            elif a10_scored_arm:
                a10_valid_entries.append(
                    _a10_episode_entry(
                        suite_dir=suite_dir,
                        summary=result,
                        run_signature_sha256=run_signature_sha256,
                    )
                )
            elif dual_scored_arm:
                dual_valid_entries.append(
                    _a10_episode_entry(
                        suite_dir=suite_dir,
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
                and (
                    not bool(result.get("success"))
                    or (
                        dual_arm_name == "a12"
                        and (
                            _memory_protocol_violation(result)
                            or _a12_memory_record_mismatch(result)
                        )
                    )
                )
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"{dual_arm['label'] if dual_scored_arm else 'A10' if a10_scored_arm else str(args.a678_arm).upper()} capability-preservation gate failed on "
                    f"{task_name}; scientific failures are terminal and cannot be rerun"
                )
            if (
                dual_arm_name == "bprv2"
                and bpr_mode == "primary"
                and task_name == dual_arm["contract"].RECIPE_TASK
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_gate5_failure")
                raise RuntimeError(
                    "BPR-v2 Recipe gain-preservation gate failed; scientific failure is terminal"
                )
            if (
                dual_arm_name == "a1r2"
                and task_name == dual_arm["contract"].RECIPE_TASK
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_gate5_failure")
                raise RuntimeError(
                    "A1-R2 Recipe gain-preservation gate failed; scientific failure is terminal"
                )
            if (
                dual_arm_name and dual_arm_name.startswith("sys_trrc_")
                and dual_arm["recovery_mode"] == "full"
                and task_name in dual_arm["contract"].PRESERVATION_TASKS
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_preservation_gate_failure")
                raise RuntimeError(
                    f"{dual_arm['label']} preservation failed on {task_name}; "
                    "valid scientific failure is terminal and cannot be rerun"
                )
            if (
                dual_arm_name and dual_arm_name.startswith("sys_trrc_")
                and dual_arm["recovery_mode"] == "full"
                and task_name == dual_arm["contract"].ACTIVATION_TASK
                and not _gate_passed(dual_arm["contract"].activation_report(
                    summaries, dual_arm["recovery_mode"]
                ))
            ):
                checkpoint("stopped_activation_gate_failure")
                raise RuntimeError(
                    f"{dual_arm['label']} BrowserMultiply activation gate failed; "
                    "valid scientific failure is terminal and cannot be rerun"
                )
            if (
                dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}
                and task_name in dual_arm["gate_tasks"]
                and (
                    not bool(result.get("success"))
                    or int(
                        (((result.get("memory_mechanism") or {}).get("evidence_register") or {}).get("counters") or {}).get("activation_count")
                        or 0
                    )
                    or int(
                        (((result.get("memory_mechanism") or {}).get("evidence_register") or {}).get("counters") or {}).get("render_count")
                        or 0
                    )
                )
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"{dual_arm['label']} six-task capability/silence gate failed on {task_name}; "
                    "scientific failure is terminal"
                )
            if (
                dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}
                and task_name == dual_arm["contract"].TARGET_GATE_TASK
                and not _gate_passed(dual_arm["contract"].target_gate_report(summaries))
            ):
                checkpoint("stopped_target_gate_failure")
                raise RuntimeError(
                    (
                        "A1-R13D Browser target gate failed; scientific failure is terminal"
                        if dual_arm_name == "a1r13d"
                        else "A1-R15 Browser target gate failed; scientific failure is terminal"
                        if dual_arm_name == "a1r15"
                        else "A1-R14 Browser target gate failed; scientific failure is terminal"
                        if dual_arm_name == "a1r14"
                        else "A1-R13 Browser target gate failed; scientific failure is terminal"
                    )
                )
            if (
                dual_arm_name == "a1r12" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure");raise RuntimeError(f"A1-R12 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "sys_nag"
                and task_name in dual_arm["gate_tasks"]
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"SYS-NAG six-task capability gate failed on {task_name}; "
                    "scientific failure is terminal"
                )
            if (
                dual_arm_name == "a1r11" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure");raise RuntimeError(f"A1-R11 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r10" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure");raise RuntimeError(f"A1-R10 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r9" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure");raise RuntimeError(f"A1-R9 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r8" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure");raise RuntimeError(f"A1-R8 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r7" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure"); raise RuntimeError(f"A1-R7 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r6" and task_name in dual_arm["gate_tasks"] and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(f"A1-R6 six-task capability gate failed on {task_name}; scientific failure is terminal")
            if (
                dual_arm_name == "a1r5"
                and task_name in dual_arm["gate_tasks"]
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"A1-R5 six-task capability gate failed on {task_name}; "
                    "scientific failure is terminal"
                )
            if (
                dual_arm_name == "a1r4"
                and task_name in dual_arm["gate_tasks"]
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"A1-R4 six-task capability gate failed on {task_name}; "
                    "scientific failure is terminal"
                )
            if (
                dual_arm_name == "a1r3v3"
                and task_name in dual_arm["gate_tasks"]
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"A1-R3-v3 six-task capability gate failed on {task_name}; "
                    "scientific failure is terminal"
                )
            if (
                dual_arm_name == "a1r3"
                and task_name in dual_arm["gate_tasks"]
                and not bool(result.get("success"))
            ):
                checkpoint("stopped_capability_gate_failure")
                raise RuntimeError(
                    f"A1-R3 six-task capability gate failed on {task_name}; "
                    "scientific failure is terminal"
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
            checkpoint(
                "infrastructure_incomplete"
                if dual_arm_name in {"a12", "bprv2", "a1r2", "a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15"}
                or (sys_trrc_arm and len(invalid_attempts) > 2)
                else "stopped_invalid_episode"
            )
            if active_exception is None:
                raise
        else:
            for attempt in invalid_attempts:
                if (
                    attempt.get("reason") == "suite_lifecycle_error"
                    and not attempt.get("resolved_by_episode_id")
                ):
                    attempt["resolved_by_episode_id"] = "suite_close_success_on_resume"

    if sys_trrc_arm:
        mode = dual_arm["recovery_mode"]
        stage = str(args.sys_trrc_stage)
        stage_closure = dual_arm["contract"].stage_contract(mode, stage)
        expected_stage_order = stage_closure["tasks"]
        observed_order = tuple(str(item.get("task_name")) for item in summaries)
        if observed_order != tuple(expected_stage_order):
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(
                f"{dual_arm['label']} {stage} exact stage closure failed: {observed_order}"
            )
        if mode in {"base", "detector"}:
            checkpoint(stage_closure["completion_status"])
            result = json.loads((suite_dir / "sys_trrc_result.json").read_text(encoding="utf-8"))
            print(json.dumps({"suite_dir": str(suite_dir), "sys_trrc_result": result}, indent=2, ensure_ascii=False))
            return
        if stage != "l4":
            checkpoint(stage_closure["completion_status"])
            result = json.loads((suite_dir / "sys_trrc_result.json").read_text(encoding="utf-8"))
            print(json.dumps({"suite_dir": str(suite_dir), "sys_trrc_result": result}, indent=2, ensure_ascii=False))
            return

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
    if dual_scored_arm:
        gate = dual_arm["preservation_report"](summaries)
        if (dual_arm_name != "bprv2" or bpr_mode == "primary") and not (
            sys_trrc_arm and dual_arm["recovery_mode"] == "generic"
        ):
            if not _gate_passed(gate):
                checkpoint("stopped_capability_gate_incomplete")
                raise RuntimeError(
                    f"{dual_arm['label']} cannot aggregate before its blocking "
                    f"{len(dual_arm['gate_tasks'])}/{len(dual_arm['gate_tasks'])} capability gate passes"
                )
        if sys_trrc_arm and dual_arm["recovery_mode"] == "full":
            activation = dual_arm["contract"].activation_report(
                summaries, dual_arm["recovery_mode"]
            )
            if not _gate_passed(activation):
                checkpoint("stopped_activation_gate_incomplete")
                raise RuntimeError(
                    f"{dual_arm['label']} cannot aggregate before BrowserMultiply activation passes"
                )
        if dual_arm_name == "bprv2" and bpr_mode == "primary":
            gate5 = dual_arm["contract"].gate5_report(summaries)
            if not _gate_passed(gate5):
                checkpoint("stopped_gate5_incomplete")
                raise RuntimeError("BPR-v2 primary cannot aggregate before Gate5 is 5/5")
        completion_kwargs = {
            "summaries": summaries,
            "invalid_attempts": invalid_attempts,
            "lifecycle_errors": suite_lifecycle_errors,
        }
        if dual_arm_name == "bprv2":
            completion_kwargs["expected_count"] = dual_arm["expected_count"]
        if dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
            completion_kwargs["mode"] = dual_arm["recovery_mode"]
        closure_errors = dual_arm["completion_errors"](**completion_kwargs)
        if closure_errors:
            checkpoint(
                "infrastructure_incomplete"
                if dual_arm_name in {"a12", "bprv2"}
                else "stopped_incomplete_or_invalid"
            )
            raise RuntimeError(
                f"{dual_arm['label']} cannot aggregate: {closure_errors}"
            )
    if a10_scored_arm:
        gate = a10_preservation_report(summaries)
        if gate["status"] != "pass":
            checkpoint("stopped_capability_gate_incomplete")
            raise RuntimeError("A10 cannot aggregate before the blocking 4/4 preservation gate passes")
        closure_errors = a10_completion_errors(
            summaries=summaries,
            invalid_attempts=invalid_attempts,
            lifecycle_errors=suite_lifecycle_errors,
        )
        if closure_errors:
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(f"A10 cannot aggregate: {closure_errors}")
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
    if enriched_diag_arm:
        closure_errors = _diag6_completion_errors(
            summaries, invalid_attempts, suite_lifecycle_errors
        )
        if closure_errors:
            checkpoint("stopped_incomplete_or_invalid")
            raise RuntimeError(
                f"DIAG6 {enriched_diag_arm} cannot aggregate: {closure_errors}"
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
                if (a345_scored_arm or controller_memory_arm)
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
                dual_arm["preservation_report"](summaries)
                if dual_scored_arm
                else a10_preservation_report(summaries)
                if a10_scored_arm
                else a7_gate_report(summaries)
                if (a7_gated_continuation or prospective_gate_arm)
                else a678_preservation_report(summaries)
            )
            if (a678_scored_arm or a10_scored_arm or dual_scored_arm)
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
            int((call.get("raven_meta") or {}).get("transport_attempts") or 0)
            for item in summaries for call in _all_model_call_audits(item)
        ),
        "transport_attempt_max": max(
            [int((call.get("raven_meta") or {}).get("transport_attempts") or 0)
             for item in summaries for call in _all_model_call_audits(item)] or [0]
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
                "memory_active": bool((item.get("memory_mechanism") or {}).get("active")),
                "memory_trigger_count": int((item.get("memory_mechanism") or {}).get("trigger_count") or 0),
                "memory_nonempty_read_count": int((item.get("memory_mechanism") or {}).get("nonempty_read_count") or 0),
                "first_nonempty_read_step": (
                    (((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or [{}])[0].get("step")
                    if (((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events"))
                    else None
                ),
                "memory_rendered_chars": int((item.get("memory_mechanism") or {}).get("rendered_chars_total") or 0),
                "phase_switch_count": int((((item.get("memory_mechanism") or {}).get("phase") or {}).get("phase_switch_count")) or 0),
                "frontier_eviction_count": int((((item.get("memory_mechanism") or {}).get("frontiers") or {}).get("eviction_count")) or 0),
                "model_calls_added": int((item.get("memory_mechanism") or {}).get("model_calls_added") or 0),
                "action_override_count": int((item.get("memory_mechanism") or {}).get("action_override_count") or 0),
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
    if enriched_diag_arm:
        reference_path = REPOSITORY_ROOT / "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json"
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        causal_records = _diag6_causal_read_analysis(enriched_diag_arm, summaries)
        active_episode_count = sum(int(_memory_active(item)) for item in summaries)
        nonempty_read_count = len(causal_records)
        productive_count = sum(
            int(item.get("productive_divergence_hypothesis") is True)
            for item in causal_records
        )
        diagnostically_active = active_episode_count >= 3 and nonempty_read_count >= 3
        productive_signal = productive_count >= 2
        if not diagnostically_active:
            scientific_label = "insufficient_diagnostic_activation"
        elif productive_signal:
            scientific_label = "productive_divergence_signal_observed"
        else:
            scientific_label = "activation_without_productive_divergence_signal"
        aggregate["enriched_memory_diagnostic6_result"] = {
            "schema": "enriched_memory_diagnostic6_result_v1",
            "protocol_id": diag6_contract.PROTOCOL_ID,
            "diagnostic_arm": enriched_diag_arm,
            "experiment_id": diag6_contract.ARM_BINDINGS[enriched_diag_arm]["experiment_id"],
            "source_mechanism_id": diag6_contract.ARM_BINDINGS[enriched_diag_arm]["source_mechanism_id"],
            "selection_rule": "post_hoc_common_memory_opportunity_enrichment",
            "held_out_eligible": False,
            "formal_arm_status_repaired": False,
            "task_order": list(diag6_contract.TASKS),
            "valid_episode_count": len(summaries),
            "success_count": sum(int(bool(item.get("success"))) for item in summaries),
            "reward_sum": sum(float(item.get("evaluator_reward") or 0) for item in summaries),
            "active_episode_count": active_episode_count,
            "actual_nonempty_read_count": nonempty_read_count,
            "productive_divergence_hypothesis_count": productive_count,
            "diagnostically_active": diagnostically_active,
            "productive_divergence_signal": productive_signal,
            "scientific_label": scientific_label,
            "pairwise": {
                "reference_sha256": _sha256(reference_path),
                "versus_a0": _diag6_pairwise(summaries, "A0", reference),
                "versus_a1": _diag6_pairwise(summaries, "A1", reference),
            },
            "intervention_boundary": {
                "model_calls_added": 0,
                "guard_enabled": False,
                "action_override_count": 0,
                "forced_termination_count": 0,
                "protocol_violation": any(_memory_protocol_violation(item) for item in summaries),
            },
            "causal_read_records": causal_records,
            "episodes": [
                {
                    "task_name": item["task_name"],
                    "episode_id": item["episode_id"],
                    "reward": item["evaluator_reward"],
                    "success": item["success"],
                    "memory_active": _memory_active(item),
                    "nonempty_read_count": sum(
                        int(str(record.get("episode", record.get("episode_id"))) == str(item["episode_id"]))
                        for record in causal_records
                    ),
                    "model_calls": item["model_call_count"],
                    "executed_actions": item["executed_action_count"],
                    "token_usage": _usage_totals([item]),
                }
                for item in summaries
            ],
            "errors": [],
        }
    if dual_arm_name == "bprv2":
        bpr_counters: dict[str, int] = {}
        for summary in summaries:
            for key, value in ((summary.get("memory_mechanism") or {}).get("counters") or {}).items():
                if isinstance(value, int):
                    bpr_counters[key] = bpr_counters.get(key, 0) + value
        bpr_result = {
            "schema": dual_arm["result_schema"],
            "arm": bpr_mode,
            "mechanism_id": dual_arm["mechanism_id"],
            "experiment_id": dual_arm["experiment_id"],
            "implementation_commit": dual_preflight.get("implementation_commit"),
            "source_freeze_content_sha256": dual_preflight.get("source_freeze_content_sha256"),
            "preflight_file_sha256": _sha256(dual_preflight_path),
            "live_receipt_file_sha256": _sha256(dual_receipt_path),
            "primary_result_sha256": (
                _sha256(args.a1r1_bpr_v2_primary_result) if bpr_mode == "empty_read" else None
            ),
            "completion_status": "COMPLETE_19" if bpr_mode == "primary" else "COMPLETE_5_EMPTY_READ",
            "valid_episode_count": len(summaries),
            "invalid_attempt_count": len(invalid_attempts),
            "success_count": aggregate["success_count"],
            "reward_sum": sum(float(item.get("evaluator_reward") or 0) for item in summaries),
            "gate4": dual_arm["preservation_report"](summaries),
            "gate5": (
                dual_arm["contract"].gate5_report(summaries)
                if bpr_mode == "primary" else None
            ),
            "accuracy_verdict": (
                "PASS" if bpr_mode == "primary" and aggregate["success_count"] >= 6
                else "FAIL" if bpr_mode == "primary" else "NOT_APPLICABLE_ABLATION"
            ),
            "cost_verdict": (
                "PASS" if bpr_mode == "primary"
                and aggregate["total_model_calls"] < 603
                and int(aggregate["token_usage"]["total_tokens"]) < 3464267
                and float(aggregate["exact_valid_elapsed_seconds"]) < 14595.492
                else "FAIL" if bpr_mode == "primary" else "NOT_APPLICABLE_ABLATION"
            ),
            "mechanism_verdict": (
                "MECHANISM_PENDING_ABLATION" if bpr_mode == "primary" else "PENDING_CAUSAL_ADJUDICATION"
            ),
            "counters": bpr_counters,
            "ordered_tasks": [item["task_name"] for item in summaries],
            "episode_json_sha256s": {
                item["episode_id"]: _sha256(suite_dir / "episodes" / item["episode_id"] / "episode.json")
                for item in summaries
            },
            "errors": [],
        }
        aggregate[dual_arm["result_key"]] = bpr_result
    if dual_arm_name in {"a1r2", "a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15"}:
        vertical_counters: dict[str, int] = {}
        for summary in summaries:
            for key, value in (
                ((summary.get("memory_mechanism") or {}).get("counters") or {}).items()
            ):
                if isinstance(value, int):
                    vertical_counters[key] = vertical_counters.get(key, 0) + value
        gate6 = dual_arm["preservation_report"](summaries)
        success_count = sum(int(bool(item.get("success"))) for item in summaries)
        reward_sum = sum(float(item.get("evaluator_reward") or 0.0) for item in summaries)
        calls = sum(int(item.get("model_call_count") or 0) for item in summaries)
        actions = sum(int(item.get("executed_action_count") or 0) for item in summaries)
        usage = _usage_totals(summaries)
        elapsed = sum(
            (
                datetime.fromisoformat(item["finished_at"])
                - datetime.fromisoformat(item["started_at"])
            ).total_seconds()
            for item in summaries
        )
        if dual_arm_name in {"a1r3v3", "a1r3", "a1r4", "a1r5", "a1r6", "a1r7", "a1r8", "a1r9", "a1r10", "a1r11", "a1r12", "a1r13", "a1r13d", "a1r14", "a1r15"}:
            accuracy_pass = bool(
                success_count >= 7 and reward_sum > 6.5 and _gate_passed(gate6)
            )
            cost_components = {
                "calls_not_above_a1r2": calls <= 603,
                "tokens_below_a1r2": int(usage["total_tokens"]) < 2_685_730,
                "elapsed_below_a1r2": elapsed < 11_230.182856,
            }
            if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}:
                causal_records = []
                for summary in summaries:
                    register = (
                        (summary.get("memory_mechanism") or {}).get("evidence_register")
                        or {}
                    )
                    rendered = [
                        row for row in register.get("read_events") or []
                        if row.get("rendered") is True
                    ]
                    if rendered:
                        causal_records.append(
                            {
                                "episode_id": summary.get("episode_id"),
                                "task_name": summary.get("task_name"),
                                "reward": summary.get("evaluator_reward"),
                                "success": bool(summary.get("success")),
                                "committed_evidence_read_count": len(rendered),
                                "exact_text_sha256s": [
                                    row.get("exact_text_sha256") for row in rendered
                                ],
                                "productive_signal": bool(
                                    summary.get("success")
                                    and summary.get("task_name")
                                    == dual_arm["contract"].TARGET_GATE_TASK
                                ),
                                "classification": (
                                    "TARGET_SUCCESS_ABLATION_UNRESOLVED"
                                    if summary.get("success")
                                    else "COMMITTED_READ_NO_SUCCESS"
                                ),
                            }
                        )
            else:
                causal_records = (
                    _a1r3v3_causal_analysis(summaries)
                    if dual_arm_name == "a1r3v3"
                    else _a1r3_failure_causal_analysis(summaries)
                )
            productive_count = sum(
                int(
                    item.get("productive_signal") is True
                    or item.get("classification")
                    == "QUALIFYING_NEW_WIN_ABLATION_UNRESOLVED"
                )
                for item in causal_records
            )
            failure_injection_count = sum(
                int(item.get("receipt_committed") is True)
                for item in causal_records
            ) if dual_arm_name == "a1r3v3" else len(causal_records)
            mechanism_verdict = (
                "PENDING_MATCHED_NEUTRALIZED_ABLATION"
                if dual_arm_name == "a1r3v3" and failure_injection_count
                else "NOT_OBSERVED_NO_CNR_COMMIT"
                if dual_arm_name == "a1r3v3"
                else "TARGET_SUCCESS_CANDIDATE_SUPPORT_ABLATION_UNRESOLVED"
                if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"} and productive_count >= 1
                else "TARGET_FAILED_AFTER_COMMITTED_EVIDENCE_READ"
                if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"} and failure_injection_count
                else "TARGET_EVIDENCE_NOT_OBSERVED"
                if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}
                else "PASS"
                if productive_count >= 2
                else "FAIL_INSUFFICIENT_PRODUCTIVE_FAILURE_DIVERGENCE"
                if failure_injection_count
                else "NOT_OBSERVED_NO_FAILURE_EVIDENCE_INJECTION"
            )
            accuracy_verdict = "PASS" if accuracy_pass else "FAIL"
            cost_verdict = "PASS" if all(cost_components.values()) else "FAIL"
            combined = (
                f"ACCURACY_{accuracy_verdict}_COST_{cost_verdict}_MECHANISM_{mechanism_verdict}"
            )
        else:
            accuracy_pass = bool(
                success_count >= 6 and reward_sum >= 6.5 and _gate_passed(gate6)
            )
            cost_components = {
                "calls_below_a1": calls < 603,
                "tokens_below_a1": int(usage["total_tokens"]) < 3_464_267,
                "elapsed_below_a1": elapsed < 14_595.492,
            }
            causal_records = []
            productive_count = 0
            failure_injection_count = 0
            mechanism_verdict = "NOT_ESTABLISHED_NO_MATCHED_ABLATION"
            accuracy_verdict = "PASS" if accuracy_pass else "FAIL"
            cost_verdict = "PASS" if all(cost_components.values()) else "FAIL"
            combined = (
                f"ACCURACY_{accuracy_verdict}_COST_{cost_verdict}_MECHANISM_NOT_ESTABLISHED"
            )

        pairwise_reference_path = (
            REPOSITORY_ROOT / "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json"
        )
        pairwise_reference = json.loads(pairwise_reference_path.read_text(encoding="utf-8"))
        task_rows = []
        for item in summaries:
            audit = item.get("memory_mechanism") or {}
            counters = audit.get("counters") or {}
            task_rows.append(
                {
                    "task_name": item["task_name"],
                    "seed": item["seed"],
                    "episode_id": item["episode_id"],
                    "episode_json_sha256": _sha256(
                        suite_dir / "episodes" / item["episode_id"] / "episode.json"
                    ),
                    "native_max_steps": int(
                        (item.get("run_metadata") or {})["native_max_steps"]
                    ),
                    "success": item["success"],
                    "reward": item["evaluator_reward"],
                    "termination_reason": item["termination_reason"],
                    "model_calls": item["model_call_count"],
                    "executed_actions": item["executed_action_count"],
                    "token_usage": _usage_totals([item]),
                    "elapsed_seconds": (
                        datetime.fromisoformat(item["finished_at"])
                        - datetime.fromisoformat(item["started_at"])
                    ).total_seconds(),
                    "memory_active": bool(audit.get("active")),
                    "nonempty_read_count": int(counters.get("nonempty_read_count") or 0),
                    "rendered_chars": int(counters.get("injected_chars") or 0),
                    "valid_prefix_count": int(counters.get("valid_prefix_count") or 0),
                    "same_state_nonrefresh_count": int(
                        counters.get("same_state_nonrefresh_count") or 0
                    ),
                    "failure_evidence_count": int(
                        counters.get("failure_evidence_count") or 0
                    ),
                    "failure_evidence_injection_count": sum(
                        int(
                            record.get("episode_id") == item["episode_id"]
                            and (
                                dual_arm_name != "a1r3v3"
                                or record.get("receipt_committed") is True
                            )
                        )
                        for record in causal_records
                    ),
                    "evidence_value_register": (
                        (audit.get("evidence_register") or {}).get("counters")
                        if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}
                        else None
                    ),
                }
            )
        result_payload = {
            "schema": dual_arm["result_schema"],
            "status": "COMPLETE",
            "identity": {
                "mechanism_id": dual_arm["mechanism_id"],
                "experiment_id": dual_arm["experiment_id"],
                "task_seed": dual_arm["task_seed"],
                "generation_seed": args.generation_seed,
                "implementation_commit": dual_preflight.get("implementation_commit"),
                "source_freeze_content_sha256": dual_preflight.get(
                    "source_freeze_content_sha256"
                ),
                "preflight_content_sha256": dual_preflight.get("content_sha256"),
                "preflight_file_sha256": _sha256(dual_preflight_path),
                "run_signature_sha256": run_signature_sha256,
                "live_receipt_content_sha256s": aggregate[
                    "live_server_receipt_sha256s"
                ],
                "paired_reference_sha256": _sha256(pairwise_reference_path),
            },
            "closure": {
                "status": "exact_19_closed",
                "valid_episode_count": len(summaries),
                "invalid_attempt_count": len(invalid_attempts),
                "invalid_attempts_resolved": all(
                    bool(item.get("resolved_by_episode_id")) for item in invalid_attempts
                ),
                "ordered_tasks_exact": True,
                "single_transport_per_call": aggregate["transport_attempt_max"] == 1,
            },
            "gate6": gate6,
            "target_gate": (
                dual_arm["contract"].target_gate_report(summaries)
                if dual_arm_name in {"a1r13", "a1r13d", "a1r14", "a1r15"}
                else None
            ),
            "performance": {
                "success_count": success_count,
                "reward_sum": reward_sum,
                "model_calls": calls,
                "executed_actions": actions,
                "token_usage": usage,
                "valid_elapsed_seconds": elapsed,
            },
            "verdicts": {
                "accuracy": accuracy_verdict,
                "cost": cost_verdict,
                "cost_components": cost_components,
                "mechanism": mechanism_verdict,
                "combined": combined,
            },
            "pairwise": {
                "versus_a0": _a10_pairwise(summaries, "A0", pairwise_reference),
                "versus_a1": _a10_pairwise(summaries, "A1", pairwise_reference),
            },
            "memory": {
                "active_episode_count": sum(
                    int(bool((item.get("memory_mechanism") or {}).get("active")))
                    for item in summaries
                ),
                "nonempty_read_count": int(
                    vertical_counters.get("nonempty_read_count") or 0
                ),
                "rendered_chars_total": int(vertical_counters.get("injected_chars") or 0),
                "failure_evidence_injection_count": failure_injection_count,
                "productive_failure_divergence_count": productive_count,
                "evidence_value_active_episode_count": sum(
                    int(
                        bool(
                            ((((item.get("memory_mechanism") or {}).get("evidence_register") or {}).get("counters") or {}).get("activation_count"))
                        )
                    )
                    for item in summaries
                ),
                "counters": vertical_counters,
                "decision_boundary": {
                    "extra_model_calls": 0,
                    "action_override_count": 0,
                    "forced_termination_count": 0,
                    "hidden_ui_used_for_decision": False,
                    "evaluator_used_for_decision": False,
                },
            },
            "causal_failure_injections": causal_records,
            "episodes": task_rows,
            "invalid_attempts": invalid_attempts,
            "errors": [],
        }
        aggregate[dual_arm["result_key"]] = result_payload
    if a10_scored_arm or (
        dual_scored_arm
        and dual_arm_name not in {"bprv2", "a1r2", "a1r3v3", "a1r3"}
        and dual_arm_name != "a1r4"
        and dual_arm_name != "a1r5"
        and dual_arm_name != "a1r6"
        and dual_arm_name != "a1r7"
        and dual_arm_name != "a1r8"
        and dual_arm_name != "a1r9"
        and dual_arm_name != "a1r10"
        and dual_arm_name != "a1r11"
        and dual_arm_name != "a1r12"
        and dual_arm_name != "a1r13"
        and dual_arm_name != "a1r13d"
        and dual_arm_name != "a1r14"
        and dual_arm_name != "a1r15"
    ):
        result_label = dual_arm["label"] if dual_scored_arm else "A10"
        result_prefix = result_label.upper()
        result_key = dual_arm["result_key"] if dual_scored_arm else "a10_result"
        result_schema = dual_arm["result_schema"] if dual_scored_arm else "a10_ecobf_result_v1"
        result_preflight = dual_preflight if dual_scored_arm else a10_preflight
        result_preflight_path = dual_preflight_path if dual_scored_arm else args.a10_preflight_report
        result_receipt_path = dual_receipt_path if dual_scored_arm else args.a10_launch_receipt
        result_gate = (
            dual_arm["preservation_report"](summaries)
            if dual_scored_arm
            else a10_preservation_report(summaries)
        )
        result_parent_commit = (
            dual_arm["parent_evidence_commit"]
            if dual_scored_arm
            else A10_PARENT_EVIDENCE_COMMIT
        )
        result_review_commit = (
            dual_arm.get("review_commit") or result_parent_commit
            if dual_scored_arm
            else None
        )
        result_source_freeze_sha256 = result_preflight.get(
            "source_freeze_sha256",
            result_preflight.get("source_freeze_payload_sha256"),
        )
        result_task_seed = dual_arm["task_seed"] if dual_scored_arm else A10_TASK_SEED
        implementation_commit = next(
            (
                str(result_preflight[key])
                for key in (
                    "implementation_commit",
                    "a10_v2_implementation_commit",
                    "a11_implementation_commit",
                    "a10_implementation_commit",
                )
                if result_preflight.get(key)
            ),
            None,
        )
        reward_sum = sum(float(item.get("evaluator_reward") or 0.0) for item in summaries)
        success_count = sum(int(bool(item.get("success"))) for item in summaries)
        per_read_token_counts: dict[tuple[str, int], int] = {}
        memory_token_counts = _a10_memory_token_counts(
            summaries, per_read=per_read_token_counts
        )
        manifest_payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        task_ids = {
            (str(item["task_class"]), int(item["task_seed"])): str(item["task_id"])
            for item in manifest_payload.get("instances") or []
        }
        pairwise_reference_path = REPOSITORY_ROOT / "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json"
        pairwise_reference = json.loads(pairwise_reference_path.read_text(encoding="utf-8"))
        elapsed_seconds = sum(
            (
                datetime.fromisoformat(item["finished_at"])
                - datetime.fromisoformat(item["started_at"])
            ).total_seconds()
            for item in summaries
        )
        active_success_count = sum(
            int(bool(item.get("success")) and _memory_active(item))
            for item in summaries
        )
        causal_read_analysis = (
            _a12_causal_read_analysis(summaries, per_read_token_counts)
            if dual_arm_name == "a12"
            else _dual_causal_read_analysis(summaries)
            if dual_scored_arm
            else _a10_causal_read_analysis(summaries)
        )
        productive_divergence_count = sum(
            item["analysis_class"]
            == "trace_grounded_productive_divergence_hypothesis"
            for item in causal_read_analysis
        )
        protocol_boundary_invalid = any(
            _memory_protocol_violation(item) for item in summaries
        ) or bool(
            dual_arm_name == "a12"
            and any(_a12_memory_record_mismatch(item) for item in summaries)
        )
        usage_totals = _usage_totals(summaries)
        executed_action_total = sum(
            int(item.get("executed_action_count") or 0) for item in summaries
        )
        model_call_total = sum(int(item.get("model_call_count") or 0) for item in summaries)
        a12_nonempty_read_total = sum(
            int(
                (item.get("memory_mechanism") or {}).get("nonempty_read_count")
                or (
                    (item.get("memory_mechanism") or {}).get("counters") or {}
                ).get("nonempty_read_count")
                or 0
            )
            for item in summaries
        )
        a12_rendered_token_total = sum(memory_token_counts.values())
        a12_cost_target = bool(
            model_call_total < 603
            and executed_action_total < 596
            and usage_totals["total_tokens"] < 3_464_267
            and a12_nonempty_read_total <= 95
            and a12_rendered_token_total <= 9_500
        )
        performance_target = bool(
            len(summaries) == 19
            and success_count >= 6
            and reward_sum > 5.5
            and _gate_passed(result_gate)
            and (dual_arm_name != "a12" or a12_cost_target)
        )
        if dual_arm_name == "a10v2":
            final_verdict = (
                "A10_V2_INFRASTRUCTURE_INVALID" if closure_errors
                else "A10_V2_PROTOCOL_INVALID" if protocol_boundary_invalid
                else "A10_V2_SCIENTIFIC_FAILURE" if not performance_target
                else "A10_V2_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL"
                if active_success_count < 1 or productive_divergence_count < 1
                else "A10_V2_OVERALL_PASS"
            )
        elif dual_arm_name == "a11":
            final_verdict = (
                "SUITE_INFRASTRUCTURE_INCOMPLETE" if closure_errors
                else "PROTOCOL_INVALID" if protocol_boundary_invalid
                else "A11_SCIENTIFIC_FAILURE" if not performance_target
                else "PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL"
                if active_success_count < 1 or productive_divergence_count < 1
                else "A11_OVERALL_PASS"
            )
        elif dual_arm_name == "a12":
            final_verdict = (
                "A12_SUITE_INFRASTRUCTURE_INCOMPLETE" if closure_errors
                else "A12_PROTOCOL_INVALID" if protocol_boundary_invalid
                else "A12_SCIENTIFIC_FAILURE" if not performance_target
                else "A12_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL"
                if active_success_count < 1 or productive_divergence_count < 1
                else "A12_OVERALL_PASS"
            )
        elif closure_errors:
            final_verdict = f"{result_prefix} INFRASTRUCTURE INVALID"
        elif protocol_boundary_invalid:
            final_verdict = f"{result_prefix} PROTOCOL INVALID"
        elif not performance_target:
            final_verdict = f"{result_prefix} SCIENTIFIC FAILURE"
        elif active_success_count < 1 or productive_divergence_count < 1:
            final_verdict = f"{result_prefix} PERFORMANCE PASS / MECHANISM EVIDENCE FAIL"
        else:
            final_verdict = f"{result_prefix} OVERALL PASS"
        aggregate[result_key] = {
            "schema": result_schema,
            "arm": dual_arm["arm"] if dual_scored_arm else "a10",
            "mechanism_id": run_signature["method"],
            "experiment_id": run_signature["experiment_id"],
            "parent_evidence_commit": result_parent_commit,
            "implementation_commit": implementation_commit,
            "source_freeze_sha256": result_source_freeze_sha256,
            "preflight_sha256": _sha256(result_preflight_path),
            "live_receipt_sha256": _sha256(result_receipt_path),
            "live_receipt_sha256s": aggregate["live_server_receipt_sha256s"],
            "run_signature_sha256": run_signature_sha256,
            "task_seed": result_task_seed,
            "generation_seed": args.generation_seed,
            "valid_episode_count": len(summaries),
            "invalid_episode_count": len(invalid_attempts),
            "gate": result_gate,
            "summary": {
                "success_count": success_count,
                "reward_sum": reward_sum,
                "executed_actions": sum(int(item.get("executed_action_count") or 0) for item in summaries),
                "model_calls": sum(int(item.get("model_call_count") or 0) for item in summaries),
                **_usage_totals(summaries),
                "elapsed_seconds": elapsed_seconds,
            },
            "memory": {
                "write_attempt_count": sum(int((item.get("memory_mechanism") or {}).get("write_attempt_count") or 0) for item in summaries),
                "write_success_count": sum(int((item.get("memory_mechanism") or {}).get("write_success_count") or 0) for item in summaries),
                "trigger_count": sum(int((item.get("memory_mechanism") or {}).get("trigger_count") or 0) for item in summaries),
                "nonempty_read_count": sum(int((item.get("memory_mechanism") or {}).get("nonempty_read_count") or 0) for item in summaries),
                "active_success_count": active_success_count,
                "max_reads_per_episode": max([int((item.get("memory_mechanism") or {}).get("nonempty_read_count") or 0) for item in summaries] or [0]),
                "rendered_chars_total": sum(int((item.get("memory_mechanism") or {}).get("rendered_chars_total") or 0) for item in summaries),
                "rendered_tokens_total": sum(memory_token_counts.values()),
                "model_calls_added": sum(int((item.get("memory_mechanism") or {}).get("model_calls_added") or 0) for item in summaries),
                "guard_enabled": any(bool((item.get("memory_mechanism") or {}).get("guard_enabled")) for item in summaries),
                "action_override_count": sum(int((item.get("memory_mechanism") or {}).get("action_override_count") or 0) for item in summaries),
                "forced_termination_count": sum(int((item.get("memory_mechanism") or {}).get("forced_termination_count") or 0) for item in summaries),
                "hidden_ui_used_for_decision": any(bool(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("hidden_ui_used_for_decision")) for item in summaries),
                "evaluator_used_for_decision": any(bool(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("evaluator_used_for_decision")) for item in summaries),
            },
            "per_task": [
                {
                    "task_id": task_ids[(str(item["task_name"]), int(item["seed"]))],
                    "task_name": item["task_name"],
                    "task_seed": item["seed"],
                    "native_max_steps": int((item.get("run_metadata") or {})["native_max_steps"]),
                    "episode_id": item["episode_id"],
                    "episode_json_sha256": _sha256(suite_dir / "episodes" / item["episode_id"] / "episode.json"),
                    "reward": item["evaluator_reward"],
                    "success": item["success"],
                    "termination_reason": item["termination_reason"],
                    "executed_actions": item["executed_action_count"],
                    "model_calls": item["model_call_count"],
                    "transport_attempt_max": max(
                        [int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) for step in item.get("steps", [])] or [0]
                    ),
                    **_usage_totals([item]),
                    "elapsed_seconds": (
                        datetime.fromisoformat(item["finished_at"])
                        - datetime.fromisoformat(item["started_at"])
                    ).total_seconds(),
                    "memory_active": bool((item.get("memory_mechanism") or {}).get("active")),
                    "memory_write_success_count": int((item.get("memory_mechanism") or {}).get("write_success_count") or 0),
                    "memory_trigger_count": int((item.get("memory_mechanism") or {}).get("trigger_count") or 0),
                    "memory_nonempty_read_count": int((item.get("memory_mechanism") or {}).get("nonempty_read_count") or 0),
                    "first_nonempty_read_step": (
                        (((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or [{}])[0].get("step")
                        if (((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events")) else None
                    ),
                    "memory_rendered_chars": int((item.get("memory_mechanism") or {}).get("rendered_chars_total") or 0),
                    "memory_rendered_tokens": memory_token_counts[str(item["episode_id"])],
                    "phase_switch_count": int(((item.get("memory_mechanism") or {}).get("phase") or {}).get("phase_switch_count") or 0),
                    "frontier_eviction_count": int(((item.get("memory_mechanism") or {}).get("frontiers") or {}).get("eviction_count") or 0),
                    "branch_eviction_count": int(((item.get("memory_mechanism") or {}).get("frontiers") or {}).get("branch_eviction_count") or 0),
                    "model_calls_added": int((item.get("memory_mechanism") or {}).get("model_calls_added") or 0),
                    "guard_enabled": bool((item.get("memory_mechanism") or {}).get("guard_enabled")),
                    "action_override_count": int((item.get("memory_mechanism") or {}).get("action_override_count") or 0),
                }
                for item in summaries
            ],
            "pairwise": {
                "A0": _a10_pairwise(summaries, "A0", pairwise_reference),
                "A1": _a10_pairwise(summaries, "A1", pairwise_reference),
                "reference_sha256": _sha256(pairwise_reference_path),
            },
            "causal_read_analysis": causal_read_analysis,
            "productive_divergence_hypothesis_count": productive_divergence_count,
            "performance_target_reached": performance_target,
            "overall_verdict": final_verdict,
        }
        if dual_scored_arm:
            base_result = aggregate[result_key]

            def audit_metric(audit: dict, *paths: tuple[str, ...]) -> int:
                for path in paths:
                    value: object = audit
                    for key in path:
                        if not isinstance(value, dict) or key not in value:
                            value = None
                            break
                        value = value[key]
                    if value is not None:
                        if isinstance(value, dict):
                            return sum(int(item or 0) for item in value.values())
                        return int(value or 0)
                return 0

            def total_metric(*paths: tuple[str, ...]) -> int:
                return sum(
                    audit_metric(item.get("memory_mechanism") or {}, *paths)
                    for item in summaries
                )

            task_rows = list(base_result["per_task"])
            for index, (row, summary) in enumerate(zip(task_rows, summaries, strict=True)):
                audit = summary.get("memory_mechanism") or {}
                row["task_index"] = index
                row["resolves_invalid_episode_id"] = summary.get("resolves_invalid_episode_id")
                row["provisional_route_watch_count"] = audit_metric(
                    audit, ("closed_route_watches", "created_count")
                )
                row["mature_route_watch_count"] = audit_metric(
                    audit, ("closed_route_watches", "matured_count")
                )
                row["normal_workflow_dismissal_count"] = audit_metric(
                    audit, ("closed_route_watches", "dismissed_count")
                )
                row["provisional_route_count"] = audit_metric(
                    audit,
                    ("routes", "provisional_count"),
                    ("routes", "closed_count"),
                    ("route_evidence", "provisional_route_count"),
                )
                row["confirmed_route_count"] = audit_metric(
                    audit,
                    ("routes", "confirmed_count"),
                    ("routes", "confirmation_counts"),
                    ("route_evidence", "confirmed_route_count"),
                )
                classifications = ((audit.get("routes") or {}).get("classification_counts") or {})
                row["normal_navigation_exemption_count"] = (
                    audit_metric(
                        audit,
                        ("routes", "normal_navigation_exemption_count"),
                        ("route_evidence", "normal_navigation_exemption_count"),
                    )
                    + int(classifications.get("WORKFLOW_ADVANCE") or 0)
                    + int(classifications.get("NOVEL_EXPLORATION_RETURN") or 0)
                )
                row["mature_trigger_count"] = audit_metric(
                    audit,
                    ("triggers", "mature_count"),
                    ("triggers", "matured_count"),
                    ("triggers", "delivered_count"),
                    ("triggers", "delivered_counts_by_kind"),
                )
                row["route_eviction_count"] = audit_metric(
                    audit, ("routes", "eviction_count")
                )
                boundary = audit.get("decision_boundary") or audit.get("causal_boundary") or {}
                row["forced_termination_count"] = int(boundary.get("forced_termination_count") or 0)
                row["hidden_ui_used"] = bool(boundary.get("hidden_ui_used_for_decision"))
                row["evaluator_used"] = bool(boundary.get("evaluator_used_for_decision"))
                row["future_used"] = bool(boundary.get("future_information_used"))

            common_memory = dict(base_result["memory"])
            common_memory.update(
                {
                    "mature_trigger_count": total_metric(
                        ("triggers", "mature_count"),
                        ("triggers", "matured_count"),
                        ("triggers", "delivered_count"),
                        ("triggers", "delivered_counts_by_kind"),
                    ),
                    "productive_divergence_count": productive_divergence_count,
                }
            )
            if dual_arm_name == "a10v2":
                common_memory.update(
                    {
                        "provisional_route_watch_count": total_metric(
                            ("closed_route_watches", "created_count")
                        ),
                        "mature_route_watch_count": total_metric(
                            ("closed_route_watches", "matured_count")
                        ),
                        "normal_workflow_dismissal_count": total_metric(
                            ("closed_route_watches", "dismissed_count")
                        ),
                        "max_reads_per_phase": max(
                            [
                                max(
                                    [
                                        sum(
                                            int(event.get("phase_id") == phase)
                                            for event in ((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or []
                                        )
                                        for phase in {
                                            event.get("phase_id")
                                            for event in ((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or []
                                        }
                                    ]
                                    or [0]
                                )
                                for item in summaries
                            ]
                            or [0]
                        ),
                        "minimum_read_cooldown": min(
                            [
                                later - earlier
                                for item in summaries
                                for earlier, later in zip(
                                    [int(event.get("step", -1)) for event in ((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or []],
                                    [int(event.get("step", -1)) for event in ((item.get("memory_mechanism") or {}).get("reads") or {}).get("read_events") or []][1:],
                                )
                            ]
                            or [None],
                            key=lambda value: float("inf") if value is None else value,
                        ),
                    }
                )
                aggregate[result_key] = {
                    "schema": result_schema,
                    "status": final_verdict,
                    "identity": {
                        "design_parent_commit": result_parent_commit,
                        "implementation_commit": implementation_commit,
                        "mechanism_id": run_signature["method"],
                        "experiment_id": run_signature["experiment_id"],
                        "source_freeze_sha256": result_source_freeze_sha256,
                        "preflight_sha256": _sha256(result_preflight_path),
                        "live_receipt_chain": aggregate["live_server_receipt_sha256s"],
                    },
                    "benchmark": {
                        "task_seed": result_task_seed,
                        "generation_seed": args.generation_seed,
                        "valid_episode_count": len(summaries),
                        "invalid_attempt_count": len(invalid_attempts),
                        "exact_order": True,
                    },
                    "gate": {
                        "status": result_gate.get("status"),
                        "required_success": int(result_gate.get("required", result_gate.get("required_success", 4))),
                        "observed_success": int(result_gate.get("success_count", result_gate.get("observed_success", 0))),
                        "tasks": result_gate.get("tasks") or [],
                    },
                    "performance": base_result["summary"],
                    "memory": common_memory,
                    "mechanism_evidence": {
                        "successful_active_memory_episodes": [
                            item["episode_id"]
                            for item in summaries
                            if item.get("success") and (item.get("memory_mechanism") or {}).get("active")
                        ],
                        "productive_divergence_hypotheses": [
                            item for item in causal_read_analysis
                            if item.get("analysis_class") == "trace_grounded_productive_divergence_hypothesis"
                        ],
                    },
                    "comparison": {
                        "versus_A0": base_result["pairwise"]["A0"],
                        "versus_A1": base_result["pairwise"]["A1"],
                    },
                    "invalid_attempts": invalid_attempts,
                    "tasks": task_rows,
                    "errors": [],
                }
            elif dual_arm_name == "a11":
                common_memory.update(
                    {
                        "provisional_route_count": total_metric(
                            ("routes", "provisional_count"),
                            ("routes", "closed_count"),
                            ("route_evidence", "provisional_route_count"),
                        ),
                        "confirmed_route_count": total_metric(
                            ("routes", "confirmed_count"),
                            ("routes", "confirmation_counts"),
                            ("route_evidence", "confirmed_route_count"),
                        ),
                        "normal_navigation_exemption_count": sum(
                            row["normal_navigation_exemption_count"] for row in task_rows
                        ),
                    }
                )
                historical_a10v1 = REPOSITORY_ROOT / "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json"
                aggregate[result_key] = {
                    "schema": result_schema,
                    "mechanism_id": run_signature["method"],
                    "experiment_id": run_signature["experiment_id"],
                    "parent_evidence_commit": result_parent_commit,
                    "implementation_commit": implementation_commit,
                    "source_freeze_sha256": result_source_freeze_sha256,
                    "preflight_sha256": _sha256(result_preflight_path),
                    "live_receipt_sha256": _sha256(result_receipt_path),
                    "historical_a10v1_report_sha256": _sha256(historical_a10v1),
                    "task_seed": result_task_seed,
                    "generation_seed": args.generation_seed,
                    "gate": result_gate,
                    "closure": {
                        "status": "exact_19_closed",
                        "valid_episode_count": len(summaries),
                        "invalid_attempt_count": len(invalid_attempts),
                        "ordered_tasks_exact": True,
                    },
                    "summary": base_result["summary"],
                    "memory": common_memory,
                    "pairwise": {
                        "versus_a0": base_result["pairwise"]["A0"],
                        "versus_a1": base_result["pairwise"]["A1"],
                    },
                    "episodes": task_rows,
                    "invalid_attempts": invalid_attempts,
                    "causal_read_analysis": causal_read_analysis,
                    "overall_verdict": final_verdict,
                    "errors": [],
                }
            else:
                for row, summary in zip(task_rows, summaries, strict=True):
                    audit = summary.get("memory_mechanism") or {}
                    counters = audit.get("counters") or {}
                    boundary = audit.get("causal_boundary") or {}
                    episode_id = str(summary.get("episode_id"))
                    episode_reads = [
                        item
                        for item in causal_read_analysis
                        if str(item.get("episode_id")) == episode_id
                    ]
                    row.update(
                        {
                            "resolves_invalid_episode_ids": list(
                                summary.get("resolves_invalid_episode_ids") or []
                            ),
                            "first_support_count": int(counters.get("support_created_count") or 0),
                            "candidate_matured_count": int(counters.get("candidate_matured_count") or 0),
                            "eligible_candidate_count": int(counters.get("eligible_candidate_count") or 0),
                            "actual_nonempty_read_count": int(audit.get("nonempty_read_count") or counters.get("nonempty_read_count") or 0),
                            "first_nonempty_read_step": min(
                                [
                                    int(event.get("read_step", -1))
                                    for event in audit.get("read_events") or []
                                    if event.get("actual_nonempty") is True
                                ]
                                or [None],
                                key=lambda value: (
                                    float("inf") if value is None else value
                                ),
                            ),
                            "rendered_chars": int(
                                audit.get("rendered_chars_total")
                                or sum(
                                    int(event.get("rendered_chars") or 0)
                                    for event in audit.get("read_events") or []
                                )
                            ),
                            "rendered_tokens": memory_token_counts[episode_id],
                            "context_reset_count": int(counters.get("context_loss_count") or 0)
                            + int(counters.get("material_progress_reset_count") or 0),
                            "cooldown_suppressed_count": int(counters.get("cooldown_suppressed_count") or 0),
                            "cap_suppressed_count": int(counters.get("cap_suppressed_count") or 0),
                            "one_shot_suppressed_count": int(counters.get("one_shot_suppressed_count") or 0),
                            "next_action_divergence_count": sum(item.get("next_action_diverged") is True for item in episode_reads),
                            "material_progress_after_read_count": sum(item.get("material_progress_within_2") is True for item in episode_reads),
                            "same_failed_action_relapse_count": sum(item.get("same_failed_action_within_4") is True for item in episode_reads),
                            "model_calls_added": int(
                                audit.get("model_calls_added")
                                or boundary.get("model_calls_added")
                                or 0
                            ),
                            "guard_enabled": bool(
                                audit.get("guard_enabled")
                                or boundary.get("guard_enabled")
                            ),
                            "action_override_count": int(
                                audit.get("action_override_count")
                                or boundary.get("action_override_count")
                                or 0
                            ),
                            "forced_termination_count": int(
                                audit.get("forced_termination_count")
                                or boundary.get("forced_termination_count")
                                or 0
                            ),
                            "hidden_ui_used": bool(
                                boundary.get("hidden_ui_used_for_decision")
                            ),
                            "evaluator_used": bool(
                                boundary.get("evaluator_used_for_decision")
                            ),
                            "future_used": bool(
                                boundary.get("future_information_used")
                            ),
                        }
                    )

                successful_active = [
                    str(item["episode_id"])
                    for item in summaries
                    if item.get("success") and _memory_active(item)
                ]
                a12_memory = {
                    "first_support_count": total_metric(("counters", "support_created_count")),
                    "candidate_matured_count": total_metric(("counters", "candidate_matured_count")),
                    "eligible_candidate_count": total_metric(("counters", "eligible_candidate_count")),
                    "actual_nonempty_read_count": sum(
                        int(
                            (item.get("memory_mechanism") or {}).get("nonempty_read_count")
                            or ((item.get("memory_mechanism") or {}).get("counters") or {}).get("nonempty_read_count")
                            or 0
                        )
                        for item in summaries
                    ),
                    "context_reset_count": total_metric(("counters", "context_loss_count"))
                    + total_metric(("counters", "material_progress_reset_count")),
                    "cooldown_suppressed_count": total_metric(("counters", "cooldown_suppressed_count")),
                    "cap_suppressed_count": total_metric(("counters", "cap_suppressed_count")),
                    "one_shot_suppressed_count": total_metric(("counters", "one_shot_suppressed_count")),
                    "rendered_chars_total": sum(
                        int(
                            (item.get("memory_mechanism") or {}).get("rendered_chars_total")
                            or sum(
                                int(event.get("rendered_chars") or 0)
                                for event in (item.get("memory_mechanism") or {}).get("read_events") or []
                            )
                        )
                        for item in summaries
                    ),
                    "rendered_tokens_total": a12_rendered_token_total,
                    "successful_active_memory_episodes": successful_active,
                    "productive_divergence_count": productive_divergence_count,
                    "model_calls_added": sum(
                        int(
                            (item.get("memory_mechanism") or {}).get("model_calls_added")
                            or ((item.get("memory_mechanism") or {}).get("causal_boundary") or {}).get("model_calls_added")
                            or 0
                        )
                        for item in summaries
                    ),
                    "guard_enabled": any(
                        bool(
                            (item.get("memory_mechanism") or {}).get("guard_enabled")
                            or ((item.get("memory_mechanism") or {}).get("causal_boundary") or {}).get("guard_enabled")
                        )
                        for item in summaries
                    ),
                    "action_override_count": sum(
                        int(
                            (item.get("memory_mechanism") or {}).get("action_override_count")
                            or ((item.get("memory_mechanism") or {}).get("causal_boundary") or {}).get("action_override_count")
                            or 0
                        )
                        for item in summaries
                    ),
                    "forced_termination_count": sum(
                        int(
                            (item.get("memory_mechanism") or {}).get("forced_termination_count")
                            or ((item.get("memory_mechanism") or {}).get("causal_boundary") or {}).get("forced_termination_count")
                            or 0
                        )
                        for item in summaries
                    ),
                }
                aggregate[result_key] = {
                    "schema": result_schema,
                    "status": final_verdict,
                    "identity": {
                        "mechanism_id": run_signature["method"],
                        "experiment_id": run_signature["experiment_id"],
                        "review_commit": result_review_commit,
                        "implementation_commit": implementation_commit,
                        "source_freeze_payload_sha256": result_preflight.get("source_freeze_payload_sha256", result_preflight.get("source_freeze_sha256")),
                        "reference_segments_sha256": _sha256(
                            dual_arm["reference_segments_path"]
                        ),
                        "offline_replay_sha256": result_preflight.get("offline_replay_sha256"),
                        "preflight_sha256": _sha256(result_preflight_path),
                        "live_receipt_chain": aggregate["live_server_receipt_sha256s"],
                    },
                    "benchmark": {
                        "task_seed": result_task_seed,
                        "generation_seed": args.generation_seed,
                        "valid_episode_count": len(summaries),
                        "invalid_attempt_count": len(invalid_attempts),
                        "exact_order": True,
                    },
                    "gate": {
                        "status": result_gate.get("status"),
                        "success_count": int(result_gate.get("success_count") or 0),
                        "required": int(result_gate.get("required") or 4),
                        "memory_active_success_count": sum(
                            int(bool(item.get("success")) and _memory_active(item))
                            for item in summaries[:4]
                        ),
                    },
                    "performance": base_result["summary"],
                    "memory": a12_memory,
                    "pairwise": {
                        "versus_a0": base_result["pairwise"]["A0"],
                        "versus_a1": base_result["pairwise"]["A1"],
                    },
                    "episodes": task_rows,
                    "invalid_attempts": invalid_attempts,
                    "read_causal_records": causal_read_analysis,
                    "errors": [],
                }
    _atomic_json(suite_dir / "aggregate.json", aggregate)
    checkpoint("complete")
    if dual_arm_name and dual_arm_name.startswith("sys_trrc_"):
        aggregate["sys_trrc_result"] = json.loads(
            (suite_dir / "sys_trrc_result.json").read_text(encoding="utf-8")
        )
        _atomic_json(suite_dir / "aggregate.json", aggregate)
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
