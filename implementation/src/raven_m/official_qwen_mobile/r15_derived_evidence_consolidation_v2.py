"""Stabilized-v2 identity for one-shot late raw-evidence rehydration."""

from __future__ import annotations

from typing import Any, Callable

from .r15_derived_evidence_consolidation import LateRawEvidenceRehydrationPolicy


SYSTEM_ID = "sys_r2_stabilized_late_raw_evidence_rehydration_v2"
EXPERIMENT_ID = "SYS_R2_SLRER_QWEN3VL32B_S20260806_G3407_V2"
AUDIT_SCHEMA = "sys_r2_stabilized_late_raw_evidence_rehydration_audit_v2"
POST_ACTION_SETTLE_SECONDS = 1.0


class StabilizedLateRawEvidenceRehydrationPolicy(
    LateRawEvidenceRehydrationPolicy
):
    """Reuse the frozen LRER state machine under a new composite identity.

    Visible-frame settling is performed by the controller before its single
    post-action capture.  This wrapper changes no LRER trigger, evidence, or
    renderer semantics; it makes the new system identity explicit in every
    per-episode audit.
    """

    system_id = SYSTEM_ID

    def __init__(self, *, text_delta_counter: Callable[[str, str], int]) -> None:
        super().__init__(text_delta_counter=text_delta_counter)

    def audit_record(self) -> dict[str, Any]:
        record = super().audit_record()
        record.update(
            {
                "schema": AUDIT_SCHEMA,
                "system_id": SYSTEM_ID,
                "experiment_id": EXPERIMENT_ID,
                "visible_frame_settle": {
                    "policy": "fixed_visible_frame_settle_before_single_capture_v1",
                    "seconds": POST_ACTION_SETTLE_SECONDS,
                    "additional_model_calls": 0,
                    "additional_actions": 0,
                    "additional_state_captures": 0,
                    "uses_hidden_ui_or_activity": False,
                },
            }
        )
        return record


__all__ = [
    "AUDIT_SCHEMA",
    "EXPERIMENT_ID",
    "POST_ACTION_SETTLE_SECONDS",
    "SYSTEM_ID",
    "StabilizedLateRawEvidenceRehydrationPolicy",
]
