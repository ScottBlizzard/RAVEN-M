from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from android_env.proto import adb_pb2

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    semantic_ui_snapshot,
)
from raven_m.history.policies import (
    CompletionAdjudication,
    HistoryPolicy,
    RavenMemoryPolicy,
)
from raven_m.models.transformers_client import ModelCall


class RepeatingSaveClient:
    def generate(self, **kwargs) -> ModelCall:
        decision = {
            "status": "continue",
            "action": {"type": "tap", "x": 0.94, "y": 0.085},
            "expected_outcome": "The event is saved.",
            "decision_summary": "Tap save.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class PickerBackThenDrawerClient:
    def generate(self, **kwargs) -> ModelCall:
        repair = kwargs["call_label"].endswith("_repair")
        action = (
            {"type": "tap", "x": 0.07, "y": 0.08}
            if repair
            else {"type": "press_back"}
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The destination navigation changes.",
            "decision_summary": "Navigate within the destination picker.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class EmptyPickerWaitThenDrawerClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        repair = kwargs["call_label"].endswith("_repair")
        action = (
            {"type": "tap", "x": 0.07, "y": 0.08}
            if repair
            else {"type": "wait", "duration_ms": 1000}
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "Destination navigation advances.",
            "decision_summary": "Navigate to the requested destination.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class EmptyPickerUnboundTapThenDrawerClient(
    EmptyPickerWaitThenDrawerClient
):
    def generate(self, **kwargs) -> ModelCall:
        call = super().generate(**kwargs)
        if kwargs["call_label"].endswith("_repair"):
            return call
        decision = json.loads(call.content)
        decision["action"] = {"type": "tap", "x": 0.385, "y": 0.075}
        decision["expected_outcome"] = "The destination is confirmed."
        decision["decision_summary"] = (
            "Tap the title area to confirm the destination before moving."
        )
        return ModelCall(
            call_id=call.call_id,
            episode_id=call.episode_id,
            idempotency_key=call.idempotency_key,
            image_sha256=call.image_sha256,
            image_sha256s=call.image_sha256s,
            prompt_sha256=call.prompt_sha256,
            request_sha256=call.request_sha256,
            response_sha256=call.response_sha256,
            content=json.dumps(decision),
            usage=call.usage,
            raven_meta=call.raven_meta,
        )


class OpenRootsDrawerUnboundThenRowClient:
    def __init__(self, *, valid_repair: bool = True) -> None:
        self.valid_repair = valid_repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        repair = kwargs["call_label"].endswith("_repair")
        action = (
            (
                {"type": "tap", "x": 0.30, "y": 0.76}
                if self.valid_repair
                else {"type": "swipe", "x": 0.5, "y": 0.8,
                      "x2": 0.5, "y2": 0.2, "duration_ms": 500}
            )
            if repair
            else {"type": "tap", "x": 0.08, "y": 0.08}
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The requested storage root opens.",
            "decision_summary": "Navigate through the visible roots drawer.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class DrawerToFreshRootClient:
    def generate(self, **kwargs) -> ModelCall:
        label = kwargs["call_label"]
        assert label in {"step_000_initial", "step_001_initial"}
        action = (
            {"type": "tap", "x": 0.30, "y": 0.76}
            if label == "step_000_initial"
            else {"type": "tap", "x": 0.68, "y": 0.50}
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "Navigation advances toward Music.",
            "decision_summary": "Tap the visible task-relevant Files row.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class CriticRejectedCommitThenDrawerClient:
    def __init__(self, *, valid_repair: bool = True) -> None:
        self.valid_repair = valid_repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.endswith("_repair"):
            action = (
                {"type": "tap", "x": 0.065, "y": 0.08}
                if self.valid_repair
                else {"type": "press_back"}
            )
            summary = "Open the visible roots navigation drawer."
            outcome = "The storage roots drawer opens."
        else:
            action = {"type": "tap", "x": 0.385, "y": 0.945}
            summary = "Tap the Move button to commit the pending operation."
            outcome = "The file is moved to the current destination."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": outcome,
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class RejectWrongDestinationCommitPolicy(HistoryPolicy):
    variant = "M0"

    def adjudicate_action(self, decision, **kwargs) -> CompletionAdjudication:
        del kwargs
        action = decision.get("action", {})
        if (
            action.get("type") == "tap"
            and action.get("y", 0) > 0.9
        ):
            return CompletionAdjudication(
                accepted=False,
                record={
                    "schema_version": "action_adjudication.v1",
                    "trigger": "consequential_action_candidate",
                    "output": {
                        "schema_version": "critic.v1",
                        "verdict": "reobserve",
                        "recommended_constraint": (
                            "confirm Ringtones instead of Downloads"
                        ),
                    },
                    "error": None,
                    "model_call_ids": [],
                },
                error=(
                    "Action critic rejected commit: confirm Ringtones "
                    "instead of Downloads"
                ),
            )
        return CompletionAdjudication()


class CommitThenRepeatClient:
    def __init__(self, *, valid_repair: bool = True) -> None:
        self.valid_repair = valid_repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.startswith("step_000"):
            action = {"type": "tap", "x": 0.40, "y": 0.94}
            summary = "Commit the pending move."
        elif label.endswith("_repair"):
            action = (
                {"type": "press_back"}
                if self.valid_repair
                else {"type": "wait", "duration_ms": 1000}
            )
            summary = "Dismiss the repeated transfer UI safely."
        else:
            action = {"type": "tap", "x": 0.67, "y": 0.344}
            summary = "Choose Move to again."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The file operation advances.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class CommitThenPrematureDoneClient:
    def __init__(self, *, valid_repair: bool = True) -> None:
        self.valid_repair = valid_repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.startswith("step_000"):
            status = "continue"
            action = {"type": "tap", "x": 0.40, "y": 0.94}
            summary = "Commit the pending move."
            evidence = []
        elif label.endswith("_repair"):
            status = "continue"
            action = (
                {"type": "press_back"}
                if self.valid_repair
                else {"type": "wait", "duration_ms": 1000}
            )
            summary = "Leave the stale source search view safely."
            evidence = []
        else:
            status = "done"
            action = None
            summary = "Declare the move complete before destination verification."
            evidence = [
                {
                    "claim": "The file was moved to Ringtones.",
                    "evidence": "direct_screen",
                    "memory_ids": [],
                }
            ]
        decision = {
            "status": status,
            "action": action,
            "expected_outcome": "The file operation advances.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": evidence,
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class RejectPrematurePostCommitCompletionPolicy(HistoryPolicy):
    variant = "M0"

    def adjudicate_completion(self, decision, **kwargs) -> CompletionAdjudication:
        del kwargs
        if decision.get("status") != "done":
            return CompletionAdjudication()
        return CompletionAdjudication(
            accepted=False,
            record={
                "schema_version": "completion_adjudication.v2",
                "trigger": "completion_candidate",
                "output": {
                    "schema_version": "critic.v1",
                    "verdict": "reject_completion",
                    "recommended_constraint": (
                        "reobserve while checking the Ringtones folder"
                    ),
                },
                "error": None,
                "model_call_ids": [],
            },
            error=(
                "Completion critic rejected completion: reobserve while "
                "checking the Ringtones folder"
            ),
        )


class PostCommitVerificationClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.startswith("step_000"):
            action = {"type": "tap", "x": 0.38, "y": 0.945}
            summary = "Tap the MOVE button to confirm the move."
            outcome = "The file is moved to the selected destination."
        else:
            action = {"type": "tap", "x": 0.25, "y": 0.678}
            summary = "Tap Ringtones to confirm the moved file is present."
            outcome = "The Ringtones folder opens for verification."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": outcome,
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class CommitThenSourceBrowseClient:
    def __init__(
        self,
        *,
        valid_repair: bool = True,
        repair_summary: str | None = None,
        repair_expected_outcome: str | None = None,
        invalid_repair_completion_evidence: bool = False,
    ) -> None:
        self.valid_repair = valid_repair
        self.repair_summary = repair_summary
        self.repair_expected_outcome = repair_expected_outcome
        self.invalid_repair_completion_evidence = (
            invalid_repair_completion_evidence
        )
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.startswith("step_000"):
            action = {"type": "tap", "x": 0.38, "y": 0.945}
            summary = "Tap the MOVE button to confirm the move."
        elif label.endswith("_repair"):
            action = (
                {"type": "press_back"}
                if self.valid_repair
                else {"type": "tap", "x": 0.82, "y": 0.08}
            )
            summary = self.repair_summary or (
                "Leave the exact source directory after the move."
            )
        else:
            action = {
                "type": "swipe",
                "x": 0.5,
                "y": 0.8,
                "x2": 0.5,
                "y2": 0.2,
                "duration_ms": 500,
            }
            summary = "Swipe up in Music to search for the moved file."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": (
                self.repair_expected_outcome
                if label.endswith("_repair")
                and self.repair_expected_outcome is not None
                else "The file workflow advances."
            ),
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": (
                [
                    {
                        "claim": "The file was moved.",
                        "evidence": "direct_screen",
                        "memory_ids": [],
                    }
                ]
                if (
                    label.endswith("_repair")
                    and self.invalid_repair_completion_evidence
                )
                else []
            ),
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class NavigationOverrideProbePolicy(HistoryPolicy):
    variant = "M0"

    def __init__(self) -> None:
        self.candidates: list[bool | None] = []

    def adjudicate_action(
        self,
        decision,
        **kwargs,
    ) -> CompletionAdjudication:
        del decision
        candidate = kwargs["consequential_action_candidate"]
        self.candidates.append(candidate)
        if candidate is not None:
            return CompletionAdjudication()
        return CompletionAdjudication(
            accepted=False,
            record={
                "schema_version": "action_adjudication.v1",
                "trigger": "consequential_action_candidate",
                "output": {
                    "schema_version": "critic.v1",
                    "verdict": "reobserve",
                    "recommended_constraint": (
                        "confirm the Ringtones folder is selected"
                    ),
                },
                "error": None,
                "model_call_ids": [],
            },
            error=(
                "Action critic rejected commit: confirm the Ringtones "
                "folder is selected"
            ),
        )


class WrongFileThenSearchClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.endswith("_repair"):
            action = {"type": "tap", "x": 0.83, "y": 0.08}
            summary = "Open Search to isolate the exact filename."
        else:
            action = {
                "type": "long_press",
                "x": 0.75,
                "y": 0.51,
                "duration_ms": 800,
            }
            summary = "Long-press a truncated same-prefix file."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The exact target becomes verifiable.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class FocusedInputThenSafeTextClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        action = {
            "type": "type_text",
            "text": "nature_sounds.mp3",
            "text_origin": "task_literal",
            "source_memory_ids": [],
            "clear_text": False,
        }
        if not label.endswith("_repair"):
            action.update(x=0.5, y=0.5, clear_text=True)
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The exact filename appears in Search.",
            "decision_summary": "Type the exact filename into focused Search.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class UniqueSearchCoordinateThenSafeTextClient(
    FocusedInputThenSafeTextClient
):
    def generate(self, **kwargs) -> ModelCall:
        call = super().generate(**kwargs)
        if kwargs["call_label"].endswith("_repair"):
            return call
        value = json.loads(call.content)
        value["action"]["x"] = 0.5
        value["action"]["y"] = 0.075
        return ModelCall(
            call_id=call.call_id,
            episode_id=call.episode_id,
            idempotency_key=call.idempotency_key,
            image_sha256=call.image_sha256,
            image_sha256s=call.image_sha256s,
            prompt_sha256=call.prompt_sha256,
            request_sha256=call.request_sha256,
            response_sha256=call.response_sha256,
            content=json.dumps(value),
            usage=call.usage,
            raven_meta=call.raven_meta,
        )


class UnboundTextThenActivateInputClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.endswith("_repair"):
            action = {"type": "tap", "x": 0.82, "y": 0.075}
            summary = "Tap Search to activate its input."
        else:
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": True,
                "x": 0.5,
                "y": 0.075,
            }
            summary = "Type the exact filename into the inactive top bar."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "A Search input becomes active.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class MalformedCoordinateThenActivateInputClient:
    def __init__(self, *, safe_repair: bool = True) -> None:
        self.safe_repair = safe_repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label == "step_000_initial":
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": True,
                "x": 0.5,
                "y": 75,
            }
            summary = "Enter the requested filename in Search."
        elif label == "step_000_repair" and self.safe_repair:
            action = {"type": "tap", "x": 0.5, "y": 0.075}
            summary = "Activate the visible Search input safely."
        elif label == "step_000_repair":
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": True,
                "x": 0.5,
                "y": 0.075,
            }
            summary = "Retry typing directly in the unfocused Search input."
        else:
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": False,
            }
            summary = "Type in the now-active Search input."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The exact filename appears in Search.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class RepeatedActivationRecoveryClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        state_delta = []
        if label == "step_000_initial":
            action = {"type": "tap", "x": 0.5, "y": 0.5}
            summary = "Tap Search to activate the empty input."
            state_delta = [
                {
                    "kind": "progress",
                    "subject": "search",
                    "predicate": "activation",
                    "object": "requested",
                    "natural_language": "The Search input is activated.",
                    "evidence": "direct_screen",
                    "confidence": 0.9,
                }
            ]
        elif label == "step_001_initial":
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "x": 0.5,
                "y": 0.5,
                "clear_text": True,
            }
            summary = "Enter the exact filename into Search."
        elif label == "step_001_repair":
            action = {"type": "tap", "x": 0.5, "y": 0.5}
            summary = "Repeat the bounded activation tap before typing."
        else:
            assert label == "step_002_initial"
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": False,
            }
            summary = "Enter the exact filename into the activated Search."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The exact filename appears in Search.",
            "decision_summary": summary,
            "state_delta": state_delta,
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class PostActivationClearTextClient:
    def __init__(self, *, valid_repair: bool = True) -> None:
        self.requests: list[dict] = []
        self.valid_repair = valid_repair

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label == "step_000_repair":
            action = {"type": "tap", "x": 0.5, "y": 0.075}
            summary = "Activate the visible Search input."
        else:
            action = {
                "type": "type_text",
                "text": "nature_sounds.mp3",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "clear_text": not (
                    label == "step_001_repair" and self.valid_repair
                ),
            }
            if label != "step_001_repair":
                action.update(x=0.5, y=0.075)
            summary = "Enter the exact filename into Search."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The exact filename appears in Search.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class VisibleControlActivationRetryClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        assert label in {
            "step_000_initial",
            "step_001_initial",
            "step_001_repair",
        }
        decision = {
            "status": "continue",
            "action": {"type": "tap", "x": 0.87, "y": 0.835},
            "expected_outcome": "The contact creation form opens.",
            "decision_summary": "Tap Create contact to open the form.",
            "state_delta": [
                {
                    "kind": "progress",
                    "subject": "contact_form",
                    "predicate": "state",
                    "object": "opening",
                    "natural_language": (
                        "The contact creation form is opening."
                    ),
                    "evidence": "direct_screen",
                    "confidence": 0.9,
                }
            ],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class FabricatedTaskLiteralThenPhoneClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.endswith("_repair"):
            action = {"type": "tap", "x": 0.45, "y": 0.60}
            summary = "Activate Phone before entering the requested number."
        else:
            action = {
                "type": "type_text",
                "text": "Tech Solutions",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "x": 0.45,
                "y": 0.55,
                "clear_text": True,
            }
            summary = "Invent a company value not present in the task."
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The selected contact field is updated.",
            "decision_summary": summary,
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class FabricatedTaskLiteralThenBackClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        action = (
            {"type": "press_back"}
            if label.endswith("_repair")
            else {
                "type": "type_text",
                "text": "Tech Solutions",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "x": 0.45,
                "y": 0.55,
                "clear_text": True,
            }
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The contact form remains safe.",
            "decision_summary": "Recover without filling an optional field.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class PhoneInCompanyThenPhoneClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        y = 0.60 if label.endswith("_repair") else 0.55
        decision = {
            "status": "continue",
            "action": {
                "type": "type_text",
                "text": "+17634322348",
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "x": 0.45,
                "y": y,
                "clear_text": True,
            },
            "expected_outcome": "The phone number is entered.",
            "decision_summary": "Enter the requested phone number.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class KeyboardSwipeThenBackClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        action = (
            {"type": "press_back"}
            if label.endswith("_repair")
            else {
                "type": "swipe",
                "x": 0.5,
                "y": 0.75,
                "x2": 0.5,
                "y2": 0.3,
                "duration_ms": 500,
            }
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "The keyboard is dismissed safely.",
            "decision_summary": "Dismiss the keyboard before navigating.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class DestinationPickerEnv:
    def __init__(self) -> None:
        self.execute_count = 0

    def reset(self, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        pass

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    text="CANCEL",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(y_min=0.91, y_max=0.98),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="MOVE",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(y_min=0.91, y_max=0.98),
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1


class EmptyDestinationPickerEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        state = super().get_state(wait_to_stabilize)
        state.ui_elements.extend(
            [
                SimpleNamespace(
                    package_name="files",
                    content_description="Show roots",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.10,
                        y_min=0.05,
                        y_max=0.11,
                    ),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="No items",
                    is_visible=True,
                    is_enabled=True,
                ),
            ]
        )
        return state


class OpenFilesRootsDrawerEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        labels = [
            "Recent",
            "Images",
            "Videos",
            "Audio",
            "Documents",
            "Downloads",
            "sdk_gphone64_x86_64",
        ]
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    text=label,
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.02,
                        x_max=0.58,
                        y_min=0.12 + index * 0.10,
                        y_max=0.20 + index * 0.10,
                    ),
                )
                for index, label in enumerate(labels)
            ],
        )


