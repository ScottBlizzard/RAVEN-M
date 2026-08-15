"""Fail-closed shared contract for the four SYS-TRRC prospective modes."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from . import sys_trrc_recovery as recovery
from .sys_trrc_recovery import MAX_AUX_TOKENS, SYSTEM_ID

PROTOCOL_ID = "SYS_TRRC_R2_ONE_SHOT_RECOVERY_PREREG_V2"
MECHANISM_ID = SYSTEM_ID
PARENT_EVIDENCE_COMMIT = "ad522db47a40421a08f64d1896d14b743149add1"
TASK_SEED = 20260806
GENERATION_SEED = 3407
MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
PORT = 18000
PREFLIGHT_SCHEMA = "sys_trrc_v2_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "sys_trrc_v2_live_server_receipt_v1"
CHECKPOINT_SCHEMA = "sys_trrc_v2_checkpoint_v1"
RESULT_SCHEMA = "sys_trrc_v2_result_v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

# Exact authorization closure.  Keeping this in the contract (rather than only
# in the report generator) prevents a forged preflight from silently omitting
# files whose bytes participate in the experiment.
SOURCE_FILES = (
    "protocols/SYS_TRRC_R2_ONE_SHOT_RECOVERY_V2_PREREG_2026-08-15.md",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r3v3_one_shot_cnr.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_trrc_recovery.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_trrc_token_budget.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_trrc_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_sys_trrc.py",
    "implementation/scripts/run_sys_trrc.py",
    "implementation/scripts/qualify_sys_trrc_server.py",
    "implementation/scripts/replay_sys_trrc_detector.py",
    "implementation/scripts/start_sys_trrc_server.sh",
    "implementation/configs/sys_trrc_v2_base_hard_seed20260806.json",
    "implementation/configs/sys_trrc_v2_detector_hard_seed20260806.json",
    "implementation/configs/sys_trrc_v2_generic_hard_seed20260806.json",
    "implementation/configs/sys_trrc_v2_full_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json",
    "evidence/sys_trrc_v2/SYS_TRRC_V2_R2_DETECTOR_REPLAY.json",
    "evidence/sys_trrc/token_projection_inputs/manifest.json",
    "evidence/sys_trrc/token_projection_inputs/01_BrowserMultiply_step_014.png",
    "evidence/sys_trrc/token_projection_inputs/02_ExpenseAddMultipleFromMarkor_step_014.png",
    "evidence/sys_trrc/token_projection_inputs/03_MarkorCreateNoteAndSms_step_013.png",
    "evidence/sys_trrc/token_projection_inputs/04_MarkorMergeNotes_step_013.png",
    "evidence/sys_trrc/token_projection_inputs/05_OsmAndTrack_step_015.png",
    "evidence/sys_trrc/token_projection_inputs/06_RecipeAddMultipleRecipesFromImage_step_006.png",
    "evidence/sys_trrc/token_projection_inputs/07_RecipeAddMultipleRecipesFromMarkor_step_015.png",
    "evidence/sys_trrc/token_projection_inputs/08_RecipeAddMultipleRecipesFromMarkor2_step_020.png",
    "implementation/tests/official_qwen_mobile/test_sys_trrc_contract_runner.py",
    "implementation/tests/official_qwen_mobile/test_sys_trrc_recovery.py",
    "implementation/tests/official_qwen_mobile/test_sys_trrc_token_budget.py",
    "implementation/tests/official_qwen_mobile/test_recovery_policy_controller.py",
    "implementation/tests/models/test_sys_trrc_aux_timeout.py",
)

MODE_BINDINGS = {
    "base": {
        "arm_id": "SYS-TRRC-V2-R2-BASE",
        "experiment_id": "SYS_TRRC_V2_B_R2_BASE_QWEN3VL32B_AW_HARD_S20260806_V1",
        "config": "implementation/configs/sys_trrc_v2_base_hard_seed20260806.json",
    },
    "detector": {
        "arm_id": "SYS-TRRC-V2-R2-DETECTOR",
        "experiment_id": "SYS_TRRC_V2_D_R2_DETECTOR_QWEN3VL32B_AW_HARD_S20260806_V1",
        "config": "implementation/configs/sys_trrc_v2_detector_hard_seed20260806.json",
    },
    "generic": {
        "arm_id": "SYS-TRRC-V2-R2-GENERIC",
        "experiment_id": "SYS_TRRC_V2_G_R2_GENERIC_RECOVERY_QWEN3VL32B_AW_HARD_S20260806_V1",
        "config": "implementation/configs/sys_trrc_v2_generic_hard_seed20260806.json",
    },
    "full": {
        "arm_id": "SYS-TRRC-V2-R2-FULL",
        "experiment_id": "SYS_TRRC_V2_F_R2_TRIGGERED_RECOVERY_QWEN3VL32B_AW_HARD_S20260806_V1",
        "config": "implementation/configs/sys_trrc_v2_full_hard_seed20260806.json",
    },
}

PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2", "RetroSavePlaylist", "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint", "OsmAndMarker",
)
ACTIVATION_TASK = "BrowserMultiply"
CAPABILITY_GATE_TASKS = PRESERVATION_TASKS + (ACTIVATION_TASK,)
FULL_TASK_ORDER = CAPABILITY_GATE_TASKS + (
    "ExpenseAddMultipleFromGallery", "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms", "MarkorMergeNotes", "MarkorTranscribeVideo",
    "OsmAndTrack", "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor", "RecipeAddMultipleRecipesFromMarkor2",
    "SaveCopyOfReceiptTaskEval", "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)
CONTROL_TASK_ORDER = (PRESERVATION_TASKS[0], ACTIVATION_TASK)
STAGE_TASKS = {
    "l1": (PRESERVATION_TASKS[0],),
    "l2": PRESERVATION_TASKS,
    "l3": CAPABILITY_GATE_TASKS,
    "l4": FULL_TASK_ORDER,
}
CAMPAIGN_INVOCATION_ORDER = (
    ("full", "l1"),
    ("base", "l1"), ("detector", "l1"), ("generic", "l1"),
    ("full", "l2"), ("generic", "l2"),
    ("full", "l3"),
    ("base", "l3"), ("detector", "l3"), ("generic", "l3"),
    ("full", "l4"), ("generic", "l4"),
)
ALLOWED_STAGES = {
    "base": ("l1", "l3"), "detector": ("l1", "l3"),
    "generic": ("l1", "l2", "l3", "l4"),
    "full": ("l1", "l2", "l3", "l4"),
}

EXPECTED_COMMON_AUX_SYSTEM_TEMPLATE = """You are a bounded auxiliary reasoner. You do not act, terminate, edit memory,
or decide whether the task is complete.

{role_instruction}

Use only the supplied task goal, current screenshot, exact R2 ledger, bounded
recent executed-action summaries, and detector evidence. The current screenshot
is authoritative. Do not use hidden UI, evaluator information, future state,
or outside task knowledge. Return exactly three single-line fields:

