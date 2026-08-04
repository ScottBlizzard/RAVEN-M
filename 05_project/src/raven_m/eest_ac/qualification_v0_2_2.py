"""Bounded real-model full-envelope qualification for EEST-AC v0.2.2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from raven_m.eest_ac.action_contract_v0_2_2 import (
    DecisionEnvelopeError,
    ParsedDecisionV022,
    assert_not_identical_invalid_repair,
    build_repair_prompt,
    parse_decision_v0_2_2,
)
from raven_m.models.transformers_client import ModelCall, TransformersClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnvelopeQualificationFailure(RuntimeError):
    def __init__(self, code: str, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(f"{code}:{message}")
        self.code = code
        self.message = message
        self.cause = cause


@dataclass(frozen=True)
class EnvelopeQualificationDecision:
    parsed: ParsedDecisionV022
    accepted_stage: str
    initial_direct_command_pass: bool
    initial_accepted_after_action_normalization: bool
    repair_used: bool
    repair_reason_plane: str | None
    initial_error: dict[str, Any] | None

    def record(self) -> dict[str, Any]:
        return {
            "decision": self.parsed.decision,
            "control_plane": self.parsed.control_plane,
            "control_plane_valid": self.parsed.control_plane_valid,
            "canonicalization": self.parsed.canonicalization.record() if self.parsed.canonicalization else None,
            "intent_metadata": self.parsed.intent_metadata.record(),
            "accepted_stage": self.accepted_stage,
            "initial_direct_command_pass": self.initial_direct_command_pass,
            "initial_accepted_after_action_normalization": self.initial_accepted_after_action_normalization,
            "metadata_normalized": self.parsed.intent_metadata.metadata_normalized,
            "repair_used": self.repair_used,
            "repair_reason_plane": self.repair_reason_plane,
            "initial_error": self.initial_error,
            "schema_sha256": self.parsed.schema_sha256,
            "contract_sha256": self.parsed.contract_sha256,
        }


class DecisionEnvelopeQualificationDeciderV022:
    """Use at most initial + one schema/control-plane repair under 256 tokens."""

    def __init__(
        self,
        *,
        client: TransformersClient,
        system_prompt: str,
        max_new_tokens: int = 256,
    ) -> None:
        if max_new_tokens != 256:
            raise ValueError("v0.2.2 qualification freezes max_new_tokens=256.")
        self.client = client
        self.system_prompt = system_prompt
        self.max_new_tokens = max_new_tokens

    def _call(
        self,
        *,
        image_path: Any,
        user_prompt: str,
        episode_id: str,
        label: str,
        role: str,
        calls: list[dict[str, Any]],
        attempts: list[dict[str, Any]],
        record_call: Callable[[dict[str, Any]], None],
    ) -> ModelCall:
        if len(attempts) >= 2:
            raise EnvelopeQualificationFailure("QUALIFICATION_CALL_BUDGET", "More than two model attempts requested.")
        attempt = {
            "index": len(attempts) + 1,
            "role": role,
            "label": label,
            "started_at_utc": _utc_now(),
            "completed": False,
        }
        attempts.append(attempt)
        try:
            call = self.client.generate(
                image_path=image_path,
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                episode_id=episode_id,
                call_label=label,
                max_tokens=self.max_new_tokens,
            )
            record = {"role": role, **call.audit_record()}
            calls.append(record)
            record_call(record)
            attempt.update(completed=True, call_id=call.call_id)
            return call
        except Exception as exc:
            attempt.update(error_type=type(exc).__name__, error=str(exc))
            raise

    @staticmethod
    def _error_record(error: DecisionEnvelopeError) -> dict[str, Any]:
        return {
            "code": error.code,
            "message": error.message,
            "validation_errors": list(error.validation_errors),
            "rejected_action": error.rejected_action,
            "rejected_control": error.rejected_control,
            "action_was_invalid": error.action_was_invalid,
            "authority_plane": error.authority_plane,
            "repair_allowed": error.repair_allowed,
            "fingerprint_fields": list(error.fingerprint_fields),
        }

    def decide(
        self,
        *,
        image_path: Any,
        user_prompt: str,
        episode_id: str,
        calls: list[dict[str, Any]],
        attempts: list[dict[str, Any]],
        record_call: Callable[[dict[str, Any]], None],
        allowed_citations: Iterable[str] = (),
    ) -> EnvelopeQualificationDecision:
        initial = self._call(
            image_path=image_path,
            user_prompt=user_prompt,
            episode_id=episode_id,
            label="envelope_qualification_initial",
            role="envelope_qualification_initial",
            calls=calls,
            attempts=attempts,
            record_call=record_call,
        )
        try:
            parsed = parse_decision_v0_2_2(initial.content, allowed_citations=allowed_citations)
        except DecisionEnvelopeError as initial_error:
            if not initial_error.repair_allowed:
                raise EnvelopeQualificationFailure(
                    initial_error.code,
                    initial_error.message,
                    cause=initial_error,
                ) from initial_error
            repair_prompt = build_repair_prompt(
                original_user_prompt=user_prompt,
                raw_output=initial.content,
                error=initial_error,
            )
            repaired = self._call(
                image_path=image_path,
                user_prompt=repair_prompt,
                episode_id=episode_id,
                label="envelope_qualification_control_repair",
                role="envelope_qualification_control_repair",
                calls=calls,
                attempts=attempts,
                record_call=record_call,
            )
            try:
                assert_not_identical_invalid_repair(
                    initial_raw=initial.content,
                    repaired_raw=repaired.content,
                    initial_error=initial_error,
                )
                parsed = parse_decision_v0_2_2(repaired.content, allowed_citations=allowed_citations)
            except DecisionEnvelopeError as repair_error:
                raise EnvelopeQualificationFailure(
                    repair_error.code,
                    repair_error.message,
                    cause=repair_error,
                ) from repair_error
            return EnvelopeQualificationDecision(
                parsed=parsed,
                accepted_stage="control_repair",
                initial_direct_command_pass=False,
                initial_accepted_after_action_normalization=False,
                repair_used=True,
                repair_reason_plane=initial_error.authority_plane,
                initial_error=self._error_record(initial_error),
            )
        normalized = bool(parsed.canonicalization and parsed.canonicalization.changed)
        return EnvelopeQualificationDecision(
            parsed=parsed,
            accepted_stage="initial_action_normalized" if normalized else "initial_direct",
            initial_direct_command_pass=not normalized,
            initial_accepted_after_action_normalization=True,
            repair_used=False,
            repair_reason_plane=None,
            initial_error=None,
        )
