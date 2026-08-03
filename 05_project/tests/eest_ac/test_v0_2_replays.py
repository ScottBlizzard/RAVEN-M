from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pytest

from raven_m.eest_ac.binding_metrics_v0_2 import label_three_layers
from raven_m.eest_ac.controller_v0_2 import EestAcV02Controller
from raven_m.eest_ac.observation_v0_2 import ObservationStabilizer
from raven_m.eest_ac.recovery_v0_2 import RecoveryRegistryV02
from raven_m.eest_ac.schema import EestDecisionValidationError, parse_eest_decision
from raven_m.eest_ac.models import EvidenceScope, EvidenceSource
from raven_m.eest_ac.state import EvidenceLedger
from raven_m.eest_ac.task_roles import TaskRoleParseError, TaskRoleParser, verify_exact_spans
from raven_m.env.androidworld_adapter import MappedAction
from raven_m.models.transformers_client import ModelCall


SMS_REPLAY_GOAL = (
    "Text the address of the event to Morgan Hale that Avery Stone just sent me "
    "in Simple SMS Messenger"
)


@dataclass
class FakeState:
    pixels: np.ndarray
    ui_elements: list[dict]


def screen(*texts: str, value: int = 0, package: str = "org.example.app") -> FakeState:
    return FakeState(
        pixels=np.full((48, 32, 3), value, dtype=np.uint8),
        ui_elements=[
            {
                "text": text,
                "package_name": package,
                "class_name": "android.widget.TextView",
                "is_visible": True,
                "is_enabled": True,
            }
            for text in texts
        ],
    )


class SequenceEnv:
    def __init__(self, before: FakeState, after: FakeState | None = None) -> None:
        self.before = before
        self.after = after or before
        self.phase = 0
        self.interaction_cache = None

    def reset(self, go_home=True):
        if go_home:
            self.phase = 0

    def hide_automation_ui(self):
        return None

    def get_state(self, wait_to_stabilize=True):
        return self.after if self.phase else self.before


class DelayedEnv:
    def __init__(self, states: list[FakeState]) -> None:
        self.states = states
        self.index = 0

    def get_state(self, wait_to_stabilize=True):
        value = self.states[min(self.index, len(self.states) - 1)]
        self.index += 1
        return value


class FakeAdapter:
    def map_action(self, canonical, *, screen_width, screen_height):
        return MappedAction(
            canonical=dict(canonical),
            screen_size=(screen_width, screen_height),
            actual_pixels={},
            upstream_action=None,
        )

    def execute(self, env, mapped):
        if mapped.canonical["type"] in {"open_app", "press_back", "answer"}:
            env.phase = 1
        if mapped.canonical["type"] == "answer":
            env.interaction_cache = mapped.canonical["text"]


class FakeTask:
    name = "DevelopmentReplayOnly"

    def __init__(self, goal: str) -> None:
        self.goal = goal
        self.params = {"development_replay": True}
        self.evaluator_calls = 0

    def initialize_task(self, env):
        return None

    def is_successful(self, env):
        self.evaluator_calls += 1
        return 1.0 if env.phase else 0.0

    def tear_down(self, env):
        return None


class FakeClient:
    def __init__(self, responder, *, completion_tokens: int = 60) -> None:
        self.responder = responder
        self.completion_tokens = completion_tokens
        self.counter = 0

    def generate(
        self,
        *,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        episode_id: str,
        call_label: str,
        max_tokens: int,
        context_images=None,
    ) -> ModelCall:
        self.counter += 1
        content = self.responder(call_label, user_prompt)
        image_hash = sha256(image_path.read_bytes()).hexdigest()
        return ModelCall(
            call_id=f"call-{self.counter}",
            episode_id=episode_id,
            idempotency_key=f"key-{self.counter}",
            image_sha256=image_hash,
            image_sha256s=(image_hash,),
            prompt_sha256=sha256(user_prompt.encode()).hexdigest(),
            request_sha256=f"{self.counter:064x}",
            response_sha256=sha256(content.encode()).hexdigest(),
            content=content,
            usage={
                "prompt_tokens": 350,
                "completion_tokens": self.completion_tokens,
                "total_tokens": 350 + self.completion_tokens,
            },
            raven_meta={},
        )


def decision(action, intent="navigate", *, status="continue", evidence=None, citations=None):
    return json.dumps(
        {
            "status": status,
            "action": action,
            "intent": intent,
            "evidence": evidence or [],
            "citations": citations or [],
        }
    )


def controller(client, arm, frame=None):
    return EestAcV02Controller(
        client=client,
        executor_prompt="v0.2 executor",
        summary_prompt="summary",
        arm=arm,
        max_environment_actions=5,
        max_model_calls=10,
        task_role_frame=frame,
        adapter=FakeAdapter(),
        stabilizer=ObservationStabilizer(delay_seconds=0, sleep_fn=lambda _: None),
    )


