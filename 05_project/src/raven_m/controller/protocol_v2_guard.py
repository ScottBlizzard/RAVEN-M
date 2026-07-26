"""Generic protocol-v2 provenance and repeated-action guard."""

from __future__ import annotations

from collections import defaultdict
import json
import re
from typing import Any

from raven_m.actions.schema import ActionValidationError


ANSWER_GOAL_RE = re.compile(
    r"\b(answer|return|report|tell|give|list|find|calculate|compute|what|"
    r"which|how many|how much|total duration|total distance)\b",
    flags=re.IGNORECASE,
)
TEXT_ACTIONS = {"type_text", "answer"}
TEXT_ORIGINS = {
    "task_literal",
    "current_screen",
    "verified_memory",
    "deterministic_calculation",
}
RECOVERY_CLASSES = (
    "change_target",
    "reverse_scroll_direction",
    "navigate_back",
    "reopen_app",
    "inspect_different_visible_control",
    "fail_safely",
)


def canonical_action_key(action: dict[str, Any]) -> str:
    return json.dumps(
        action,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class ProtocolV2DecisionGuard:
    """Fail closed on unsupported text provenance and no-effect loops."""

    def __init__(self, *, max_no_effect_repeats: int = 2) -> None:
        if max_no_effect_repeats < 1:
            raise ValueError("max_no_effect_repeats must be positive.")
        self.max_no_effect_repeats = max_no_effect_repeats
        self.reset(goal="")

    def reset(self, *, goal: str) -> None:
        self.goal = goal
        self.no_effect_counts: dict[tuple[str, str], int] = defaultdict(int)
        self.blocked_fingerprints: set[tuple[str, str]] = set()
        self.transition_fingerprints: list[tuple[str, str, str]] = []
        self.validation_blocks: list[dict[str, Any]] = []
        self.cycle_trigger_count = 0
        self.recovery_obligations = 0
        self.recovery_completions = 0

    def _validate_text_provenance(
        self,
        decision: dict[str, Any],
    ) -> None:
        action = decision.get("action")
        if not isinstance(action, dict) or action.get("type") not in TEXT_ACTIONS:
            return
        action_type = action["type"]
        origin = action.get("text_origin")
        source_ids = action.get("source_memory_ids")
        if origin not in TEXT_ORIGINS:
            raise ActionValidationError(
                f"{action_type} requires a valid text_origin."
            )
        if not isinstance(source_ids, list):
            raise ActionValidationError(
                f"{action_type} requires source_memory_ids."
            )
        if origin == "verified_memory" and not source_ids:
            raise ActionValidationError(
                "verified_memory text requires at least one source memory ID."
            )
        if origin != "verified_memory" and source_ids:
            raise ActionValidationError(
                "source_memory_ids must be empty unless text_origin is "
                "verified_memory."
            )
        cited = set(decision.get("memory_citations", []))
        if not set(source_ids).issubset(cited):
            raise ActionValidationError(
                "source_memory_ids must also appear in memory_citations."
            )
        if action_type == "answer":
            if decision.get("status") != "done":
                raise ActionValidationError("answer must be terminal.")
            if not ANSWER_GOAL_RE.search(self.goal):
                raise ActionValidationError(
                    "answer is permitted only for an information-return goal."
                )

    def validate_decision(
        self,
        decision: dict[str, Any],
        *,
        page_sha256: str,
    ) -> None:
        self._validate_text_provenance(decision)
        action = decision.get("action")
        if not isinstance(action, dict):
            return
        fingerprint = (page_sha256, canonical_action_key(action))
        if fingerprint in self.blocked_fingerprints:
            record = {
                "page_sha256": page_sha256,
                "action": action,
                "reason": "repeated_no_effect_action_blocked",
                "required_recovery_classes": list(RECOVERY_CLASSES),
            }
            self.validation_blocks.append(record)
            self.recovery_obligations += 1
            raise ActionValidationError(
                "LOOP_GUARD: this exact action already produced no effect "
                "twice on the unchanged page. Choose one recovery class: "
                + ", ".join(RECOVERY_CLASSES)
                + "."
            )

    def observe_transition(
        self,
        *,
        before_sha256: str,
        action: dict[str, Any],
        after_sha256: str,
    ) -> dict[str, Any]:
        action_key = canonical_action_key(action)
        fingerprint = (before_sha256, action_key)
        changed = before_sha256 != after_sha256
        if changed:
            self.no_effect_counts.pop(fingerprint, None)
        else:
            self.no_effect_counts[fingerprint] += 1
            if (
                self.no_effect_counts[fingerprint]
                >= self.max_no_effect_repeats
            ):
                self.blocked_fingerprints.add(fingerprint)
        self.transition_fingerprints.append(
            (before_sha256, action_key, after_sha256)
        )
        if len(self.transition_fingerprints) >= 4:
            a1, b1, a2, b2 = self.transition_fingerprints[-4:]
            if a1 == a2 and b1 == b2 and a1 != b1:
                self.blocked_fingerprints.update(
                    {(a1[0], a1[1]), (b1[0], b1[1])}
                )
                self.cycle_trigger_count += 1
        if self.recovery_obligations and fingerprint not in self.blocked_fingerprints:
            self.recovery_completions += 1
            self.recovery_obligations -= 1
        return {
            "changed": changed,
            "no_effect_repeat_count": self.no_effect_counts.get(
                fingerprint, 0
            ),
            "fingerprint_blocked": fingerprint in self.blocked_fingerprints,
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema_version": "protocol_v2_guard_audit.v1",
            "max_no_effect_repeats": self.max_no_effect_repeats,
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
            "validation_block_count": len(self.validation_blocks),
            "ab_ab_cycle_trigger_count": self.cycle_trigger_count,
            "validation_blocks": self.validation_blocks,
            "recovery_obligation_count": self.recovery_obligations,
            "recovery_completion_count": self.recovery_completions,
        }
