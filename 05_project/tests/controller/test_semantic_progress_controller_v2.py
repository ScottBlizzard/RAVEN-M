from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
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
    def generate(self, **kwargs) -> ModelCall:
        label = kwargs["call_label"]
        if label.startswith("step_000"):
            action = {"type": "tap", "x": 0.40, "y": 0.94}
            summary = "Commit the pending move."
        elif label.endswith("_repair"):
            action = {"type": "tap", "x": 0.07, "y": 0.08}
            summary = "Open navigation to verify the destination."
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


class FabricatedTaskLiteralThenPhoneClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.endswith("_repair"):
            text = "+17634322348"
            x, y = 0.45, 0.60
            summary = "Enter the requested phone number in Phone."
        else:
            text = "Tech Solutions"
            x, y = 0.45, 0.55
            summary = "Invent a company value not present in the task."
        decision = {
            "status": "continue",
            "action": {
                "type": "type_text",
                "text": text,
                "text_origin": "task_literal",
                "source_memory_ids": [],
                "x": x,
                "y": y,
                "clear_text": True,
            },
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
        state.ui_elements.append(
            SimpleNamespace(
                package_name="files",
                text="No items",
                is_visible=True,
                is_enabled=True,
            )
        )
        return state


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


class ContactFieldsEnv(DestinationPickerEnv):
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
        assert action.action_type == "input_text"
        assert action.text == "+17634322348"
        assert action.clear_text is True
        self.execute_count += 1


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
    params = {"file_name": "nature_sounds.mp3"}

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
    controller = EpisodeController(
        client=CommitThenRepeatClient(),  # type: ignore[arg-type]
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
    assert summary["steps"][1]["decision"]["action"]["type"] == "tap"
    assert summary["steps"][1]["parse"]["model_repair_used"]
    assert "POST_DESTINATION_COMMIT_GUARD" in summary["steps"][1]["parse"][
        "initial_validation_error"
    ]
    assert summary["protocol_v2_guard"][
        "post_destination_commit_block_count"
    ] == 1


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
    assert env.execute_count == 1
    assert summary["model_call_count"] == 2
    action = summary["steps"][0]["decision"]["action"]
    assert action["text"] == "+17634322348"
    assert action["text_origin"] == "task_literal"
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
    assert "fill that requested value in its matching field now" in repair_prompt
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