def test_shared_exact_span_parser_separates_source_field_destination() -> None:
    frame = TaskRoleParser().parse(SMS_REPLAY_GOAL, require_transfer=True)
    assert verify_exact_spans(SMS_REPLAY_GOAL, frame)
    assert frame.source.text == "Avery Stone"
    assert frame.requested_field.text == "the address of the event"
    assert frame.destination.text == "Morgan Hale"
    with pytest.raises(TaskRoleParseError):
        TaskRoleParser().parse("Do whatever seems useful.", require_transfer=True)


def test_generic_create_with_from_grammar_uses_only_exact_spans() -> None:
    goal = (
        "Create a file in a writing app, called output.md with the transactions "
        "from the receipt.png. Use an image viewer to view the receipt."
    )
    frame = TaskRoleParser().parse(goal, require_transfer=True)
    assert verify_exact_spans(goal, frame)
    assert frame.destination.text == "a file in a writing app, called output.md"
    assert frame.requested_field.text == "the transactions"
    assert frame.source.text == "the receipt.png"
    assert frame.parse_rule == "create_destination_with_field_from_source"


def test_delayed_transition_never_becomes_recovery() -> None:
    unchanged = screen("Conversation list")
    changed = screen("Avery Stone", "123 Main St", value=10)
    before = ObservationStabilizer.capture(unchanged)
    transition = ObservationStabilizer(
        delay_seconds=0,
        sleep_fn=lambda _: None,
    ).observe_after(env=DelayedEnv([unchanged, changed, changed]), before=before)
    assert not transition.no_effect_confirmed
    assert transition.outcome == "changed_or_uncertain"
    registry = RecoveryRegistryV02()
    with pytest.raises(ValueError, match="stable no-effect"):
        registry.register(
            state_signature=before.fingerprint.state_signature,
            canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
            failed_event_id="event:1",
            observed_step=1,
            stability_audit=transition.audit_record(),
        )


def test_missing_a11y_is_uncertain_even_when_pixels_match() -> None:
    empty = FakeState(np.zeros((16, 16, 3), dtype=np.uint8), [])
    before = ObservationStabilizer.capture(empty)
    result = ObservationStabilizer(delay_seconds=0, sleep_fn=lambda _: None).observe_after(
        env=DelayedEnv([empty, empty]), before=before
    )
    assert not result.no_effect_confirmed


def test_recovery_blocks_exact_and_same_class_but_allows_different_class() -> None:
    stable = screen("No change")
    before = ObservationStabilizer.capture(stable)
    transition = ObservationStabilizer(delay_seconds=0, sleep_fn=lambda _: None).observe_after(
        env=DelayedEnv([stable, stable]), before=before
    )
    registry = RecoveryRegistryV02()
    action = {"type": "tap", "x": 0.5, "y": 0.5}
    record = registry.register(
        state_signature=before.fingerprint.state_signature,
        canonical_action=action,
        failed_event_id="event:1",
        observed_step=1,
        stability_audit=transition.audit_record(),
    )
    assert record.canonical_action == action
    assert registry.block_reason(state_signature=before.fingerprint.state_signature, canonical_action=action) == "exact_action_repeat_in_stable_state"
    assert registry.block_reason(
        state_signature=before.fingerprint.state_signature,
        canonical_action={"type": "tap", "x": 0.2, "y": 0.2},
    ) == "same_action_class_forbidden_in_stable_state"
    assert registry.block_reason(
        state_signature=before.fingerprint.state_signature,
        canonical_action={"type": "press_back"},
    ) is None


def test_wrong_destination_replay_is_not_counted_as_capture_success() -> None:
    frame = TaskRoleParser().parse(SMS_REPLAY_GOAL, require_transfer=True)
    summary = {
        "task_role_frame": frame.record(),
        "evidence_ledger": [
            {"entity": "Avery Stone", "field": "the address of the event", "value": "123 Main St"}
        ],
        "ordinary_summary": None,
        "steps": [
            {
                "executed": True,
                "before_visible_texts": ["Avery Stone", "Conversation"],
                "decision": {
                    "intent": "type the address",
                    "action": {"type": "type_text", "text": "123 Main St"},
                    "evidence": [],
                },
            }
        ],
    }
    label = label_three_layers(summary, expected_value="123 Main St")
    assert label.capture == "correct"
    assert label.destination_retention == "source_as_destination"
    assert label.destination_action == "wrong_destination"


def test_compact_schema_replaces_recorded_truncation_shape() -> None:
    truncated_v01 = '{"status":"continue","action":{"type":"tap","x":0.5'
    with pytest.raises(EestDecisionValidationError):
        parse_eest_decision(truncated_v01, schema_path=Path("schemas/eest_ac_decision.v0_2.schema.json"))
    compact = {
        "status": "continue",
        "action": {"type": "type_text", "text": "x" * 360, "clear_text": True},
        "intent": "i" * 64,
        "evidence": [
            {"entity": "e" * 64, "field": "f" * 48, "value": "v" * 160, "scope": "cross_page"}
        ],
        "citations": ["task:root"],
    }
    encoded = json.dumps(compact, separators=(",", ":"))
    assert len(encoded.encode("utf-8")) < 900
    assert parse_eest_decision(encoded, schema_path=Path("schemas/eest_ac_decision.v0_2.schema.json")).decision == compact


