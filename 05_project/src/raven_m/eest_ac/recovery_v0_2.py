"""Strong, action-aware Recovery Registry for EEST-AC v0.2."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonicalize_action(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict) or not isinstance(action.get("type"), str):
        raise ValueError("A canonical action object with a type is required.")
    return json.loads(_canonical_json(action))


def action_signature(action: dict[str, Any]) -> str:
    return sha256(_canonical_json(canonicalize_action(action)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RecoveryRecordV02:
    recovery_id: str
    state_signature: str
    canonical_action_json: str
    action_signature: str
    action_class: str
    failed_event_id: str
    observed_step: int

    @property
    def canonical_action(self) -> dict[str, Any]:
        return json.loads(self.canonical_action_json)

    def record(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "state_signature": self.state_signature,
            "canonical_action": self.canonical_action,
            "action_signature": self.action_signature,
            "action_class": self.action_class,
            "failed_event_id": self.failed_event_id,
            "observed_step": self.observed_step,
            "instruction": "Choose a different action class in this unchanged state.",
        }


class RecoveryRegistryV02:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], RecoveryRecordV02] = {}

    @property
    def records(self) -> tuple[RecoveryRecordV02, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda item: (item.state_signature, item.action_class, item.action_signature),
            )
        )

    def register(
        self,
        *,
        state_signature: str,
        canonical_action: dict[str, Any],
        failed_event_id: str,
        observed_step: int,
        stability_audit: dict[str, Any],
    ) -> RecoveryRecordV02:
        if (
            stability_audit.get("outcome") != "no_effect_confirmed"
            or stability_audit.get("no_effect_confirmed") is not True
            or stability_audit.get("post_observations_agree") is not True
            or int(stability_audit.get("sample_count", 0)) < 2
        ):
            raise ValueError("Recovery requires a bounded stable no-effect audit.")
        action = canonicalize_action(canonical_action)
        signature = action_signature(action)
        action_class = action["type"]
        identity = {"state": state_signature, "action": signature}
        recovery_id = "recovery:v02:" + sha256(
            _canonical_json(identity).encode("utf-8")
        ).hexdigest()[:16]
        record = RecoveryRecordV02(
            recovery_id=recovery_id,
            state_signature=state_signature,
            canonical_action_json=_canonical_json(action),
            action_signature=signature,
            action_class=action_class,
            failed_event_id=failed_event_id,
            observed_step=observed_step,
        )
        self._records.setdefault((state_signature, signature), record)
        return self._records[(state_signature, signature)]

    def for_state(self, state_signature: str) -> tuple[RecoveryRecordV02, ...]:
        return tuple(item for item in self.records if item.state_signature == state_signature)

    def block_reason(
        self,
        *,
        state_signature: str,
        canonical_action: dict[str, Any],
    ) -> str | None:
        records = self.for_state(state_signature)
        if not records:
            return None
        action = canonicalize_action(canonical_action)
        signature = action_signature(action)
        if any(item.action_signature == signature for item in records):
            return "exact_action_repeat_in_stable_state"
        if any(item.action_class == action["type"] for item in records):
            return "same_action_class_forbidden_in_stable_state"
        return None
