from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.history.policies import RavenMemoryPolicy
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


class FilesTask:
    name = "FilesMoveFile"
    goal = "Move the requested file to the requested folder."
    params = {"file_name": "nature_sounds.mp3"}

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