def test_controller_counts_invalid_calls_and_still_evaluates(tmp_path) -> None:
    task = FakeTask("Open the camera app.")
    client = FakeClient(lambda *_: '{"status":', completion_tokens=256)
    result = controller(client, "B3", TaskRoleParser().parse(task.goal)).run(
        env=SequenceEnv(screen("Home")),
        task=task,
        episode_id="output-truncation-replay",
        episode_dir=tmp_path / "invalid",
        seed=1,
        study_id="development_replay",
    )
    assert result["failure_class"] == "model_or_controller_invalid"
    assert result["model_calls"] == result["model_call_record_count"] == 2
    assert result["model_call_accounting_valid"]
    assert result["schema_truncation_count"] == 1
    assert result["evaluator_status"] == "ran_after_controller_error"
    assert task.evaluator_calls == 1


def test_generic_open_completion_stops_after_one_action_and_call(tmp_path) -> None:
    task = FakeTask("Open the camera app.")
    env = SequenceEnv(
        screen("Home", package="com.android.launcher"),
        screen("Camera", value=10, package="org.example.camera"),
    )
    client = FakeClient(
        lambda *_: decision(
            {"type": "open_app", "app_name": "camera"},
            "open requested app",
            citations=["task:root"],
        )
    )
    result = controller(client, "M_SLOTS", TaskRoleParser().parse(task.goal)).run(
        env=env,
        task=task,
        episode_id="early-completion-replay",
        episode_dir=tmp_path / "completion",
        seed=1,
        study_id="development_replay",
    )
    assert result["task_success"]
    assert result["termination_reason"] == "deterministic_requirement_satisfied"
    assert result["environment_actions"] == 1
    assert result["model_calls"] == 1
    assert result["completion_tp"]


def test_controller_blocks_repeated_action_and_requires_new_class(tmp_path) -> None:
    task = FakeTask(SMS_REPLAY_GOAL)
    replies = {
        "executor_d000_initial": decision({"type": "tap", "x": 0.5, "y": 0.5}),
        "executor_d001_initial": decision({"type": "tap", "x": 0.5, "y": 0.5}),
        "executor_d002_initial": decision({"type": "press_back"}, "use different action class"),
        "executor_d003_initial": decision(None, "complete", status="done"),
    }
    result = controller(
        FakeClient(lambda label, _: replies[label]),
        "M_SLOTS",
        TaskRoleParser().parse(task.goal, require_transfer=True),
    ).run(
        env=SequenceEnv(screen("Avery Stone", "No change"), screen("Morgan Hale", value=20)),
        task=task,
        episode_id="repeated-action-replay",
        episode_dir=tmp_path / "repeat",
        seed=1,
        study_id="development_replay",
    )
    assert result["repeated_action_blocks"] == 1
    assert result["different_class_after_recovery"] == 1
    assert result["environment_actions"] == 2
    assert result["recovery_registry"][0]["canonical_action"]["type"] == "tap"


def test_evidence_deduplicates_logical_fact_deterministically() -> None:
    ledger = EvidenceLedger()
    kwargs = {
        "entity": "Avery Stone",
        "field": "the address of the event",
        "value": "123 Main St",
        "source": EvidenceSource.CURRENT_SCREEN,
        "scope": EvidenceScope.CROSS_PAGE,
        "expected_source_sha256": "a" * 64,
        "visible_texts": ("Avery Stone", "123 Main St"),
    }
    first = ledger.add(
        **kwargs,
        acquisition_step=1,
        source_sha256="a" * 64,
        relevance_tags=("Morgan Hale", "send", "send"),
    )
    second = ledger.add(
        **kwargs,
        acquisition_step=2,
        source_sha256="a" * 64,
        relevance_tags=("send", "Morgan Hale"),
    )
    assert first is second
    assert len(ledger.records) == 1
    assert first.relevance_tags == ("morgan hale", "send")


@pytest.mark.parametrize("arm,expected_plan", [("B3", 0), ("B3_MATCH", 1), ("M_SLOTS", 0)])
def test_matched_auxiliary_reports_eligible_planned_realized(
    tmp_path, arm: str, expected_plan: int
) -> None:
    task = FakeTask("Provide the requested answer.")

    def respond(label: str, _: str) -> str:
        if label == "executor_d000_initial":
            return decision({"type": "answer", "text": "result"}, "answer")
        if label == "matched_summary_d000":
            return json.dumps({"summary": "Return the requested result."})
        raise AssertionError(label)

    result = controller(FakeClient(respond), arm).run(
        env=SequenceEnv(screen("Result", "result"), screen("Result", value=2)),
        task=task,
        episode_id=f"accounting-{arm}",
        episode_dir=tmp_path / arm,
        seed=1,
        study_id="development_replay",
    )
    assert result["eligible_opportunities"] == 1
    assert result["planned_auxiliary_calls"] == expected_plan
    assert result["realized_auxiliary_calls"] == expected_plan
    assert result["model_call_accounting_valid"]