class DrawerToStaleThenFreshRootEnv(DestinationPickerEnv):
    foreground_activity_name = (
        "com.google.android.documentsui/"
        "com.android.documentsui.files.FilesActivity"
    )

    def __init__(self) -> None:
        super().__init__()
        self.post_storage_observation_count = 0

    @staticmethod
    def _drawer_elements() -> list[SimpleNamespace]:
        labels = [
            "Recent",
            "Images",
            "Videos",
            "Audio",
            "Documents",
            "Downloads",
            "sdk_gphone64_x86_64",
        ]
        return [
            SimpleNamespace(
                package_name="com.google.android.documentsui",
                text=label,
                is_visible=True,
                is_enabled=True,
                bbox=SimpleNamespace(
                    x_min=0.02,
                    x_max=0.58,
                    y_min=0.12 + index * 0.10,
                    y_max=0.20 + index * 0.10,
                ),
            )
            for index, label in enumerate(labels)
        ]

    @staticmethod
    def _root_elements() -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                package_name="com.google.android.documentsui",
                text="Music",
                is_visible=True,
                is_enabled=True,
                is_clickable=False,
                is_editable=False,
                bbox=SimpleNamespace(
                    x_min=0.52,
                    x_max=0.90,
                    y_min=0.44,
                    y_max=0.56,
                ),
            ),
            SimpleNamespace(
                package_name="com.google.android.documentsui",
                text="Ringtones",
                is_visible=True,
                is_enabled=True,
                is_clickable=False,
                is_editable=False,
                bbox=SimpleNamespace(
                    x_min=0.05,
                    x_max=0.45,
                    y_min=0.72,
                    y_max=0.84,
                ),
            ),
        ]

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        if self.execute_count == 0:
            pixels = np.zeros((100, 100, 3), dtype=np.uint8)
            elements = self._drawer_elements()
        elif self.execute_count == 1:
            self.post_storage_observation_count += 1
            if self.post_storage_observation_count == 1:
                pixels = np.zeros((100, 100, 3), dtype=np.uint8)
                elements = self._drawer_elements()
            elif self.post_storage_observation_count == 2:
                pixels = np.full((100, 100, 3), 255, dtype=np.uint8)
                elements = self._drawer_elements()
            else:
                pixels = np.full((100, 100, 3), 255, dtype=np.uint8)
                elements = self._root_elements()
        else:
            pixels = np.full((100, 100, 3), 127, dtype=np.uint8)
            elements = self._root_elements()
        return SimpleNamespace(pixels=pixels, ui_elements=elements)

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1


class CriticRejectedDestinationPickerEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    content_description="Show roots",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.10,
                        y_min=0.05,
                        y_max=0.11,
                    ),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="Downloads",
                    is_visible=True,
                    is_enabled=True,
                ),
                SimpleNamespace(
                    package_name="files",
                    text="No items",
                    is_visible=True,
                    is_enabled=True,
                ),
                SimpleNamespace(
                    package_name="files",
                    text="CANCEL",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.26,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="MOVE",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.28,
                        x_max=0.50,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        assert action.x == 6
        assert action.y == 8
        self.execute_count += 1


class PostCommitEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        if self.execute_count == 0:
            elements = [
                SimpleNamespace(
                    package_name="files",
                    text="CANCEL",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.26,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="MOVE",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.28,
                        x_max=0.50,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
            ]
        else:
            elements = [
                SimpleNamespace(
                    package_name="files",
                    text="Move to…",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.55,
                        x_max=0.95,
                        y_min=0.31,
                        y_max=0.37,
                    ),
                )
            ]
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                min(self.execute_count, 1),
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        if self.execute_count == 0:
            assert action.action_type == "click"
        else:
            assert action.action_type == "navigate_back"
        self.execute_count += 1


class PostCommitVerificationEnv(DestinationPickerEnv):
    def __init__(
        self,
        *,
        destination_package: str = "com.google.android.documentsui",
    ) -> None:
        super().__init__()
        self.destination_package = destination_package

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        if self.execute_count == 0:
            elements = [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="CANCEL",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.26,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="MOVE",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.28,
                        x_max=0.50,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
            ]
        elif self.execute_count == 1:
            elements = [
                SimpleNamespace(
                    package_name=self.destination_package,
                    text="Ringtones",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=False,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.06,
                        x_max=0.49,
                        y_min=0.63,
                        y_max=0.72,
                    ),
                ),
            ]
        else:
            elements = [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="nature_sounds.mp3",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=True,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.06,
                        x_max=0.49,
                        y_min=0.20,
                        y_max=0.30,
                    ),
                )
            ]
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                min(self.execute_count, 2),
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1


class PostCommitSourceExitEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        if self.execute_count == 0:
            elements = [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="CANCEL",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.03,
                        x_max=0.26,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="MOVE",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.28,
                        x_max=0.50,
                        y_min=0.91,
                        y_max=0.98,
                    ),
                ),
            ]
        elif self.execute_count == 1:
            elements = [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Music",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=False,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.15,
                        x_max=0.55,
                        y_min=0.05,
                        y_max=0.11,
                    ),
                )
            ]
        else:
            elements = [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Music",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=True,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.55,
                        x_max=0.90,
                        y_min=0.38,
                        y_max=0.46,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Ringtones",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=True,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.06,
                        x_max=0.49,
                        y_min=0.63,
                        y_max=0.72,
                    ),
                ),
            ]
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                min(self.execute_count, 2),
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        if self.execute_count == 0:
            assert action.action_type == "click"
        else:
            assert action.action_type == "navigate_back"
        self.execute_count += 1


class ExactTargetGridEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    text="nature_sounds_backup.mp3",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.62,
                        x_max=0.91,
                        y_min=0.55,
                        y_max=0.60,
                    ),
                ),
                SimpleNamespace(
                    package_name="files",
                    text="nature_sounds.mp3",
                    is_visible=True,
                    is_enabled=True,
                    bbox=SimpleNamespace(
                        x_min=0.62,
                        x_max=0.91,
                        y_min=0.80,
                        y_max=0.85,
                    ),
                ),
            ],
        )


class FocusedInputEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    text="",
                    hint_text="Search",
                    class_name="android.widget.EditText",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=True,
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "input_text"
        assert action.x is None
        assert action.y is None
        assert action.clear_text is False
        assert action.text == "nature_sounds.mp3"
        self.execute_count += 1


class SoftKeyboardOnlyInputEnv(FocusedInputEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Search",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                ),
                SimpleNamespace(
                    package_name="com.google.android.inputmethod.latin",
                    text="q",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                ),
            ],
        )


class UniqueFocusedSearchEnv(FocusedInputEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="",
                    hint_text="Search",
                    class_name="android.widget.EditText",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=True,
                    bbox=SimpleNamespace(
                        x_min=0.20,
                        x_max=0.90,
                        y_min=0.05,
                        y_max=0.10,
                    ),
                ),
            ],
        )


class UnboundTextTargetEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Music",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.15,
                        x_max=0.45,
                        y_min=0.05,
                        y_max=0.1,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    content_description="Search",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.78,
                        x_max=0.86,
                        y_min=0.05,
                        y_max=0.1,
                    ),
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        assert action.x in {81, 82}
        assert action.y in {7, 8}
        self.execute_count += 1


class UnfocusedEditableSearchEnv(UnboundTextTargetEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="",
                    hint_text="Search",
                    class_name="android.widget.EditText",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.20,
                        x_max=0.90,
                        y_min=0.05,
                        y_max=0.10,
                    ),
                ),
            ],
        )


