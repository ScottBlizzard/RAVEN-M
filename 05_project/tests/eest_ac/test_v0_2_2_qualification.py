from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
import numpy as np

from raven_m.eest_ac.qualification_v0_2_2 import (
    DecisionEnvelopeQualificationDeciderV022,
    EnvelopeQualificationFailure,
)
from raven_m.eest_ac.observation_policy_v0_2_2 import (
    QualificationObservationStabilizerV022,
    audit_stable_change_v0_2_2,
)
from raven_m.eest_ac.observation_v0_2 import (
    CapturedObservation,
    ObservationFingerprint,
    StabilizedTransition,
)
from raven_m.models.transformers_client import ModelCall


def response(action: dict, *, intent: object = "qualification") -> str:
    return json.dumps({
        "status": "continue",
        "action": action,
        "intent": intent,
        "evidence": [],
        "citations": [],
    }, ensure_ascii=False, separators=(",", ":"))


class FakeClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.index = 0

    def generate(self, **kwargs) -> ModelCall:
        content = self.outputs[self.index]
        self.index += 1
        call_id = f"c{self.index}"
        return ModelCall(
            call_id=call_id,
            episode_id=kwargs["episode_id"],
            idempotency_key=f"i{self.index}",
            image_sha256="a" * 64,
            image_sha256s=("a" * 64,),
            prompt_sha256="b" * 64,
            request_sha256="c" * 64,
            response_sha256=sha256(content.encode()).hexdigest(),
            content=content,
            usage={"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140},
            raven_meta={},
        )


def run(outputs: list[str]):
    calls: list[dict] = []
    attempts: list[dict] = []
    written: list[dict] = []
    result = DecisionEnvelopeQualificationDeciderV022(
        client=FakeClient(outputs),  # type: ignore[arg-type]
        system_prompt="contract",
    ).decide(
        image_path=Path("screen.png"),
        user_prompt="probe\nAVAILABLE_CITATIONS:task:root",
        episode_id="episode",
        calls=calls,
        attempts=attempts,
        record_call=written.append,
        allowed_citations={"task:root"},
    )
    return result, calls, attempts, written


def test_initial_direct_uses_one_call() -> None:
    result, calls, attempts, written = run([response({"type": "press_back"})])
    assert result.accepted_stage == "initial_direct"
    assert result.initial_direct_command_pass
    assert not result.repair_used
    assert len(calls) == len(attempts) == len(written) == 1


def test_long_or_whitespace_intent_is_metadata_only_and_uses_no_repair() -> None:
    result, calls, attempts, _ = run([
        response({"type": "press_back"}, intent="  describe\t" + "界" * 600 + "  ")
    ])
    assert result.accepted_stage == "initial_direct"
    assert result.parsed.intent_metadata.metadata_normalized
    assert result.parsed.intent_metadata.display_truncated
    assert len(calls) == len(attempts) == 1


def test_initial_action_alias_normalizes_without_repair() -> None:
    result, calls, attempts, _ = run([
        response({"type": "swipe", "x": 0.5, "y": 0.8, "direction": "up", "distance": 0.6})
    ])
    assert result.accepted_stage == "initial_action_normalized"
    assert result.parsed.decision["action"]["y2"] == pytest.approx(0.2)
    assert len(calls) == len(attempts) == 1


def test_control_error_may_use_one_repair() -> None:
    result, calls, attempts, _ = run([
        response({"type": "press", "key": "recent_app"}),
        response({"type": "press_back"}),
    ])
    assert result.accepted_stage == "control_repair"
    assert result.repair_used
    assert result.repair_reason_plane == "control_plane"
    assert len(calls) == len(attempts) == 2


def test_schema_critical_intent_may_use_one_repair() -> None:
    result, calls, attempts, _ = run([
        response({"type": "press_back"}, intent=" \t\n"),
        response({"type": "press_back"}, intent="return"),
    ])
    assert result.accepted_stage == "control_repair"
    assert result.repair_reason_plane == "observability_schema_critical"
    assert len(calls) == len(attempts) == 2


def test_identical_invalid_control_terminates_with_two_counted_calls() -> None:
    invalid = response({"type": "press", "key": "recent_app"})
    calls: list[dict] = []
    attempts: list[dict] = []
    written: list[dict] = []
    with pytest.raises(EnvelopeQualificationFailure) as caught:
        DecisionEnvelopeQualificationDeciderV022(
            client=FakeClient([invalid, invalid]),  # type: ignore[arg-type]
            system_prompt="contract",
        ).decide(
            image_path=Path("screen.png"),
            user_prompt="probe",
            episode_id="episode",
            calls=calls,
            attempts=attempts,
            record_call=written.append,
        )
    assert caught.value.code == "REPAIR_IDENTICAL_INVALID_CONTROL"
    assert len(calls) == len(attempts) == len(written) == 2


def _captured(
    *,
    pixel: str,
    a11y: str | None,
    signature: str,
    packages: tuple[str, ...] = ("example.package",),
) -> CapturedObservation:
    return CapturedObservation(
        state=object(),
        fingerprint=ObservationFingerprint(
            pixel_sha256=pixel,
            a11y_sha256=a11y,
            a11y_available=a11y is not None,
            state_signature=signature,
            visible_texts=(),
            package_names=packages,
            element_count=1 if a11y is not None else 0,
        ),
    )


def _transition(*posts: CapturedObservation) -> StabilizedTransition:
    return StabilizedTransition(
        post_observations=posts,
        final_observation=posts[-1],
        outcome="changed_or_uncertain",
        no_effect_confirmed=False,
        post_observations_agree=False,
    )


def test_terminal_window_accepts_stable_changed_positive() -> None:
    before = _captured(pixel="pre-p", a11y="pre-a", signature="pre-s")
    transition_frame = _captured(pixel="motion", a11y="motion-a", signature="motion-s")
    settled_one = _captured(pixel="post-p", a11y="post-a", signature="post-s")
    settled_two = _captured(pixel="post-p", a11y="post-a", signature="post-s")
    audit = audit_stable_change_v0_2_2(
        before=before,
        transition=_transition(transition_frame, settled_one, settled_two),
    )
    assert audit.stable_change
    assert audit.terminal_window_size == 2
    assert audit.reasons == ()


def test_terminal_window_rejects_dynamic_pixel_negative() -> None:
    before = _captured(pixel="pre-p", a11y="same-a", signature="pre-s")
    post_one = _captured(pixel="dynamic-1", a11y="same-a", signature="post-1")
    post_two = _captured(pixel="dynamic-2", a11y="same-a", signature="post-2")
    audit = audit_stable_change_v0_2_2(
        before=before,
        transition=_transition(post_one, post_two),
    )
    assert not audit.stable_change
    assert "terminal_pixels_unsettled" in audit.reasons


def test_terminal_window_rejects_missing_a11y_negative() -> None:
    before = _captured(pixel="pre-p", a11y="pre-a", signature="pre-s")
    post_one = _captured(pixel="post-p", a11y=None, signature="post-s")
    post_two = _captured(pixel="post-p", a11y=None, signature="post-s")
    audit = audit_stable_change_v0_2_2(
        before=before,
        transition=_transition(post_one, post_two),
    )
    assert not audit.stable_change
    assert "terminal_a11y_unavailable" in audit.reasons


def test_terminal_window_rejects_stable_no_change() -> None:
    before = _captured(pixel="same-p", a11y="same-a", signature="same-s")
    post_one = _captured(pixel="same-p", a11y="same-a", signature="same-s")
    post_two = _captured(pixel="same-p", a11y="same-a", signature="same-s")
    audit = audit_stable_change_v0_2_2(
        before=before,
        transition=_transition(post_one, post_two),
    )
    assert not audit.stable_change
    assert "terminal_did_not_change" in audit.reasons


def test_qualification_stabilizer_takes_exactly_four_frozen_samples() -> None:
    class State:
        def __init__(self, value: int) -> None:
            self.pixels = np.full((2, 2, 3), value, dtype=np.uint8)
            self.ui_elements = [{"text": str(value), "package_name": "example.package"}]

    class Env:
        def __init__(self) -> None:
            self.index = 0

        def get_state(self, *, wait_to_stabilize: bool) -> State:
            assert wait_to_stabilize
            self.index += 1
            return State(self.index)

    sleeps: list[float] = []
    env = Env()
    stabilizer = QualificationObservationStabilizerV022(sleep_fn=sleeps.append)
    before = stabilizer.capture(State(0))
    transition = stabilizer.observe_after(env=env, before=before)
    assert len(transition.post_observations) == 4
    assert sleeps == [1.0, 1.0, 1.0]