ASSESSMENT: <brief visible-evidence assessment>
RECOMMENDATION: <one concise suggestion for the executor's next decision>
VISIBLE_CHECK: <what visible evidence the executor should inspect next>"""
EXPECTED_GENERIC_ROLE = """Independently review the supplied visible evidence and provide one concise
next-decision suggestion."""
EXPECTED_FULL_ROLE = """Identify the currently recurring or visibly unsupported approach and provide
one materially different, screenshot-grounded recovery strategy for the next
decision."""
EXPECTED_ADVICE_TEMPLATE = """AUXILIARY ADVICE (non-authoritative; expires after this request):
ASSESSMENT: {assessment}
RECOMMENDATION: {recommendation}
VISIBLE_CHECK: {visible_check}
The current screenshot is authoritative. The executor must decide the next action."""


def expected_config(mode: str) -> dict[str, Any]:
    arm = binding(mode)
    control = mode in {"base", "detector"}
    recovery_config: dict[str, Any] = {
        "max_aux_calls_per_episode": 0 if control else 1,
        "max_aux_tokens": 192,
        "max_total_tokenizer_tokens": 8192,
        "max_latency_seconds": 60,
        "transport_attempts_per_call": 1,
        "retry": False,
        "require_remaining_normal_decision_slot": True,
        "exact_protocol_prompts": True,
        "aux_parser": "blank_line_tolerant_exact_three_fields_v2",
    }
    if mode == "base":
        recovery_config = {"enabled": False, **recovery_config}
    return {
        "schema": "sys_trrc_v2_config_v1",
        "protocol_id": PROTOCOL_ID,
        "system_id": SYSTEM_ID,
        "arm_id": arm["arm_id"],
        "mode": mode,
        "experiment_id": arm["experiment_id"],
        "task_seed": TASK_SEED,
        "generation_seed": GENERATION_SEED,
        "task_order": (
            "staged_L1_Expense_then_L3_Browser_control_complete_two"
            if control else
            "staged_L1_Expense_then_L2_R2_six_then_L3_Browser_then_L4_remaining_twelve"
        ),
        "r2": {
            "mechanism_id": "a1r2_compact_verified_pending_v1",
            "ttl_requests": 8,
            "max_render_chars": 1100,
            "system_prompt": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
        },
        "recovery": recovery_config,
    }


def canonical_sha256(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value); payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def v1_live_aux_parser_regression(root: Path | None = None) -> dict[str, Any]:
    """Recompute the V2 delivery repair against the exact frozen V1 response."""
    fixture_path = (root or REPOSITORY_ROOT) / (
        "evidence/sys_trrc/SYS_TRRC_FULL_L1_EXPENSE_EPISODE_2026-08-15.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_episode_id = "ExpenseDeleteMultiple2_20260806_4f40564b"
    if fixture.get("episode_id") != fixture_episode_id:
        raise RuntimeError("V1 fixture episode identity")
    attempt = (fixture.get("auxiliary_model_call_attempts") or [])[0]
    model_call = attempt.get("model_call") or {}
    response_sha = "5f8c63ee635b460ce38f61dc00c67bf3eb9ed0b8d43c94decaf9e8ae404278a1"
    content = str(model_call.get("content") or "")
    if (
        int(attempt.get("request_step")) != 7
        or model_call.get("response_sha256") != response_sha
        or sha256(content.encode()).hexdigest() != response_sha
    ):
        raise RuntimeError("V1 fixture response identity")
    parsed = recovery.parse_auxiliary_response(content)
    if not str(parsed.get("recommendation") or "").startswith('Tap the "MORE" link'):
        raise RuntimeError("V1 fixture parser output")
    return {
        "status": "PASS",
        "fixture_episode_id": fixture_episode_id,
        "response_sha256": response_sha,
        "request_step": 7,
        "parsed_render_sha256": sha256(parsed["rendered"].encode()).hexdigest(),
        "blank_only_lines_ignored": True,
    }


def binding(mode: str) -> dict[str, Any]:
    if mode not in MODE_BINDINGS:
        raise RuntimeError(f"unknown SYS-TRRC mode: {mode}")
    item = dict(MODE_BINDINGS[mode])
    item["mode"] = mode
    item["config_path"] = REPOSITORY_ROOT / item.pop("config")
    return item


def source_freeze_path(mode: str) -> Path:
    binding(mode)
    return REPOSITORY_ROOT / f"evidence/sys_trrc_v2/SYS_TRRC_V2_{mode.upper()}_SOURCE_FREEZE.json"


def stage_contract(mode: str, stage: str) -> dict[str, Any]:
    """Return the exact single-invocation stage closure for one independent arm."""
    binding(mode)
    if stage not in ALLOWED_STAGES[mode]:
        raise RuntimeError(f"SYS-TRRC {mode} does not permit stage {stage}")
    control = mode in {"base", "detector"}
    tasks = (
        CONTROL_TASK_ORDER[:1]
        if control and stage == "l1"
        else CONTROL_TASK_ORDER
        if control
        else STAGE_TASKS[stage]
    )
    prior = {
        "l2": "stage_l1_complete",
        "l3": "stage_l1_complete" if control else "stage_l2_complete",
        "l4": "stage_l3_complete",
    }.get(stage)
    completion = (
        "control_complete" if control and stage == "l3"
        else f"stage_{stage}_complete" if stage != "l4"
        else "complete"
    )
    return {"mode": mode, "stage": stage, "tasks": tuple(tasks),
            "required_prior_status": prior, "completion_status": completion}


def validate_campaign_ledger(path: Path) -> dict[str, Any]:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if (
        ledger.get("schema") != "sys_trrc_v2_campaign_ledger_v1"
        or ledger.get("protocol_id") != PROTOCOL_ID
        or ledger.get("planned_order") != [list(item) for item in CAMPAIGN_INVOCATION_ORDER]
        or ledger.get("content_sha256") != content_sha256(ledger)
        or not str(ledger.get("campaign_id") or "")
    ):
        raise RuntimeError("SYS-TRRC campaign ledger integrity")
    previous = None
    for ordinal, entry in enumerate(ledger.get("entries") or [], start=1):
        if (
            int(entry.get("ordinal") or 0) != ordinal
            or [entry.get("mode"), entry.get("stage")]
            != list(CAMPAIGN_INVOCATION_ORDER[ordinal - 1])
            or entry.get("previous_entry_sha256") != previous
        ):
            raise RuntimeError("SYS-TRRC campaign ledger chain")
        entry_payload = dict(entry)
        entry_sha = entry_payload.pop("entry_sha256", None)
        if canonical_sha256(entry_payload) != entry_sha:
            raise RuntimeError("SYS-TRRC campaign entry hash")
        for field in ("checkpoint_path", "result_path"):
            artifact = Path(str(entry.get(field) or ""))
            if not artifact.is_file() or file_sha256(artifact) != entry.get(f"{field}_sha256"):
                raise RuntimeError(f"SYS-TRRC campaign artifact drift: {field}")
        mode = str(entry.get("mode") or "")
        stage = str(entry.get("stage") or "")
        arm = binding(mode)
        suite_dir = Path(str(entry.get("suite_dir") or ""))
        snapshot_checkpoint = Path(str(entry["checkpoint_path"]))
        snapshot_result = Path(str(entry["result_path"]))
        if not suite_dir.is_dir():
            raise RuntimeError("SYS-TRRC campaign suite missing")
        checkpoint = json.loads(snapshot_checkpoint.read_text(encoding="utf-8"))
        result = json.loads(snapshot_result.read_text(encoding="utf-8"))
        if (
            checkpoint.get("schema") != CHECKPOINT_SCHEMA
            or checkpoint.get("prospective_arm") != f"sys_trrc_{mode}"
            or checkpoint.get("experiment_id") != arm["experiment_id"]
            or checkpoint.get("mechanism_id") != MECHANISM_ID
            or checkpoint.get("sys_trrc_stage") != stage
            or checkpoint.get("status") != entry.get("checkpoint_status")
            or checkpoint.get("content_sha256") != content_sha256(checkpoint)
            or result.get("status") != entry.get("result_status")
            or result.get("content_sha256") != content_sha256(result)
        ):
            raise RuntimeError("SYS-TRRC campaign checkpoint/result identity")
        stage_info = stage_contract(mode, stage)
        if entry.get("advancement_authorized") is True:
            if (
                int(entry.get("return_code") or 0) != 0
                or checkpoint.get("status") != stage_info["completion_status"]
            ):
                raise RuntimeError("SYS-TRRC campaign advancement authorization")
        elif checkpoint.get("status") == stage_info["completion_status"]:
            raise RuntimeError("SYS-TRRC completed stage was not authorized")
        preflight_path = Path(str(entry.get("preflight_path") or ""))
        if (
            not preflight_path.is_file()
            or file_sha256(preflight_path) != entry.get("preflight_path_sha256")
        ):
            raise RuntimeError("SYS-TRRC campaign preflight artifact drift")
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        run_signature_sha256 = str(checkpoint.get("run_signature_sha256") or "")
        if run_signature_sha256 != entry.get("run_signature_sha256"):
            raise RuntimeError("SYS-TRRC campaign run signature drift")
        validate_result_payload(
            result, mode=mode, checkpoint_path=snapshot_checkpoint,
            run_signature_sha256=run_signature_sha256, preflight=preflight,
            preflight_path=preflight_path, suite_dir=suite_dir,
        )
        previous = entry_sha
    pending = ledger.get("pending_attempt")
    if pending is not None:
        next_ordinal = len(ledger.get("entries") or []) + 1
        if (
            not isinstance(pending, dict)
            or int(pending.get("ordinal") or 0) != next_ordinal
            or [pending.get("mode"), pending.get("stage")]
            != list(CAMPAIGN_INVOCATION_ORDER[next_ordinal - 1])
        ):
            raise RuntimeError("SYS-TRRC campaign pending invocation")
        suite_text = str(pending.get("suite_dir") or "")
        if suite_text:
            suite_dir = Path(suite_text)
            checkpoint_path = suite_dir / "checkpoint.json"
            if checkpoint_path.is_file():
                checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                if (
                    checkpoint.get("prospective_arm")
                    != f"sys_trrc_{pending['mode']}"
                    or checkpoint.get("sys_trrc_stage") != pending["stage"]
                    or checkpoint.get("content_sha256") != content_sha256(checkpoint)
                ):
                    raise RuntimeError("SYS-TRRC campaign pending checkpoint")
    return ledger


def _recomputed_projection_evidence(
    projector: Any | None = None,
) -> dict[str, Any]:
    """Rebuild the complete eight-row multimodal projection from frozen inputs."""
    from . import sys_trrc_recovery as recovery
    from .sys_trrc_token_budget import ExactQwenMultimodalTokenProjector

    package = REPOSITORY_ROOT / "evidence/sys_trrc/token_projection_inputs"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    replay = json.loads(
        (REPOSITORY_ROOT / "evidence/sys_trrc_v2/SYS_TRRC_V2_R2_DETECTOR_REPLAY.json")
        .read_text(encoding="utf-8")
    )
    if (
        manifest.get("schema") != "sys_trrc_token_projection_inputs_v1"
        or manifest.get("status") != "PASS"
        or manifest.get("errors") != []
        or manifest.get("generation_calls") != 0
        or manifest.get("content_sha256") != content_sha256(manifest)
    ):
        raise RuntimeError("projection_manifest_integrity")
    if replay.get("content_sha256") != content_sha256(replay):
        raise RuntimeError("detector_replay_integrity")
    manifest_source = manifest.get("source") or {}
    replay_source = replay.get("source") or {}
    if (
        manifest_source.get("checkpoint_file_sha256")
        != replay_source.get("checkpoint_file_sha256")
        # The PNG package was materialized before V2 from the byte-identical
        # V1 detector behavior. Its source hash remains immutable, while the
        # current replay below carries the independent V2 audit identity.
        or manifest_source.get("detector_replay_content_sha256")
        != "ed47170cdceb0ea4354ac04c3761a9ae1a5d5a03458c027aea871ce0c739c55b"
        or manifest_source.get("suite_id") != replay_source.get("suite_id")
        or int(manifest_source.get("valid_episode_count") or 0) != 19
        or int(replay_source.get("valid_episode_count") or 0) != 19
    ):
        raise RuntimeError("projection_manifest_source_binding")

    trigger_rows: list[dict[str, Any]] = []
    for episode in replay.get("episodes") or []:
        trigger_count = int(episode.get("trigger_count") or 0)
        triggers = list(episode.get("triggers") or [])
        if trigger_count != len(triggers):
            raise RuntimeError("detector_replay_trigger_count")
        if trigger_count == 0:
            continue
        if trigger_count != 1:
            raise RuntimeError("detector_replay_trigger_cap")
        trigger = triggers[0]
        trigger_rows.append({
            "task_name": str(episode.get("task_name") or ""),
            "episode_id": str(episode.get("episode_id") or ""),
            "eligible_request_step": int(trigger.get("eligible_request_step")),
            "receipt_id": str(trigger.get("receipt_id") or ""),
        })
    manifest_rows = list(manifest.get("opportunities") or [])
    if len(trigger_rows) != 8 or len(manifest_rows) != 8:
        raise RuntimeError("projection_opportunity_cardinality")

    if projector is None:
        projector = ExactQwenMultimodalTokenProjector(
            Path(MODEL_REALPATH), expected_revision=MODEL_REVISION
        )
    prepared: list[dict[str, Any]] = []
    projection_requests: list[dict[str, str]] = []
    for ordinal, (frozen, trigger) in enumerate(
        zip(manifest_rows, trigger_rows, strict=True), start=1
    ):
        if int(frozen.get("ordinal") or 0) != ordinal:
            raise RuntimeError(f"projection_ordinal:{ordinal}")
        for field in ("task_name", "episode_id", "eligible_request_step"):
            if frozen.get(field) != trigger[field]:
                raise RuntimeError(f"projection_replay_binding:{ordinal}:{field}")
        screenshot = (package / str(frozen.get("png_file") or "")).resolve()
        try:
            screenshot.relative_to(package.resolve())
        except ValueError as exc:
            raise RuntimeError(f"projection_png_escape:{ordinal}") from exc
        screenshot_sha256 = file_sha256(screenshot)
        if screenshot_sha256 != frozen.get("png_sha256"):
            raise RuntimeError(f"projection_png_hash:{ordinal}")

        frozen_modes = frozen.get("modes") or {}
        if set(frozen_modes) != {"generic", "full"}:
            raise RuntimeError(f"projection_mode_closure:{ordinal}")
        mode_inputs: dict[str, dict[str, str]] = {}
        for recovery_mode in ("generic", "full"):
            frozen_mode = frozen_modes[recovery_mode]
            if frozen_mode.get("receipt_id") != trigger["receipt_id"]:
                raise RuntimeError(f"projection_receipt_binding:{ordinal}:{recovery_mode}")
            expected_system = recovery.COMMON_AUX_SYSTEM_TEMPLATE.format(
                role_instruction=(
                    recovery.GENERIC_ROLE if recovery_mode == "generic"
                    else recovery.FULL_ROLE
                )
            )
            system_prompt = str(frozen_mode.get("system_prompt") or "")
            user_prompt = str(frozen_mode.get("user_prompt") or "")
            request_sha256 = sha256(
                (system_prompt + "\n\0\n" + user_prompt).encode("utf-8")
            ).hexdigest()
            if (
                system_prompt != expected_system
                or request_sha256 != frozen_mode.get("request_text_sha256")
            ):
                raise RuntimeError(f"projection_request_binding:{ordinal}:{recovery_mode}")
            mode_inputs[recovery_mode] = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "screenshot_path": str(screenshot),
                "request_text_sha256": request_sha256,
            }
            projection_requests.append({
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "screenshot_path": str(screenshot),
            })
        prepared.append({
            "frozen": frozen, "trigger": trigger,
            "screenshot_sha256": screenshot_sha256,
            "mode_inputs": mode_inputs,
        })

    if hasattr(projector, "project_many"):
        projections = projector.project_many(projection_requests)
    else:
        projections = [
            projector(
                request["system_prompt"], request["user_prompt"],
                request["screenshot_path"],
            )
            for request in projection_requests
        ]
    if len(projections) != 16:
        raise RuntimeError("projection_batch_cardinality")

    opportunities: list[dict[str, Any]] = []
    projection_index = 0
    for row in prepared:
        frozen = row["frozen"]
        trigger = row["trigger"]
        projected_modes: dict[str, Any] = {}
        receipt_ids: dict[str, str] = {}
        for recovery_mode in ("generic", "full"):
            mode_input = row["mode_inputs"][recovery_mode]
            projection = projections[projection_index]
            projection_index += 1
            projected_total = (
                int(projection["exact_multimodal_input_tokens"]) + MAX_AUX_TOKENS
            )
            if projected_total > 8192:
                raise RuntimeError(
                    f"projection_token_budget:{frozen['ordinal']}:{recovery_mode}"
                )
            projected_modes[recovery_mode] = {
                **projection,
                "request_text_sha256": mode_input["request_text_sha256"],
                "reserved_output_tokens": MAX_AUX_TOKENS,
                "projected_total_tokens": projected_total,
            }
            receipt_ids[recovery_mode] = trigger["receipt_id"]
        opportunities.append({
            "task_name": trigger["task_name"],
            "episode_id": trigger["episode_id"],
            "eligible_request_step": trigger["eligible_request_step"],
            "receipt_ids": receipt_ids,
            "png_file": frozen["png_file"],
            "screenshot_sha256": row["screenshot_sha256"],
            "modes": projected_modes,
        })
    return {
        "schema": "sys_trrc_eight_opportunity_token_projection_v1",
        "source_suite": str(manifest_source.get("suite_id") or ""),
        "opportunity_count": 8,
        "processor_files_sha256": dict(projector.processor_files_sha256),
        "maximum_projected_total_tokens": max(
            int(mode_row["projected_total_tokens"])
            for row in opportunities for mode_row in row["modes"].values()
        ),
        "opportunities": opportunities,
    }


def validate_preflight_report(
    path: Path, *, expected_mode: str | None = None,
    projector: Any | None = None, recompute_projection: bool = True,
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    mode = expected_mode or str(report.get("mode") or "")
    arm = binding(mode)
    config = json.loads(arm["config_path"].read_text(encoding="utf-8"))
    expected = {
        "schema": PREFLIGHT_SCHEMA, "status": "PASS", "errors": [],
        "generation_calls": 0, "live_generation_authorized": True,
        "protocol_id": PROTOCOL_ID, "system_id": SYSTEM_ID, "mode": mode,
        "arm_id": arm["arm_id"], "experiment_id": arm["experiment_id"],
        "config_content_sha256": canonical_sha256(config),
    }
    errors = [f"{k}_drift" for k, v in expected.items() if report.get(k) != v]
    if report.get("content_sha256") != content_sha256(report): errors.append("content_hash")
    if config != expected_config(mode):
        errors.append("config_semantic_closure")
    checks = report.get("checks") or {}
    exact_prompt_values = {
        "common": EXPECTED_COMMON_AUX_SYSTEM_TEMPLATE,
        "generic": EXPECTED_GENERIC_ROLE,
        "full": EXPECTED_FULL_ROLE,
        "wrapper": EXPECTED_ADVICE_TEMPLATE,
    }
    if {
        "common": recovery.COMMON_AUX_SYSTEM_TEMPLATE,
        "generic": recovery.GENERIC_ROLE,
        "full": recovery.FULL_ROLE,
        "wrapper": recovery.ADVICE_TEMPLATE,
    } != exact_prompt_values:
        errors.append("runtime_prompt_semantic_closure")
    expected_prompt_hashes = {
        key: sha256(value.encode("utf-8")).hexdigest()
        for key, value in exact_prompt_values.items()
    }
    if checks.get("exact_protocol_prompt_sha256s") != expected_prompt_hashes:
        errors.append("preflight_prompt_hash_closure")
    required_config = expected_config(mode)["recovery"].copy()
    required_config.pop("enabled", None)
    if checks.get("required_recovery_config") != required_config:
        errors.append("preflight_recovery_config_closure")
    try:
        expected_parser_regression = v1_live_aux_parser_regression()
        if checks.get("v1_live_aux_parser_regression") != expected_parser_regression:
            errors.append("v1_live_aux_parser_regression_closure")
    except Exception as exc:
        errors.append(
            f"v1_live_aux_parser_regression_recompute:{type(exc).__name__}:{exc}"
        )
    focused_tests = checks.get("focused_tests") or {}
    if focused_tests.get("returncode") != 0:
        errors.append("focused_tests_not_passed")
    reported_sources = (checks.get("source_files") or {})
    if set(reported_sources) != set(SOURCE_FILES):
        errors.append("source_file_closure")
    projection = (checks.get("eight_opportunity_token_projection") or {})
    try:
        if recompute_projection:
            recomputed_projection = (
                _recomputed_projection_evidence()
                if projector is None else
                _recomputed_projection_evidence(projector)
            )
            if projection != recomputed_projection:
                errors.append("eight_opportunity_token_projection_exact_closure")
        elif (
            projector is None
            or projection.get("schema")
            != "sys_trrc_eight_opportunity_token_projection_v1"
            or int(projection.get("opportunity_count") or 0) != 8
            or len(projection.get("opportunities") or []) != 8
            or int(projection.get("maximum_projected_total_tokens") or 999999) > 8192
            or projection.get("processor_files_sha256")
            != projector.processor_files_sha256
        ):
            errors.append("eight_opportunity_token_projection_runtime_binding")
        replay = json.loads(
            (REPOSITORY_ROOT / "evidence/sys_trrc_v2/SYS_TRRC_V2_R2_DETECTOR_REPLAY.json")
            .read_text(encoding="utf-8")
        )
        if checks.get("detector_replay_content_sha256") != replay.get("content_sha256"):
            errors.append("detector_replay_report_binding")
    except Exception as exc:
        errors.append(f"eight_opportunity_token_projection_recompute:{type(exc).__name__}:{exc}")
    commit = str(report.get("implementation_commit") or "")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        errors.append("implementation_commit")
    else:
        if subprocess.run(["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor",
                           PARENT_EVIDENCE_COMMIT, commit], capture_output=True).returncode:
            errors.append("parent_evidence_not_ancestor")
        for name, expected_sha in reported_sources.items():
            source = REPOSITORY_ROOT / str(name)
            try:
                frozen = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "show", f"{commit}:{name}"])
                if sha256(frozen).hexdigest() != expected_sha or file_sha256(source) != expected_sha:
                    errors.append(f"source_drift:{name}")
            except Exception:
                errors.append(f"source_missing:{name}")
        freeze_payload = {
            "schema": "sys_trrc_v2_source_freeze_v1",
            "implementation_commit": commit,
            "files": reported_sources,
        }
        if report.get("source_freeze_content_sha256") != content_sha256(freeze_payload):
            errors.append("source_freeze_content_hash")
        freeze_path = source_freeze_path(mode)
        try:
            frozen_report = json.loads(freeze_path.read_text(encoding="utf-8"))
            if frozen_report != {**freeze_payload, "content_sha256": content_sha256(freeze_payload)}:
                errors.append("source_freeze_file")
        except Exception:
            errors.append("source_freeze_file")
    if errors: raise RuntimeError(f"SYS-TRRC preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path,
                            expected_mode: str | None = None,
                            projector: Any | None = None,
                            recompute_projection: bool = True) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    mode = expected_mode or str(receipt.get("mode") or "")
    arm = binding(mode); preflight = validate_preflight_report(
        preflight_path, expected_mode=mode, projector=projector,
        recompute_projection=recompute_projection,
    )
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA, "status": "PASS", "errors": [],
        "generation_calls": 0, "protocol_id": PROTOCOL_ID, "system_id": SYSTEM_ID,
        "mode": mode, "arm_id": arm["arm_id"], "experiment_id": arm["experiment_id"],
        "implementation_commit": preflight.get("implementation_commit"),
        "preflight_content_sha256": preflight.get("content_sha256"),
        "served_model_id": MODEL_ID, "served_model_ids_observed": [MODEL_ID],
        "model_realpath": MODEL_REALPATH, "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    errors = [f"{k}_drift" for k, v in expected.items() if receipt.get(k) != v]
    if receipt.get("content_sha256") != content_sha256(receipt): errors.append("content_hash")
    try:
        stamp = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age_seconds = (datetime.now(timezone.utc)-stamp.astimezone(timezone.utc)).total_seconds()
        if stamp.tzinfo is None or age_seconds < -60 or age_seconds > 43200: raise ValueError
    except (TypeError, ValueError): errors.append("qualified_at")
    cmdline = str(receipt.get("process_cmdline") or "")
    if "vllm" not in cmdline or MODEL_REALPATH not in cmdline or str(PORT) not in cmdline: errors.append("process_identity")
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(not str(x) for x in packages.values()):
        errors.append("packages")
    model_verification = receipt.get("model_content_verification") or {}
    model_rows = list(model_verification.get("files") or [])
    supplemental_rows = list(model_verification.get("supplemental_files") or [])
    model_file_set = [
        {"path": row.get("path"), "sha256": row.get("sha256")}
        for row in model_rows
    ]
    if (
        model_verification.get("schema") != "sys_trrc_model_content_verification_v1"
        or model_verification.get("status") != "PASS"
        or model_verification.get("manifest_file_sha256") != MODEL_MANIFEST_SHA256
        or int(model_verification.get("file_count") or 0) < 20
        or len(model_rows)
        != int(model_verification.get("file_count") or 0)
        or model_verification.get("directory_closed") is not True
        or int(model_verification.get("supplemental_file_count") or 0) != 3
        or int(model_verification.get("directory_file_count") or 0)
        != len(model_rows) + len(supplemental_rows)
        or [str(row.get("path") or "") for row in supplemental_rows]
        != [".gitattributes", "README.md", "merges.txt"]
        or len(supplemental_rows) != 3
        or any(
            set(row) != {"path", "sha256", "size", "mtime_ns"}
            or len(str(row.get("sha256") or "")) != 64
            or int(row.get("size", -1)) < 0
            or int(row.get("mtime_ns", -1)) < 0
            for row in supplemental_rows
        )
        or [str(row.get("path") or "") for row in model_rows]
        != sorted(str(row.get("path") or "") for row in model_rows)
        or len({str(row.get("path") or "") for row in model_rows}) != len(model_rows)
        or any(
            set(row) != {"path", "sha256", "size", "mtime_ns"}
            or not str(row.get("path") or "")
            or len(str(row.get("sha256") or "")) != 64
            or int(row.get("size", -1)) < 0
            or int(row.get("mtime_ns", -1)) < 0
            for row in model_rows
        )
        or model_verification.get("file_set_sha256")
        != canonical_sha256(model_file_set)
        or model_verification.get("supplemental_file_set_sha256")
        != canonical_sha256([
            {"path": row.get("path"), "sha256": row.get("sha256")}
            for row in supplemental_rows
        ])
        or model_verification.get("content_sha256") != content_sha256(model_verification)
    ):
        errors.append("model_content_verification")
    if os.name != "nt":
        proc = Path(f"/proc/{int(receipt.get('process_pid') or -1)}/cmdline")
        observed = proc.read_bytes().replace(b"\0", b" ").decode() if proc.is_file() else ""
        if observed != cmdline: errors.append("process_not_alive_or_drifted")
    if errors: raise RuntimeError(f"SYS-TRRC receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    found = {str(x.get("task_name")): x for x in summaries}
    rows = [{"task_name": n, "reward": (found.get(n) or {}).get("evaluator_reward"),
             "pass": (found.get(n) or {}).get("evaluator_reward") == 1.0}
            for n in PRESERVATION_TASKS]
    observed_count = sum(int((found.get(x["task_name"]) or {}).get("evaluator_reward") is not None) for x in rows)
    success_count = sum(int(x["pass"]) for x in rows)
    status = "pass" if success_count == 6 else "fail" if success_count < observed_count else "incomplete_by_stage"
    return {"status": status, "success_count": success_count, "observed_count": observed_count,
            "required": 6, "tasks": rows}


def activation_report(summaries: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    binding(mode)
    item = next((x for x in summaries if x.get("task_name") == ACTIVATION_TASK), None)
    if item is None:
        return {"status": "incomplete_by_stage", "task_name": ACTIVATION_TASK,
                "episode_present": False, "qualification": "NOT_RUN_BY_STAGE",
                "trigger_count": 0, "aux_committed_count": 0,
                "injection_committed_count": 0, "valid_auxiliary_response": False,
                "valid_committed_injection": False, "immediate_normal_action_executed": False,
                "qualifying_visible_window": False, "task_success": False}
    audit = ((item or {}).get("recovery_mechanism") or {})
    counters = audit.get("counters") or {}
    triggered = int(counters.get("trigger_count") or 0) == 1
    aux = int(counters.get("aux_committed_count") or 0)
    injected = int(counters.get("injection_committed_count") or 0)
    aux_attempts = [
        attempt for attempt in (item or {}).get("auxiliary_model_call_attempts", [])
        if attempt.get("model_call") is not None
    ]
    valid_aux_attempts = [
        attempt for attempt in aux_attempts
        if not attempt.get("error")
        and ((attempt.get("commit") or {}).get("valid_output") is True)
        and bool((attempt.get("commit") or {}).get("injection_text"))
        and bool((attempt.get("commit") or {}).get("injection_ticket_id"))
        and int((((attempt.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1
    ]
    valid_aux = aux == 1 and len(aux_attempts) == 1 and len(valid_aux_attempts) == 1
    aux_ticket = (
        str((valid_aux_attempts[0].get("commit") or {}).get("injection_ticket_id") or "")
        if valid_aux else ""
    )
    injected_steps = [
        step for step in (item or {}).get("steps", [])
        if ((step.get("recovery") or {}).get("normal_injection"))
    ]
    injection_record = (
        ((injected_steps[0].get("recovery") or {}).get("normal_injection") or {})
        if len(injected_steps) == 1 else {}
    )
    injection_commit = injection_record.get("injection_commit") or {}
    valid_injection = bool(
        injected == 1 and len(injected_steps) == 1 and aux_ticket
        and str(injection_record.get("ticket_id") or "") == aux_ticket
        and injection_commit.get("event") == "normal_injection_committed"
        and str(injection_commit.get("ticket_id") or "") == aux_ticket
        and int(injection_commit.get("transport_attempts") or 0) == 1
    )
    immediate_action_executed = bool(
        valid_injection
        and injected_steps[0].get("executed")
        and isinstance(((injected_steps[0].get("decision") or {}).get("canonical_action")), dict)
    )
    watches = list(audit.get("post_injection_watches") or [])
    qualifying_watch = bool(
        len(watches) == 1
        and 1 <= int(watches[0].get("observed_actions") or 0) <= 4
        and watches[0].get("visible_change_seen") is True
        and watches[0].get("anchor_relapse_seen") is False
    )
    if mode == "base":
        passed = item is not None and item.get("error") is None and item.get("evaluator_reward") is not None
        qualification = "VALID_SEALED_BROWSER_EPISODE" if passed else "BASE_CONTROL_EPISODE_INVALID"
    elif mode == "detector":
        passed = bool(item and triggered and aux == 0 and injected == 0 and len(aux_attempts) == 0)
        qualification = "DETECTOR_ACTIVATED" if passed else "DETECTOR_CONTROL_ACTIVATION_FAILED"
    elif mode == "generic":
        passed = bool(item and triggered and valid_aux and valid_injection)
        qualification = "DELIVERED" if passed else "GENERIC_CONTROL_DELIVERY_FAILED"
    else:
        passed = bool(item and triggered and valid_aux and valid_injection and immediate_action_executed and qualifying_watch and bool(item.get("success")))
        qualification = "QUALIFYING_RECOVERY_SUCCESS" if passed else "FULL_QUALIFYING_RECOVERY_FAILED"
    return {"status": "pass" if passed else "fail", "task_name": ACTIVATION_TASK,
            "episode_present": item is not None, "trigger_count": int(counters.get("trigger_count") or 0),
            "aux_committed_count": aux, "injection_committed_count": injected,
            "valid_auxiliary_response": valid_aux,
            "valid_committed_injection": valid_injection,
            "immediate_normal_action_executed": immediate_action_executed,
            "qualifying_visible_window": qualifying_watch,
            "qualification": qualification,
            "task_success": bool((item or {}).get("success"))}


def cost_accounting_errors(
    summaries: list[dict[str, Any]], mode: str | None = None,
) -> list[str]:
    """Fail closed on absent or internally inconsistent measured costs."""
    errors: list[str] = []
    for summary in summaries:
        normal_records = [step.get("model_call") for step in summary.get("steps", [])]
        aux_records = [
            attempt.get("model_call")
            for attempt in summary.get("auxiliary_model_call_attempts", [])
            if attempt.get("model_call") is not None
        ]
        if any(not isinstance(record, dict) for record in normal_records + aux_records):
            errors.append("model_call_audit_missing")
            continue
        normal_count = summary.get(
            "normal_decision_call_count",
            summary.get("model_call_count") if mode == "base" else None,
        )
        aux_count = summary.get(
            "aux_recovery_call_count", 0 if mode == "base" else None,
        )
        if (
            normal_count is None or aux_count is None
            or int(normal_count or 0) != len(normal_records)
            or int(aux_count or 0) != len(aux_records)
            or int(summary.get("model_call_count") or 0)
            != len(normal_records) + len(aux_records)
        ):
            errors.append("call_accounting")
        for record in normal_records + aux_records:
            usage = record.get("usage")
            meta = record.get("raven_meta") or {}
            if not isinstance(usage, dict):
                errors.append("model_usage_missing")
                continue
            try:
                prompt = int(usage["prompt_tokens"])
                completion = int(usage["completion_tokens"])
                total = int(usage["total_tokens"])
                latency = float(meta["latency_seconds"])
            except (KeyError, TypeError, ValueError):
                errors.append("model_cost_missing")
                continue
            if (
                prompt < 0 or completion < 0 or total < 0
                or total != prompt + completion
                or not math.isfinite(latency) or latency < 0
            ):
                errors.append("model_cost_boundary")
        for field in (
            "recovery_detector_cpu_seconds", "recovery_projection_cpu_seconds",
        ):
            if field not in summary:
                errors.append(f"{field}_missing")
                continue
            try:
                value = float(summary[field])
            except (TypeError, ValueError):
                errors.append(f"{field}_invalid")
                continue
            if not math.isfinite(value) or value < 0:
                errors.append(f"{field}_invalid")
    return sorted(set(errors))


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]],
                            lifecycle_errors: list[dict[str, Any]], mode: str | None = None) -> list[str]:
    errors = []
    if tuple(str(x.get("task_name")) for x in summaries) != FULL_TASK_ORDER: errors.append("task_order")
    if len(summaries) != 19: errors.append("valid_episode_count")
    if any(int(x.get("seed") or -1) != TASK_SEED for x in summaries): errors.append("task_seed")
    if lifecycle_errors or any(not x.get("resolved_by_episode_id") for x in invalid_attempts): errors.append("unresolved_infrastructure")
    if len(invalid_attempts) > 2: errors.append("infrastructure_replacement_cap")
    try:
        if any(not math.isfinite(float(x.get("evaluator_reward"))) for x in summaries): errors.append("reward")
    except (TypeError, ValueError): errors.append("reward")
    for item in summaries:
        if int(item.get("model_call_count") or 0) != int(item.get("normal_decision_call_count") or 0) + int(item.get("aux_recovery_call_count") or 0): errors.append("call_accounting")
        if int(item.get("aux_recovery_call_count") or 0) > (0 if mode in {"base", "detector"} else 1): errors.append("aux_call_cap")
        records = [(s.get("model_call") or {}) for s in item.get("steps", [])]
        records += [(a.get("model_call") or {}) for a in item.get("auxiliary_model_call_attempts", []) if a.get("model_call")]
        if any(int(((x.get("raven_meta") or {}).get("transport_attempts") or 0)) != 1 for x in records): errors.append("transport_attempt_not_one")
        audit = item.get("recovery_mechanism") or {}; state = audit.get("state") or {}; counters = audit.get("counters") or {}
        if any(state.get(k) is not None for k in ("support", "pending_receipt", "pending_aux", "pending_injection")): errors.append("unclosed_recovery_state")
        if int(counters.get("trigger_count") or 0) > 1: errors.append("trigger_cap")
        if int(counters.get("aux_committed_count") or 0) + int(counters.get("cancelled_aux_count") or 0) > (0 if mode in {"base", "detector"} else 1): errors.append("aux_lifecycle_cap")
    errors.extend(cost_accounting_errors(summaries, mode))
    return sorted(set(errors))


def control_completion_errors(*, summaries: list[dict[str, Any]],
                              invalid_attempts: list[dict[str, Any]],
                              lifecycle_errors: list[dict[str, Any]],
                              mode: str) -> list[str]:
    errors: list[str] = []
    if mode not in {"base", "detector"}: errors.append("control_mode")
    if tuple(str(x.get("task_name")) for x in summaries) != CONTROL_TASK_ORDER:
        errors.append("task_order")
    if len(summaries) != 2: errors.append("valid_episode_count")
    if any(int(x.get("seed") or -1) != TASK_SEED for x in summaries): errors.append("task_seed")
    if lifecycle_errors or any(not x.get("resolved_by_episode_id") for x in invalid_attempts):
        errors.append("unresolved_infrastructure")
    if len(invalid_attempts) > 2: errors.append("infrastructure_replacement_cap")
    for item in summaries:
        if int(item.get("aux_recovery_call_count") or 0) != 0:
            errors.append("control_aux_call")
        normal_count = int(
            item.get("normal_decision_call_count", item.get("model_call_count", 0)) or 0
        )
        if int(item.get("model_call_count") or 0) != normal_count:
            errors.append("call_accounting")
        records = [(s.get("model_call") or {}) for s in item.get("steps", [])]
        if any(int(((x.get("raven_meta") or {}).get("transport_attempts") or 0)) != 1 for x in records):
            errors.append("transport_attempt_not_one")
        audit = item.get("recovery_mechanism") or {}
        state = audit.get("state") or {}
        if any(state.get(k) is not None for k in ("support", "pending_receipt", "pending_aux", "pending_injection")):
            errors.append("unclosed_recovery_state")
    errors.extend(cost_accounting_errors(summaries, mode))
    return sorted(set(errors))


def result_payload(*, mode: str, status: str, summaries: list[dict[str, Any]],
                   invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]],
                   run_signature_sha256: str, preflight: dict[str, Any],
                   preflight_file_sha256: str, receipt_file_sha256s: list[str],
                   checkpoint_sha256: str | None = None,
                   campaign_stage: str | None = None) -> dict[str, Any]:
    """Create a formal COMPLETE or gate-terminal partial result from immutable episode evidence."""
    arm = binding(mode)
    expected_order = CONTROL_TASK_ORDER if mode in {"base", "detector"} else FULL_TASK_ORDER
    normal = sum(int(x.get("normal_decision_call_count", x.get("model_call_count", 0)) or 0) for x in summaries)
    aux = sum(int(x.get("aux_recovery_call_count") or 0) for x in summaries)
    calls = sum(int(x.get("model_call_count") or 0) for x in summaries)
    token_groups = {k: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                    for k in ("normal", "aux", "combined")}
    transport = {"normal_call_count": 0, "aux_call_count": 0, "maximum_attempts": 0,
                 "all_single_attempt": True}
    model_latency = {"normal_seconds": 0.0, "aux_seconds": 0.0, "combined_seconds": 0.0}
    for summary in summaries:
        normal_calls = [(s.get("model_call") or {}) for s in summary.get("steps", [])]
        aux_calls = [(a.get("model_call") or {}) for a in summary.get("auxiliary_model_call_attempts", []) if a.get("model_call")]
        for kind, records in (("normal", normal_calls), ("aux", aux_calls)):
            transport[f"{kind}_call_count"] += len(records)
            for record in records:
                attempts = int(((record.get("raven_meta") or {}).get("transport_attempts") or 0))
                latency = float(((record.get("raven_meta") or {}).get("latency_seconds") or 0.0))
                model_latency[f"{kind}_seconds"] += latency
                model_latency["combined_seconds"] += latency
                transport["maximum_attempts"] = max(transport["maximum_attempts"], attempts)
                transport["all_single_attempt"] &= attempts == 1
                usage = record.get("usage") or {}
                for key in token_groups[kind]:
                    value = int(usage.get(key) or 0)
                    token_groups[kind][key] += value; token_groups["combined"][key] += value
    elapsed = sum(max(0.0, (datetime.fromisoformat(x["finished_at"])-datetime.fromisoformat(x["started_at"])).total_seconds()) for x in summaries)
    completion_errors = (
        exact_completion_errors(
            summaries=summaries, invalid_attempts=invalid_attempts,
            lifecycle_errors=lifecycle_errors, mode=mode,
        )
        if status == "COMPLETE" else
        control_completion_errors(
            summaries=summaries, invalid_attempts=invalid_attempts,
            lifecycle_errors=lifecycle_errors, mode=mode,
        )
        if status == "CONTROL_COMPLETE" else []
    )
    errors = sorted(set(completion_errors + cost_accounting_errors(summaries, mode)))
    success_count = sum(int(bool(x.get("success"))) for x in summaries)
    reward_sum = sum(float(x.get("evaluator_reward") or 0) for x in summaries)
    preservation = preservation_report(summaries)
    if mode != "full":
        accuracy_verdict = "NOT_PRIMARY_FULL_ARM"
    elif status == "COMPLETE":
        accuracy_verdict = (
            "PASS" if success_count >= 7 and reward_sum > 6.5
            and preservation["status"] == "pass" else "FAIL"
        )
    elif status.startswith("TERMINAL_SCIENTIFIC_FAILURE"):
        accuracy_verdict = "TERMINAL_FAIL"
    else:
        accuracy_verdict = "NOT_YET_ADJUDICATED"
    payload = {
        "schema": RESULT_SCHEMA, "status": status, "protocol_id": PROTOCOL_ID,
        "identity": {"system_id": SYSTEM_ID, "arm_id": arm["arm_id"], "mode": mode,
                     "experiment_id": arm["experiment_id"], "task_seed": TASK_SEED,
                     "generation_seed": GENERATION_SEED,
                     "implementation_commit": preflight.get("implementation_commit"),
                     "source_freeze_content_sha256": preflight.get("source_freeze_content_sha256"),
                     "preflight_content_sha256": preflight.get("content_sha256"),
                     "preflight_file_sha256": preflight_file_sha256,
                     "run_signature_sha256": run_signature_sha256,
                     "receipt_file_sha256s": sorted(set(receipt_file_sha256s)),
                     "checkpoint_sha256": checkpoint_sha256},
        "claim_boundary": {
            "intervention_kind": "r2_memory_plus_triggered_auxiliary_recovery_reasoning",
            "memory_improvement_claim_permitted": False,
            "held_out": False,
            "held_out_reason": "all_19_seed20260806_tasks_were_previously_observed",
        },
        "closure": {"valid_episode_count": len(summaries), "expected_episode_count": len(expected_order),
                    "campaign_stage": campaign_stage,
                    "ordered_tasks": [x.get("task_name") for x in summaries],
                    "not_run_by_protocol": list(expected_order[len(summaries):]) if status not in {"COMPLETE", "CONTROL_COMPLETE"} else [],
                    "invalid_attempt_count": len(invalid_attempts),
                    "invalid_attempts": invalid_attempts, "lifecycle_errors": lifecycle_errors,
                    "completion_errors": errors},
        "gates": {"preservation": preservation,
                  "activation": activation_report(summaries, mode)},
        "verdicts": {
            "accuracy": accuracy_verdict,
            "cost": "REPORTED_SEPARATELY_NO_SUBSTITUTION_FOR_ACCURACY",
            "specialized_recovery_causality": "NOT_ADJUDICATED_REQUIRES_CROSS_ARM_EXACT_PREFIX_JOIN",
        },
        "performance": {"success_count": success_count,
                        "reward_sum": reward_sum,
                        "model_calls": {"normal": normal, "aux": aux, "combined": calls},
                        "token_usage": token_groups, "valid_elapsed_seconds": elapsed,
                        "model_latency": model_latency,
                        "detector_cpu_seconds": sum(float(x.get("recovery_detector_cpu_seconds") or 0.0) for x in summaries),
                        "token_projection_cpu_seconds": sum(float(x.get("recovery_projection_cpu_seconds") or 0.0) for x in summaries),
                        "advice_injected_chars": sum(int(((s.get("recovery") or {}).get("normal_injection") or {}).get("rendered_chars") or 0) for x in summaries for s in x.get("steps", [])),
                        "advice_induced_executor_prompt_tokens": sum(int(((s.get("recovery") or {}).get("normal_injection") or {}).get("advice_induced_executor_prompt_tokens") or 0) for x in summaries for s in x.get("steps", [])),
                        "transport": transport},
        "scientific_failure_terminal": status.startswith("TERMINAL_SCIENTIFIC_FAILURE"),
        "errors": errors,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_result_payload(result: dict[str, Any], *, mode: str,
                            checkpoint_path: Path, run_signature_sha256: str,
                            preflight: dict[str, Any],
                            preflight_path: Path | None = None,
                            suite_dir: Path | None = None) -> None:
    arm = binding(mode); identity = result.get("identity") or {}
    errors = []
    expected = {"schema": RESULT_SCHEMA, "protocol_id": PROTOCOL_ID}
    errors += [f"{k}_drift" for k, v in expected.items() if result.get(k) != v]
    identity_expected = {
        "system_id": SYSTEM_ID, "arm_id": arm["arm_id"], "mode": mode,
        "experiment_id": arm["experiment_id"],
        "run_signature_sha256": run_signature_sha256,
        "preflight_content_sha256": preflight.get("content_sha256"),
        "source_freeze_content_sha256": preflight.get("source_freeze_content_sha256"),
        "checkpoint_sha256": file_sha256(checkpoint_path),
    }
    errors += [f"identity_{k}" for k, v in identity_expected.items() if identity.get(k) != v]
    if result.get("content_sha256") != content_sha256(result): errors.append("content_hash")
    closure = result.get("closure") or {}
    if closure.get("campaign_stage") not in {None, "l1", "l2", "l3", "l4"}:
        errors.append("campaign_stage")
    expected_count = 2 if mode in {"base", "detector"} else 19
    if int(closure.get("valid_episode_count") or 0) + len(closure.get("not_run_by_protocol") or []) != expected_count:
        errors.append("partial_cardinality")
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except Exception:
        checkpoint = {}
        errors.append("checkpoint_parse")
    checkpoint_expected = {
        "schema": CHECKPOINT_SCHEMA,
        "run_signature_sha256": run_signature_sha256,
        "prospective_arm": f"sys_trrc_{mode}",
        "experiment_id": arm["experiment_id"],
        "mechanism_id": MECHANISM_ID,
        "sys_trrc_stage": closure.get("campaign_stage"),
    }
    errors += [f"checkpoint_{k}" for k, v in checkpoint_expected.items()
               if checkpoint.get(k) != v]
    if checkpoint.get("content_sha256") != content_sha256(checkpoint):
        errors.append("checkpoint_content_hash")
    checkpoint_status = str(checkpoint.get("status") or "")
    if checkpoint_status == "complete":
        expected_status = "COMPLETE"
    elif checkpoint_status == "control_complete":
        expected_status = "CONTROL_COMPLETE"
    elif checkpoint_status.startswith("stage_") and checkpoint_status.endswith("_complete"):
        expected_status = checkpoint_status.upper()
    elif "gate" in checkpoint_status or checkpoint_status.startswith("stopped_scientific"):
        expected_status = f"TERMINAL_SCIENTIFIC_FAILURE_{checkpoint_status.upper()}"
    elif checkpoint_status in {"infrastructure_incomplete", "stopped_invalid_episode"}:
        expected_status = f"INFRASTRUCTURE_{checkpoint_status.upper()}"
    else:
        expected_status = "RUNNING_PARTIAL"
    status = str(result.get("status") or "")
    if status != expected_status:
        errors.append("status_checkpoint_mismatch")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("sys_trrc_valid_entries") or [])
    errors.extend(cost_accounting_errors(summaries, mode))
    if len(entries) != len(summaries):
        errors.append("checkpoint_entry_cardinality")
    expected_order = CONTROL_TASK_ORDER if mode in {"base", "detector"} else FULL_TASK_ORDER
    observed_order = tuple(str(item.get("task_name")) for item in summaries)
    if observed_order != tuple(expected_order[:len(summaries)]):
        errors.append("checkpoint_task_prefix")
    campaign_stage = closure.get("campaign_stage")
    if campaign_stage in {"l1", "l2", "l3", "l4"}:
        try:
            stage_info = stage_contract(mode, str(campaign_stage))
            if checkpoint_status == stage_info["completion_status"]:
                if observed_order != tuple(stage_info["tasks"]):
                    errors.append("checkpoint_stage_task_closure")
            elif checkpoint_status in {
                "stage_l1_complete", "stage_l2_complete", "stage_l3_complete",
                "control_complete", "complete",
            }:
                errors.append("checkpoint_stage_status_closure")
        except RuntimeError:
            errors.append("checkpoint_stage_mode_closure")
    artifact_suite_dir = suite_dir.resolve() if suite_dir is not None else checkpoint_path.parent
    for summary, entry in zip(summaries, entries):
        episode_id = str(summary.get("episode_id") or "")
        expected_identity = (
            str(summary.get("task_name")), int(summary.get("seed", -1)), episode_id
        )
        entry_identity = (
            str(entry.get("task_name")), int(entry.get("seed", -1)),
            str(entry.get("episode_id")),
        )
        if entry_identity != expected_identity:
            errors.append("checkpoint_entry_identity")
            continue
        if entry.get("run_signature_sha256") != run_signature_sha256:
            errors.append("checkpoint_entry_signature")
        episode_path = artifact_suite_dir / "episodes" / episode_id / "episode.json"
        try:
            on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
            if file_sha256(episode_path) != entry.get("episode_json_sha256"):
                errors.append("checkpoint_episode_file_hash")
            if canonical_sha256(on_disk) != entry.get("summary_sha256"):
                errors.append("checkpoint_episode_summary_hash")
            if canonical_sha256(summary) != entry.get("summary_sha256") or on_disk != summary:
                errors.append("checkpoint_summary_drift")
        except Exception:
            errors.append("checkpoint_episode_missing")
    for attempt in checkpoint.get("invalid_attempts") or []:
        if attempt.get("reason") == "suite_lifecycle_error":
            if (
                attempt.get("episode_id") is not None
                or not isinstance(attempt.get("error"), dict)
                or not str((attempt.get("error") or {}).get("stage") or "")
            ):
                errors.append("suite_lifecycle_invalid_attempt")
            continue
        episode_id = str(attempt.get("episode_id") or "")
        artifact = attempt.get("artifact") or {}
        episode_path = artifact_suite_dir / "episodes" / episode_id / "episode.json"
        try:
            on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
            if file_sha256(episode_path) != artifact.get("episode_json_sha256"):
                errors.append("invalid_episode_file_hash")
            if canonical_sha256(on_disk) != artifact.get("summary_sha256"):
                errors.append("invalid_episode_summary_hash")
            for field in (
                "model_call_count", "normal_decision_call_count",
                "aux_recovery_call_count",
            ):
                if int(on_disk.get(field) or 0) != int(artifact.get(field) or 0):
                    errors.append(f"invalid_episode_{field}")
            if (
                str(on_disk.get("episode_id") or "") != episode_id
                or str(on_disk.get("task_name") or "")
                != str(attempt.get("task_name") or "")
                or int(on_disk.get("seed", -1)) != int(attempt.get("seed", -1))
            ):
                errors.append("invalid_episode_identity")
        except Exception:
            errors.append("invalid_episode_missing")
    run_signature_path = artifact_suite_dir / "run_signature.json"
    try:
        run_signature = json.loads(run_signature_path.read_text(encoding="utf-8"))
        if canonical_sha256(run_signature) != run_signature_sha256:
            errors.append("run_signature_file")
    except Exception:
        errors.append("run_signature_file")
    if preflight_path is None or not preflight_path.is_file():
        errors.append("preflight_file_missing")
    elif file_sha256(preflight_path) != identity.get("preflight_file_sha256"):
        errors.append("preflight_file_hash")
    checkpoint_receipts = sorted(set(checkpoint.get("live_server_receipt_sha256s") or []))
    if sorted(set(identity.get("receipt_file_sha256s") or [])) != checkpoint_receipts:
        errors.append("receipt_hash_closure")
    if not errors:
        reconstructed = result_payload(
            mode=mode,
            status=status,
            summaries=summaries,
            invalid_attempts=list(checkpoint.get("invalid_attempts") or []),
            lifecycle_errors=list(checkpoint.get("lifecycle_errors") or []),
            run_signature_sha256=run_signature_sha256,
            preflight=preflight,
            preflight_file_sha256=file_sha256(preflight_path),
            receipt_file_sha256s=checkpoint_receipts,
            checkpoint_sha256=file_sha256(checkpoint_path),
            campaign_stage=closure.get("campaign_stage"),
        )
        if reconstructed != result:
            errors.append("result_not_derived_from_checkpoint")
    if errors: raise RuntimeError(f"SYS-TRRC result closure invalid: {errors}")