class RepeatedActivationInputEnv(DestinationPickerEnv):
    def __init__(self) -> None:
        super().__init__()
        self.tap_count = 0
        self.input_count = 0
        self.value = ""

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                int(bool(self.value)),
                dtype=np.uint8,
            ),
            ui_elements=[
                SimpleNamespace(
                    package_name="files",
                    text=self.value,
                    hint_text="Search",
                    class_name="android.widget.EditText",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.20,
                        x_max=0.80,
                        y_min=0.20,
                        y_max=0.80,
                    ),
                ),
            ],
        )

    def execute_action(self, action) -> None:
        self.execute_count += 1
        if action.action_type == "click":
            assert action.x == 50
            assert action.y == 50
            self.tap_count += 1
            return
        assert action.action_type == "input_text"
        assert action.x is None
        assert action.y is None
        assert action.clear_text is False
        assert action.text == "nature_sounds.mp3"
        self.input_count += 1
        self.value = action.text


class PostActivationKeyboardOnlyEnv(DestinationPickerEnv):
    def __init__(self) -> None:
        super().__init__()
        self.value = ""

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        elements = [
            SimpleNamespace(
                package_name="com.google.android.documentsui",
                text="",
                hint_text="Search",
                class_name="android.widget.EditText",
                is_visible=True,
                is_enabled=True,
                is_editable=True,
                is_focused=False,
                bbox=SimpleNamespace(
                    x_min=0.20,
                    x_max=0.90,
                    y_min=0.05,
                    y_max=0.10,
                ),
            ),
        ]
        if self.execute_count:
            elements.append(
                SimpleNamespace(
                    package_name="com.google.android.inputmethod.latin",
                    text="q",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.0,
                        x_max=1.0,
                        y_min=0.55,
                        y_max=1.0,
                    ),
                )
            )
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                self.execute_count,
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        if self.execute_count == 0:
            assert action.action_type == "click"
            assert action.x == 50
            assert action.y in {7, 8}
        else:
            assert action.action_type == "input_text"
            assert action.x is None
            assert action.y is None
            assert action.clear_text is False
            assert action.text == "nature_sounds.mp3"
            self.value = action.text
        self.execute_count += 1


class VisibleControlActivationRetryEnv(DestinationPickerEnv):
    def __init__(self) -> None:
        super().__init__()
        self.tap_count = 0
        self.form_open = False

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        if self.form_open:
            elements = [
                SimpleNamespace(
                    package_name="contacts",
                    hint_text="First name",
                    class_name="android.widget.EditText",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=True,
                    is_editable=True,
                    bbox=SimpleNamespace(
                        x_min=0.20,
                        x_max=0.80,
                        y_min=0.20,
                        y_max=0.30,
                    ),
                )
            ]
        else:
            elements = [
                SimpleNamespace(
                    package_name="contacts",
                    content_description="Create contact",
                    class_name="android.widget.Button",
                    is_visible=True,
                    is_enabled=True,
                    is_clickable=True,
                    is_editable=False,
                    bbox=SimpleNamespace(
                        x_min=0.80,
                        x_max=0.94,
                        y_min=0.78,
                        y_max=0.89,
                    ),
                )
            ]
        return SimpleNamespace(
            pixels=np.full(
                (100, 100, 3),
                int(self.form_open),
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1
        self.tap_count += 1
        if self.tap_count == 2:
            self.form_open = True


class ContactFieldsEnv(DestinationPickerEnv):
    def __init__(self) -> None:
        super().__init__()
        self.focus_click_count = 0
        self.atomic_clear_and_type_commands: list[list[str]] = []
        parent = self

        class Controller:
            def execute_adb_call(self, request):
                command_type = request.WhichOneof("command")
                if command_type == "generic":
                    command = list(request.generic.args)
                    assert command[:13] == [
                        "shell",
                        "input",
                        "keycombination",
                        "113",
                        "29",
                        "&&",
                        "input",
                        "keyevent",
                        "67",
                        "&&",
                        "sleep",
                        "1",
                        "&&",
                    ]
                    assert command[13:] == [
                        "input",
                        "text",
                        "+17634322348",
                    ]
                    parent.atomic_clear_and_type_commands.append(command)
                    parent.execute_count += 1
                else:
                    assert command_type == "press_button"
                    assert (
                        request.press_button.button
                        == adb_pb2.AdbRequest.PressButton.ENTER
                    )
                return adb_pb2.AdbResponse(
                    status=adb_pb2.AdbResponse.Status.OK
                )

        self.controller = Controller()

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="contacts",
                    text="",
                    hint_text="Company",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=True,
                    bbox=SimpleNamespace(
                        x_min=0.10,
                        x_max=0.80,
                        y_min=0.50,
                        y_max=0.57,
                    ),
                ),
                SimpleNamespace(
                    package_name="contacts",
                    text="",
                    hint_text="Phone",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.10,
                        x_max=0.80,
                        y_min=0.58,
                        y_max=0.65,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.inputmethod.latin",
                    text="q",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        assert action.x == 45
        assert action.y == 59
        self.focus_click_count += 1


class ContactFieldsNoKeyboardEnv(ContactFieldsEnv):
    def get_state(self, wait_to_stabilize: bool):
        state = super().get_state(wait_to_stabilize)
        state.ui_elements = [
            element
            for element in state.ui_elements
            if element.package_name
            != "com.google.android.inputmethod.latin"
        ]
        return state


class KeyboardSwipeEnv(DestinationPickerEnv):
    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((100, 100, 3), dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name="contacts",
                    text="",
                    hint_text="Company",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=True,
                    is_focused=True,
                    bbox=SimpleNamespace(
                        x_min=0.10,
                        x_max=0.80,
                        y_min=0.50,
                        y_max=0.57,
                    ),
                ),
                SimpleNamespace(
                    package_name="com.google.android.inputmethod.latin",
                    text="",
                    is_visible=True,
                    is_enabled=True,
                    is_editable=False,
                    is_focused=False,
                    bbox=SimpleNamespace(
                        x_min=0.0,
                        x_max=1.0,
                        y_min=0.63,
                        y_max=1.0,
                    ),
                ),
            ],
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "navigate_back"
        self.execute_count += 1


class FilesTask:
    name = "FilesMoveFile"
    goal = (
        "Move nature_sounds.mp3 from the requested source to the requested "
        "folder."
    )
    params = {
        "file_name": "nature_sounds.mp3",
        "destination_folder": "Ringtones",
        "source_folder": "Music",
    }

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


class ContactTask:
    name = "ContactsAddContact"
    goal = (
        "Create a new contact for Sofija Martin. Their number is "
        "+17634322348."
    )
    params = {
        "name": "Sofija Martin",
        "number": "+17634322348",
    }

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


class SemanticFailureEnv:
    def __init__(self) -> None:
        self.state_call_count = 0
        self.execute_count = 0

    def reset(self, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        pass

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.state_call_count += 1
        elements = [
            SimpleNamespace(
                package_name="calendar",
                text="Meeting with Marketing",
                resource_id="title",
            ),
            SimpleNamespace(
                package_name="calendar",
                text="08:00",
                resource_id="start_time",
            ),
            SimpleNamespace(
                package_name="calendar",
                text="00:30",
                resource_id="end_time",
            ),
            SimpleNamespace(
                package_name="com.android.systemui",
                text=f"15:{40 + self.state_call_count}",
            ),
        ]
        if self.state_call_count == 2:
            elements.append(
                SimpleNamespace(
                    package_name="calendar",
                    text="The event cannot end earlier than it starts",
                    class_name="android.widget.Toast",
                )
            )
        return SimpleNamespace(
            pixels=np.full(
                (32, 24, 3),
                self.state_call_count,
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1


class CalendarTask:
    name = "SimpleCalendarAddOneEvent"
    goal = "Create the requested calendar event."
    params = {}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


class DelayedAccessibilityEnv:
    def __init__(self) -> None:
        self.calls = 0

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.calls += 1
        elements = (
            []
            if self.calls < 3
            else [
                SimpleNamespace(
                    package_name="contacts",
                    text="No contacts yet",
                    resource_id="empty_state",
                )
            ]
        )
        return SimpleNamespace(
            pixels=np.full((16, 12, 3), self.calls, dtype=np.uint8),
            ui_elements=elements,
        )


class StaleAccessibilityEnv:
    foreground_activity_name = "expense/expense.MainActivity"

    def __init__(self) -> None:
        self.calls = 0

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.calls += 1
        package = "calendar" if self.calls == 1 else "expense"
        return SimpleNamespace(
            pixels=np.full((16, 12, 3), self.calls, dtype=np.uint8),
            ui_elements=[
                SimpleNamespace(
                    package_name=package,
                    text="Home",
                    resource_id="home",
                )
            ],
        )


class RecoverableAccessibilityController:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def refresh_env(self) -> None:
        self.refresh_calls += 1


class RecoverableAccessibilityEnv:
    foreground_activity_name = "files/files.MainActivity"

    def __init__(self) -> None:
        self.calls = 0
        self.controller = RecoverableAccessibilityController()

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.calls += 1
        elements = []
        if self.controller.refresh_calls:
            elements = [
                SimpleNamespace(
                    package_name="files",
                    text="Music",
                    resource_id="title",
                )
            ]
        return SimpleNamespace(
            pixels=np.full((16, 12, 3), self.calls, dtype=np.uint8),
            ui_elements=elements,
        )


class SamePackageStaleTransitionEnv:
    foreground_activity_name = (
        "com.google.android.documentsui/com.android.documentsui.files.FilesActivity"
    )

    def __init__(self) -> None:
        self.calls = 0
        self.stale_elements = [
            SimpleNamespace(
                package_name="com.google.android.documentsui",
                text="Downloads",
                resource_id="root",
            )
        ]

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.calls += 1
        elements = (
            self.stale_elements
            if self.calls == 1
            else [
                SimpleNamespace(
                    package_name="com.google.android.documentsui",
                    text="Files on sdk_gphone64_x86_64",
                    resource_id="container_title",
                )
            ]
        )
        return SimpleNamespace(
            pixels=np.full((16, 12, 3), 255, dtype=np.uint8),
            ui_elements=elements,
        )


def test_v2_2_readiness_retries_do_not_consume_policy_steps() -> None:
    env = DelayedAccessibilityEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        protocol_v2=True,
        protocol_v2_2=True,
        readiness_max_observations=4,
        readiness_retry_delay_seconds=0,
    )
    _, observations = controller._observe_state(
        env,
        require_accessibility=True,
    )
    assert env.calls == 3
    assert len(observations) == 3
    assert observations[-1]["source"] == "accessibility"


def test_v2_2_readiness_rejects_stale_previous_app_tree() -> None:
    env = StaleAccessibilityEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        protocol_v2=True,
        protocol_v2_2=True,
        readiness_max_observations=3,
        readiness_retry_delay_seconds=0,
    )
    _, observations = controller._observe_state(
        env,
        require_accessibility=True,
    )
    assert env.calls == 2
    assert not observations[0]["matches_foreground"]
    assert observations[0]["accessibility_packages"] == ["calendar"]
    assert observations[1]["matches_foreground"]
    assert observations[1]["accessibility_packages"] == ["expense"]


def test_v2_2_readiness_rejects_stale_same_package_tree_after_visual_transition(
) -> None:
    env = SamePackageStaleTransitionEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        protocol_v2=True,
        protocol_v2_2=True,
        readiness_max_observations=3,
        readiness_retry_delay_seconds=0,
    )
    prior_semantic = semantic_ui_snapshot(
        env.stale_elements,
        fallback_sha256="0" * 64,
    )
    _, observations = controller._observe_state(
        env,
        require_accessibility=True,
        prior_pixels=np.zeros((16, 12, 3), dtype=np.uint8),
        prior_semantic_sha256=prior_semantic["sha256"],
    )
    assert env.calls == 2
    assert observations[0]["matches_foreground"]
    assert observations[0]["material_pixel_change_from_prior"]
    assert observations[0]["semantic_matches_prior"]
    assert not observations[0]["cross_modal_fresh"]
    assert observations[1]["cross_modal_fresh"]


def test_v2_2_readiness_refreshes_accessibility_once_then_recovers() -> None:
    env = RecoverableAccessibilityEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        protocol_v2=True,
        protocol_v2_2=True,
        readiness_max_observations=6,
        readiness_retry_delay_seconds=0,
        readiness_reconnect_after_observations=3,
    )
    _, observations = controller._observe_state(
        env,
        require_accessibility=True,
    )
    assert env.controller.refresh_calls == 1
    assert env.calls == 4
    assert observations[2]["accessibility_recovery_attempted"]
    assert observations[2]["accessibility_recovery_error"] is None
    assert observations[-1]["source"] == "accessibility"
    assert observations[-1]["matches_foreground"]


