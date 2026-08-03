from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.eest_ac.qualification_v0_2_1 import (
    ActionQualificationDeciderV021,
    QualificationDecisionFailure,
)
from raven_m.models.transformers_client import ModelCall


def response(action: dict) -> str:
    return json.dumps(
        {
            "status": "continue",
            "action": action,
            "intent": "qualification",
            "evidence": [],
            "citations": [],
        },
        separators=(",", ":"),
    )


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
    result = ActionQualificationDeciderV021(
        client=FakeClient(outputs),  # type: ignore[arg-type]
        system_prompt="contract",
    ).decide(
        image_path=Path("screen.png"),
        user_prompt="probe",
        episode_id="episode",
        calls=calls,
        attempts=attempts,
        record_call=written.append,
    )
    return result, calls, attempts, written


def test_initial_direct_uses_one_recorded_call() -> None:
    result, calls, attempts, written = run([response({"type": "press_back"})])
    assert result.accepted_stage == "initial_direct"
    assert result.initial_direct_schema_pass
    assert len(calls) == len(attempts) == len(written) == 1


def test_initial_safe_normalization_uses_no_repair() -> None:
    result, calls, attempts, _ = run(
        [response({"type": "swipe", "x": 0.5, "y": 0.8, "direction": "up", "distance": 0.6})]
    )
    assert result.accepted_stage == "initial_normalized"
    assert result.parsed.decision["action"]["y2"] == pytest.approx(0.2)
    assert len(calls) == len(attempts) == 1


def test_one_repair_can_replace_unsupported_action() -> None:
    result, calls, attempts, _ = run(
        [
            response({"type": "press", "key": "recent_app"}),
            response({"type": "press_back"}),
        ]
    )
    assert result.accepted_stage == "repair"
    assert result.repair_used
    assert result.initial_error["code"] == "UNSUPPORTED_PRESS_KEY_RECENT_APP"
    assert len(calls) == len(attempts) == 2


def test_identical_invalid_repair_fails_with_two_counted_calls() -> None:
    invalid = response({"type": "press", "key": "recent_app"})
    calls: list[dict] = []
    attempts: list[dict] = []
    written: list[dict] = []
    with pytest.raises(QualificationDecisionFailure) as caught:
        ActionQualificationDeciderV021(
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
    assert caught.value.code == "REPAIR_IDENTICAL_INVALID_ACTION"
    assert len(calls) == len(attempts) == len(written) == 2