def test_controller_routes_visible_failure_and_blocks_repeat(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = SemanticFailureEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.1",
        max_steps=4,
        max_model_calls=4,
        history_policy=RavenMemoryPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
    )
    episode_dir = tmp_path / "episode"
    summary = controller.run(
        env=env,
        task=CalendarTask(),
        episode_id="semantic-failure-v2-1",
        episode_dir=episode_dir,
        seed=1,
        protocol="androidworld_protocol_v2_1_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["termination_reason"] == (
        "model_output_invalid_after_repair"
    )
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    first = summary["steps"][0]
    assert first["screenshot_changed"]
    assert not first["protocol_v2_guard"]["semantic_changed"]
    assert first["protocol_v2_guard"]["new_visible_failures"] == [
        "The event cannot end earlier than it starts"
    ]
    assert first["history_update"]["details"]["visible_failure_texts"] == [
        "The event cannot end earlier than it starts"
    ]
    memory_events = [
        json.loads(line)
        for line in (episode_dir / "memory_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    failure_writes = [
        event
        for event in memory_events
        if event.get("event") == "write"
        and event.get("item", {}).get("memory_type") == "failure"
    ]
    assert len(failure_writes) == 1


def test_controller_repairs_back_inside_destination_picker(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = DestinationPickerEnv()
    controller = EpisodeController(
        client=PickerBackThenDrawerClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="picker-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"]["type"] == "tap"
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "DESTINATION_PICKER_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    assert summary["protocol_v2_guard"][
        "destination_picker_back_block_count"
    ] == 1


def test_controller_repairs_empty_picker_wait_to_navigation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = EmptyDestinationPickerEnv()
    client = EmptyPickerWaitThenDrawerClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="empty-picker-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action == {"type": "tap", "x": 0.07, "y": 0.08}
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "DESTINATION_PICKER_EMPTY_STALL_REQUIRED" in summary[
        "steps"
    ][0]["parse"]["initial_validation_error"]
    assert summary["protocol_v2_guard"][
        "destination_picker_empty_stall_block_count"
    ] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "action.type must be tap" in repair_prompt
    assert "visible current directory" in repair_prompt
    assert "visible top-left navigation drawer" in repair_prompt
    assert "Do not wait, swipe, press_back" in repair_prompt


def test_controller_repairs_empty_picker_unbound_title_tap(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = EmptyDestinationPickerEnv()
    client = EmptyPickerUnboundTapThenDrawerClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="empty-picker-unbound-tap-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "tap",
        "x": 0.07,
        "y": 0.08,
    }
    assert "DESTINATION_PICKER_EMPTY_STALL_REQUIRED" in summary[
        "steps"
    ][0]["parse"]["initial_validation_error"]
    assessment = summary["protocol_v2_guard"]["validation_blocks"][0][
        "destination_picker_empty_stall_assessment"
    ]
    assert assessment["control_bound_tap"] is False
    assert assessment["unsupported_tap"]


def test_controller_repairs_open_roots_drawer_to_visible_row(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = OpenFilesRootsDrawerEnv()
    client = OpenRootsDrawerUnboundThenRowClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="open-roots-drawer-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "tap",
        "x": 0.30,
        "y": 0.76,
    }
    assert "FILES_ROOTS_DRAWER_SELECTION_REQUIRED" in summary[
        "steps"
    ][0]["parse"]["initial_validation_error"]
    assert summary["protocol_v2_guard"][
        "files_roots_drawer_block_count"
    ] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "roots drawer is already open" in repair_prompt
    assert "visible enabled drawer row" in repair_prompt
    assert "No coordinate is supplied" in repair_prompt


def test_controller_rejects_stale_drawer_tree_before_next_decision(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = DrawerToStaleThenFreshRootEnv()
    controller = EpisodeController(
        client=DrawerToFreshRootClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
        readiness_max_observations=4,
        readiness_retry_delay_seconds=0,
        readiness_reconnect_after_observations=3,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="stale-drawer-before-decision-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 2
    assert summary["model_output_error"] is None
    observations = summary["steps"][1][
        "before_readiness_observations"
    ]
    assert len(observations) == 2
    assert observations[0]["material_pixel_change_from_prior"] is True
    assert observations[0]["semantic_matches_prior"] is True
    assert observations[0]["cross_modal_fresh"] is False
    assert observations[1]["semantic_matches_prior"] is False
    assert observations[1]["cross_modal_fresh"] is True
    assert summary["steps"][1]["before_semantic_ui"]["sha256"] != (
        summary["steps"][0]["after_semantic_ui"]["sha256"]
    )
    assert summary["protocol_v2_guard"][
        "files_roots_drawer_block_count"
    ] == 0


def test_controller_rejects_invalid_roots_drawer_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = OpenFilesRootsDrawerEnv()
    client = OpenRootsDrawerUnboundThenRowClient(valid_repair=False)
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="open-roots-drawer-invalid-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="B3",
    )
    assert env.execute_count == 0
    assert summary["termination_reason"] == (
        "model_output_invalid_after_repair"
    )
    error = summary["model_output_error"]
    assert "FILES_ROOTS_DRAWER_SELECTION_REQUIRED" in (
        error["initial_validation_error"]
    )
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]
    assert len(
        summary["steps"][0]["before_readiness_observations"]
    ) == 1


def test_controller_repairs_critic_rejected_picker_commit_to_roots(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = CriticRejectedDestinationPickerEnv()
    client = CriticRejectedCommitThenDrawerClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        history_policy=RejectWrongDestinationCommitPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="critic-picker-renavigation-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "tap",
        "x": 0.065,
        "y": 0.08,
    }
    parse = summary["steps"][0]["parse"]
    assert parse["model_repair_used"]
    assert "DESTINATION_PICKER_RENAVIGATION_REQUIRED" in parse[
        "initial_validation_error"
    ]
    repair_prompt = client.requests[1]["user_prompt"]
    assert "targeting only the visible enabled top-left Show roots" in (
        repair_prompt
    )
    assert "Do not tap Copy/Move or Cancel" in repair_prompt
    assert "do not press_back" in repair_prompt


def test_controller_rejects_non_roots_picker_renavigation_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = CriticRejectedDestinationPickerEnv()
    controller = EpisodeController(
        client=CriticRejectedCommitThenDrawerClient(
            valid_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        history_policy=RejectWrongDestinationCommitPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="critic-picker-invalid-renavigation-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 0
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert "DESTINATION_PICKER_RENAVIGATION_REQUIRED" in error[
        "initial_validation_error"
    ]
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]
    assert "top-left Show roots" in error["repair_validation_error"]


def test_controller_repairs_repeat_transfer_after_destination_commit(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitEnv()
    client = CommitThenRepeatClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert summary["model_call_count"] == 3
    assert summary["steps"][0]["protocol_v2_guard"][
        "destination_picker_commit_executed"
    ]
    assert summary["steps"][1]["decision"]["action"] == {
        "type": "press_back"
    }
    assert summary["steps"][1]["parse"]["model_repair_used"]
    assert "POST_DESTINATION_COMMIT_GUARD" in summary["steps"][1]["parse"][
        "initial_validation_error"
    ]
    assert summary["protocol_v2_guard"][
        "post_destination_commit_block_count"
    ] == 1
    assert "POST_DESTINATION_COMMIT_ACTIVE" in client.requests[1][
        "user_prompt"
    ]
    repair_prompt = client.requests[2]["user_prompt"]
    assert 'exactly {"type":"press_back"}' in repair_prompt
    assert "Do not tap, wait, swipe, type" in repair_prompt


def test_controller_rejects_non_back_post_commit_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitEnv()
    controller = EpisodeController(
        client=CommitThenRepeatClient(
            valid_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-invalid-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert error["initial_validation_error"].startswith(
        "POST_DESTINATION_COMMIT_GUARD:"
    )
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]


def test_controller_repairs_rejected_post_commit_completion_with_back(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitEnv()
    client = CommitThenPrematureDoneClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        history_policy=RejectPrematurePostCommitCompletionPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-completion-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert summary["model_call_count"] == 3
    assert summary["steps"][1]["decision"]["action"] == {
        "type": "press_back"
    }
    assert summary["steps"][1]["parse"]["model_repair_used"]
    assert summary["steps"][1]["parse"]["initial_validation_error"].startswith(
        "Completion critic rejected completion:"
    )
    repair_prompt = client.requests[2]["user_prompt"]
    assert "current source/search view" in repair_prompt
    assert 'exactly {"type":"press_back"}' in repair_prompt
    assert "Do not tap, wait, swipe, type" in repair_prompt


def test_controller_rejects_wait_after_post_commit_completion_rejection(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitEnv()
    controller = EpisodeController(
        client=CommitThenPrematureDoneClient(
            valid_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        history_policy=RejectPrematurePostCommitCompletionPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-completion-invalid-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert error["initial_validation_error"].startswith(
        "Completion critic rejected completion:"
    )
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]
    assert "post-destination repair" in error["repair_validation_error"]


def test_controller_repairs_post_commit_source_browse_to_back(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    client = CommitThenSourceBrowseClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-source-exit-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert summary["model_call_count"] == 3
    source_exit_step = summary["steps"][1]
    assert source_exit_step["decision"]["action"] == {"type": "press_back"}
    assert source_exit_step["parse"]["model_repair_used"]
    assert source_exit_step["parse"]["initial_validation_error"].startswith(
        "POST_DESTINATION_SOURCE_EXIT_GUARD:"
    )
    assessment = source_exit_step["parse"][
        "post_destination_source_context_assessment"
    ]
    assert assessment["current_source_visible"] is True
    assert assessment["matched_labels"] == ["Music"]
    assert summary["protocol_v2_guard"][
        "post_destination_source_exit_block_count"
    ] == 1
    repair_prompt = client.requests[2]["user_prompt"]
    assert 'exactly {"type":"press_back"}' in repair_prompt
    assert "Do not tap, wait, swipe, type" in repair_prompt


def test_controller_normalizes_exact_r54_overlong_back_repair_rationale(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    r54_repair_summary = (
        "The current screen shows the Music folder, but the move operation "
        "may not have been confirmed or the destination may not be verified; "
        "pressing Back to exit this view will allow navigation to the "
        "Ringtones folder to verify the file's presence."
    )
    assert len(r54_repair_summary) == 242
    client = CommitThenSourceBrowseClient(
        repair_summary=r54_repair_summary,
    )
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="r54-overlong-back-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert summary["model_output_error"] is None
    repaired = summary["steps"][1]
    assert repaired["decision"]["action"] == {"type": "press_back"}
    assert len(repaired["decision"]["decision_summary"]) <= 159
    audit = repaired["parse"][
        "bounded_repair_rationale_normalization"
    ]
    assert audit["scope"] == "post_destination_exact_press_back_repair"
    assert audit["limit"] == 159
    assert audit["normalized_fields"] == [
        {
            "field": "decision_summary",
            "before_length": 242,
            "after_length": 159,
        }
    ]
    assert audit["protected_payload_unchanged"] is True
    assert len(audit["protected_payload_sha256_before"]) == 64
    assert (
        audit["protected_payload_sha256_before"]
        == audit["protected_payload_sha256_after"]
    )


def test_controller_does_not_normalize_overlong_non_back_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    overlong = "x" * 242
    controller = EpisodeController(
        client=CommitThenSourceBrowseClient(
            valid_repair=False,
            repair_summary=overlong,
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="overlong-non-back-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert "too long" in error["repair_validation_error"]
    assert "bounded_repair_rationale_normalization" not in error


def test_controller_normalizes_both_exact_back_rationale_fields(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    controller = EpisodeController(
        client=CommitThenSourceBrowseClient(
            repair_summary="s" * 242,
            repair_expected_outcome="o" * 242,
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="both-overlong-back-rationale-fields-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    repaired = summary["steps"][1]
    assert len(repaired["decision"]["decision_summary"]) == 159
    assert len(repaired["decision"]["expected_outcome"]) == 159
    audit = repaired["parse"][
        "bounded_repair_rationale_normalization"
    ]
    assert [item["field"] for item in audit["normalized_fields"]] == [
        "decision_summary",
        "expected_outcome",
    ]


def test_controller_normalization_does_not_rescue_unrelated_schema_error(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    controller = EpisodeController(
        client=CommitThenSourceBrowseClient(
            repair_summary="x" * 242,
            invalid_repair_completion_evidence=True,
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="overlong-back-unrelated-error-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert "completion_evidence" in error["repair_validation_error"]
    audit = error["bounded_repair_rationale_normalization"]
    assert audit["normalized_fields"][0]["before_length"] == 242
    assert audit["protected_payload_unchanged"] is True


def test_controller_rejects_non_back_source_exit_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitSourceExitEnv()
    controller = EpisodeController(
        client=CommitThenSourceBrowseClient(
            valid_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-source-exit-invalid-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert error["initial_validation_error"].startswith(
        "POST_DESTINATION_SOURCE_EXIT_GUARD:"
    )
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]
    assert "post-destination repair" in error["repair_validation_error"]


def test_controller_bypasses_false_positive_critic_only_for_exact_files_destination(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitVerificationEnv()
    client = PostCommitVerificationClient()
    policy = NavigationOverrideProbePolicy()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        history_policy=policy,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-destination-verification-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert summary["model_call_count"] == 2
    assert policy.candidates == [True, False]
    verification_step = summary["steps"][1]
    assessment = verification_step["parse"][
        "post_destination_verification_navigation_assessment"
    ]
    assert assessment["permitted"] is True
    assert assessment["content_exact_label_hit_count"] == 1
    assert assessment["clickable_hit_count"] == 0
    assert assessment["required_destination_text"] == "Ringtones"
    assert assessment["matched_packages"] == [
        "com.google.android.documentsui"
    ]
    assert verification_step["action_authority"]["risk_class"] == (
        "observe_navigation"
    )
    assert "task_parameter_destination" in verification_step[
        "action_authority"
    ]["authority_sources"]
    assert verification_step["protocol_v2_guard"][
        "post_destination_verification_navigation"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["post_destination_verification_navigation_count"] == 1
    assert audit["post_destination_verification_navigation_records"][0][
        "assessment"
    ]["matched_labels"] == ["Ringtones"]


def test_controller_keeps_critic_for_destination_outside_android_files(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostCommitVerificationEnv(destination_package="files")
    policy = NavigationOverrideProbePolicy()
    controller = EpisodeController(
        client=PostCommitVerificationClient(),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        history_policy=policy,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-commit-non-files-destination-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert policy.candidates == [True, None, None]
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert summary["protocol_v2_guard"][
        "post_destination_verification_navigation_count"
    ] == 0
    assert summary["model_output_error"]["initial_validation_error"].startswith(
        "Action critic rejected commit:"
    )


def test_controller_repairs_wrong_exact_target_to_search(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = ExactTargetGridEnv()
    client = WrongFileThenSearchClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="exact-target-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"]["type"] == "tap"
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "EXACT_TARGET_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    assert summary["protocol_v2_guard"][
        "exact_target_long_press_block_count"
    ] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "GUI action was semantically rejected" in repair_prompt
    assert '"nature_sounds_backup.mp3"' in repair_prompt
    assert "choose a materially different action" in repair_prompt
    assert 'action.type must not be "long_press"' in repair_prompt
    assert "only on a later policy step" in repair_prompt
    assert "Correct its format only" not in repair_prompt


def test_controller_repairs_coordinate_type_into_focused_input(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = FocusedInputEnv()
    client = FocusedInputThenSafeTextClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="focused-input-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action["type"] == "type_text"
    assert "x" not in action
    assert "y" not in action
    assert action["clear_text"] is False
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "FOCUSED_INPUT_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    assert summary["protocol_v2_guard"]["focused_input_block_count"] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "Keep action.type=type_text" in repair_prompt
    assert "Remove x and y" in repair_prompt
    assert "set clear_text=false" in repair_prompt
    assert "Do not tap, navigate, change the text" in repair_prompt


def test_controller_repairs_coordinate_type_with_keyboard_only(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = SoftKeyboardOnlyInputEnv()
    client = FocusedInputThenSafeTextClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="keyboard-input-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action["type"] == "type_text"
    assert "x" not in action
    assert "y" not in action
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "FOCUSED_INPUT_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    block = summary["protocol_v2_guard"]["validation_blocks"][0]
    assessment = block["focused_input_assessment"]
    assert assessment["present"] is False
    assert assessment["soft_keyboard_present"] is True
    assert assessment["input_ready"] is True


def test_controller_repairs_coordinate_for_unique_active_input(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = UniqueFocusedSearchEnv()
    client = UniqueSearchCoordinateThenSafeTextClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="unique-active-input-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    action = summary["steps"][0]["decision"]["action"]
    assert action["type"] == "type_text"
    assert "x" not in action
    assert "y" not in action
    assert action["clear_text"] is False
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "FOCUSED_INPUT_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    block = summary["protocol_v2_guard"]["validation_blocks"][0]
    assert block["reason"] == (
        "focused_input_redundant_unique_coordinate_blocked"
    )
    target = block["coordinate_text_target_assessment"]
    assert target["visible_editable_count"] == 1
    assert target["matched_empty"] is True
    repair_prompt = client.requests[1]["user_prompt"]
    assert "Remove x and y" in repair_prompt
    assert "target input is empty" in repair_prompt
    assert "set clear_text=false" in repair_prompt


def test_controller_repairs_unbound_coordinate_type_to_input_activation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = UnboundTextTargetEnv()
    client = UnboundTextThenActivateInputClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="unbound-text-target-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action == {"type": "tap", "x": 0.82, "y": 0.075}
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "TEXT_TARGET_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["coordinate_text_target_block_count"] == 1
    block = audit["validation_blocks"][0]
    assessment = block["coordinate_text_target_assessment"]
    assert assessment["visible_editable_count"] == 0
    assert assessment["matched"] is False
    repair_prompt = client.requests[1]["user_prompt"]
    assert "action.type must not be type_text" in repair_prompt
    assert "activate or reopen a visible input control" in repair_prompt


def test_controller_repairs_unfocused_clear_text_to_input_activation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = UnfocusedEditableSearchEnv()
    client = UnboundTextThenActivateInputClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="unfocused-clear-text-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action == {"type": "tap", "x": 0.82, "y": 0.075}
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "UNFOCUSED_CLEAR_TEXT_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["unfocused_clear_text_block_count"] == 1
    block = audit["validation_blocks"][0]
    assessment = block["coordinate_text_target_assessment"]
    assert assessment["visible_editable_count"] == 1
    assert assessment["matched"] is True
    repair_prompt = client.requests[1]["user_prompt"]
    assert "action.type must not be type_text" in repair_prompt
    assert "Tap that same visibly supported input control" in repair_prompt
    assert "Do not send Ctrl+A to an unfocused screen" in repair_prompt


def test_controller_routes_malformed_text_coordinate_to_safe_activation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostActivationKeyboardOnlyEnv()
    client = MalformedCoordinateThenActivateInputClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="malformed-coordinate-activation-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert summary["model_call_count"] == 3
    assert env.execute_count == 2
    assert env.value == "nature_sounds.mp3"
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.075,
    }
    assert summary["steps"][0]["parse"]["model_repair_used"] is True
    assert summary["steps"][0]["parse"]["repair_contract_error"].startswith(
        "MALFORMED_COORDINATE_INPUT_GUARD:"
    )
    assert summary["steps"][0]["input_activation_repair_marked"] is True
    assert summary["steps"][1]["decision"]["action"] == {
        "type": "type_text",
        "text": "nature_sounds.mp3",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "clear_text": False,
    }
    audit = summary["protocol_v2_guard"]
    assert audit["input_activation_proof_count"] == 1
    assert audit["input_activation_proof_consumed_count"] == 1
    assert audit["input_activation_repair_pending"] is False
    repair_prompt = client.requests[1]["user_prompt"]
    assert "MALFORMED_COORDINATE_INPUT_GUARD" in repair_prompt
    assert "action.type=tap" in repair_prompt
    assert "Do not type, clear text" in repair_prompt


def test_controller_rejects_direct_text_malformed_coordinate_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostActivationKeyboardOnlyEnv()
    controller = EpisodeController(
        client=MalformedCoordinateThenActivateInputClient(
            safe_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="malformed-coordinate-direct-text-rejected-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 0
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert summary["model_output_error"][
        "initial_validation_error"
    ].startswith("action:")
    assert "REPAIR_CONTRACT_GUARD" in summary["model_output_error"][
        "repair_validation_error"
    ]
    assert "permits only one normalized tap" in summary[
        "model_output_error"
    ]["repair_validation_error"]


def test_controller_repairs_post_activation_clear_text_without_focused_editable(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostActivationKeyboardOnlyEnv()
    client = PostActivationClearTextClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=4,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-activation-clear-text-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 2
    assert env.value == "nature_sounds.mp3"
    assert summary["model_call_count"] == 4
    repaired = summary["steps"][1]
    assert repaired["decision"]["action"] == {
        "type": "type_text",
        "text": "nature_sounds.mp3",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "clear_text": False,
    }
    assert repaired["parse"]["model_repair_used"] is True
    assert repaired["parse"]["initial_validation_error"].startswith(
        "POST_ACTIVATION_CLEAR_TEXT_GUARD:"
    )
    audit = summary["protocol_v2_guard"]
    assert audit["post_activation_clear_text_block_count"] == 1
    assert audit["input_activation_proof_count"] == 1
    assert audit["input_activation_proof_consumed_count"] == 1
    assert audit["input_activation_repair_pending"] is False
    repair_prompt = client.requests[3]["user_prompt"]
    assert "exact same text" in repair_prompt
    assert "clear_text=false" in repair_prompt
    assert "send Ctrl+A" in repair_prompt


def test_controller_rejects_unsafe_post_activation_clear_text_repair(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = PostActivationKeyboardOnlyEnv()
    controller = EpisodeController(
        client=PostActivationClearTextClient(
            valid_repair=False
        ),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=4,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="post-activation-clear-text-invalid-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    error = summary["model_output_error"]
    assert error["initial_validation_error"].startswith(
        "POST_ACTIVATION_CLEAR_TEXT_GUARD:"
    )
    assert "REPAIR_CONTRACT_GUARD" in error["repair_validation_error"]
    assert "clear_text=false" in error["repair_validation_error"]


def test_controller_allows_one_bounded_repeat_to_activate_input(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = RepeatedActivationInputEnv()
    client = RepeatedActivationRecoveryClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=3,
        max_model_calls=4,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="bounded-input-repeat-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert summary["termination_reason"] == "max_steps"
    assert summary["model_output_error"] is None
    assert summary["model_call_count"] == 4
    assert env.execute_count == 3
    assert env.tap_count == 2
    assert env.input_count == 1
    assert summary["steps"][1]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.5,
    }
    assert summary["steps"][1]["parse"]["model_repair_used"] is True
    assert "UNFOCUSED_CLEAR_TEXT_GUARD" in summary["steps"][1]["parse"][
        "initial_validation_error"
    ]
    assert summary["steps"][1]["input_activation_repair_marked"] is True
    assert summary["steps"][2]["decision"]["action"]["type"] == "type_text"
    assert "x" not in summary["steps"][2]["decision"]["action"]
    assert "y" not in summary["steps"][2]["decision"]["action"]
    audit = summary["protocol_v2_guard"]
    assert audit["input_activation_repeat_override_count"] == 1
    assert audit["unverified_progress_repeat_block_count"] == 0
    assert audit["input_activation_proof_count"] == 1
    assert audit["input_activation_proof_consumed_count"] == 1
    assert audit["input_activation_repair_pending"] is False


def test_controller_allows_one_named_visible_control_activation_retry(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = VisibleControlActivationRetryEnv()
    client = VisibleControlActivationRetryClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=2,
        max_model_calls=3,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=FilesTask(),
        episode_id="bounded-visible-control-repeat-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert summary["termination_reason"] == "max_steps"
    assert summary["model_output_error"] is None
    assert summary["model_call_count"] == 3
    assert env.execute_count == 2
    assert env.tap_count == 2
    assert env.form_open is True
    assert summary["steps"][1]["parse"]["model_repair_used"] is True
    assert "UNVERIFIED_PROGRESS_REPEAT_REQUIRED" in summary["steps"][1][
        "parse"
    ]["initial_validation_error"]
    audit = summary["protocol_v2_guard"]
    assert (
        audit["visible_control_activation_repeat_override_count"] == 1
    )
    assert audit["unverified_progress_repeat_block_count"] == 1
    record = audit[
        "visible_control_activation_repeat_override_records"
    ][0]
    assessment = record[
        "visible_control_activation_retry_assessment"
    ]
    assert assessment["matched_labels"] == ["Create contact"]
    assert assessment["commit_like"] is False
    repair_prompt = client.requests[2]["user_prompt"]
    assert "VISIBLE_CONTROL_ACTIVATION_RETRY" in repair_prompt
    assert "single bounded activation retry" in repair_prompt
    assert "never authorizes a third identical tap" in repair_prompt


def test_controller_repairs_fabricated_task_literal_to_requested_value(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = ContactFieldsNoKeyboardEnv()
    client = FabricatedTaskLiteralThenPhoneClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=ContactTask(),
        episode_id="declared-source-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 0
    assert env.focus_click_count == 1
    assert len(env.atomic_clear_and_type_commands) == 0
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action["type"] == "tap"
    assert action["x"] == 0.45
    assert action["y"] == 0.60
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "DECLARED_TEXT_SOURCE_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["declared_text_source_block_count"] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "Do not merely change text_origin" in repair_prompt
    assert "do not invent an optional field value" in repair_prompt
    assert "visible empty editable field" in repair_prompt
    assert "action.type must not be type_text or answer" in repair_prompt
    assert "tap that role-matched field only to activate it" in repair_prompt
    assert "later policy step before typing" in repair_prompt
    assert "leaves the unspecified field untouched" in repair_prompt


def test_controller_enforces_keyboard_dismissal_repair_contract(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = ContactFieldsEnv()
    client = FabricatedTaskLiteralThenPhoneClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=ContactTask(),
        episode_id="keyboard-source-contract-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 0
    assert summary["termination_reason"] == (
        "model_output_invalid_after_repair"
    )
    assert "SOFT_KEYBOARD_DISMISS_REQUIRED" in summary[
        "model_output_error"
    ]["initial_validation_error"]
    assert "REPAIR_CONTRACT_GUARD" in summary[
        "model_output_error"
    ]["repair_validation_error"]


def test_controller_repairs_phone_from_company_to_phone_field(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = ContactFieldsEnv()
    client = PhoneInCompanyThenPhoneClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=ContactTask(),
        episode_id="field-value-binding-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert env.focus_click_count == 1
    assert len(env.atomic_clear_and_type_commands) == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action["text"] == "+17634322348"
    assert action["x"] == 0.45
    assert action["y"] == 0.60
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "FIELD_VALUE_BINDING_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["task_literal_field_role_block_count"] == 1
    repair_prompt = client.requests[1]["user_prompt"]
    assert "Keep action.type=type_text" in repair_prompt
    assert "exact same text, text_origin" in repair_prompt
    assert "Do not fill an unrelated optional field" in repair_prompt


def test_controller_dismisses_keyboard_after_fabricated_source_value(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = KeyboardSwipeEnv()
    client = FabricatedTaskLiteralThenBackClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=ContactTask(),
        episode_id="fabricated-source-keyboard-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "press_back"
    }
    error = summary["steps"][0]["parse"]["initial_validation_error"]
    assert "DECLARED_TEXT_SOURCE_GUARD" in error
    assert "SOFT_KEYBOARD_DISMISS_REQUIRED" in error
    audit = summary["protocol_v2_guard"]
    assert audit["declared_text_source_block_count"] == 1
    assert audit["soft_keyboard_swipe_block_count"] == 0
    block = audit["validation_blocks"][0]
    assert block["soft_keyboard_present"] is True
    repair_prompt = client.requests[1]["user_prompt"]
    assert 'action exactly {"type":"press_back"}' in repair_prompt
    assert "Do not swipe, type, tap, save" in repair_prompt


def test_controller_repairs_keyboard_swipe_to_keyboard_dismissal(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = KeyboardSwipeEnv()
    client = KeyboardSwipeThenBackClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_steps=1,
        max_model_calls=2,
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )
    summary = controller.run(
        env=env,
        task=ContactTask(),
        episode_id="keyboard-swipe-repair-v2-2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    assert summary["steps"][0]["decision"]["action"] == {
        "type": "press_back"
    }
    assert summary["steps"][0]["parse"]["model_repair_used"]
    assert "SOFT_KEYBOARD_SWIPE_GUARD" in summary["steps"][0]["parse"][
        "initial_validation_error"
    ]
    audit = summary["protocol_v2_guard"]
    assert audit["soft_keyboard_swipe_block_count"] == 1
    block = audit["validation_blocks"][0]
    assert block["reason"] == "soft_keyboard_swipe_start_blocked"
    assessment = block["soft_keyboard_swipe_assessment"]
    assert assessment["start_in_keyboard"] is True
    assert "bbox" not in assessment
    repair_prompt = client.requests[1]["user_prompt"]
    assert 'action exactly {"type":"press_back"}' in repair_prompt
    assert "Do not swipe, type, tap, save" in repair_prompt
