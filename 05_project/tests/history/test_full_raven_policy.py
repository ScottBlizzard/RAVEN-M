from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.history.policies import FullRavenMemoryPolicy, HistoryEntry
from raven_m.models.transformers_client import ModelCall


def model_call(content: str, label: str) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="episode-a",
        idempotency_key=label,
        image_sha256="0" * 64,
        image_sha256s=("0" * 64,),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        raven_meta={},
    )


class FullClient:
    def generate(self, **kwargs) -> ModelCall:
        label = kwargs["call_label"]
        if label.startswith("planner"):
            content = (
                '{"schema_version":"plan.v1","current_subgoal":'
                '{"subgoal_id":"sg_01","description":"Save the note."},'
                '"open_requirements":["Save the note."],'
                '"required_variables":[],"completion_requirements":'
                '[{"id":"cr_1","description":"The note is saved.",'
                '"evidence_memory_ids":[]}],'
                '"plan_summary":"Save the visible note."}'
            )
        else:
            content = (
                '{"schema_version":"critic.v1","verdict":"recover",'
                '"issue":"The action repeated without visible effect.",'
                '"recommended_constraint":"Avoid the same tap and re-observe.",'
                '"memory_ids":[]}'
            )
        return model_call(content, label)


def entry(tmp_path: Path, step: int) -> HistoryEntry:
    path = tmp_path / f"step_{step:03d}_after.png"
    path.write_bytes(b"same")
    digest = sha256(b"same").hexdigest()
    return HistoryEntry(
        step=step,
        decision_summary="Tap save.",
        action={"type": "tap", "x": 0.9, "y": 0.1},
        observed_outcome="No visible change.",
        screenshot_path=path,
        screenshot_sha256=digest,
        before_screenshot_sha256=digest,
        expected_outcome="The note closes.",
    )


def test_full_policy_calls_planner_then_loop_critic(tmp_path: Path) -> None:
    policy = FullRavenMemoryPolicy(
        client=FullClient(),  # type: ignore[arg-type]
        planner_prompt="planner",
        critic_prompt="critic",
    )
    policy.reset(
        episode_dir=tmp_path,
        goal="Save the note",
        episode_id="episode-a",
        task_id="DevTask",
    )
    first = policy.observe(
        entry(tmp_path, 0),
        episode_id="episode-a",
        remaining_model_calls=4,
    )
    assert first.details["role_call_counts"]["planner"] == 1
    assert first.details["role_call_counts"]["critic"] == 0
    second = policy.observe(
        entry(tmp_path, 1),
        episode_id="episode-a",
        remaining_model_calls=4,
    )
    assert second.details["loop_detected"]
    assert second.details["role_call_counts"]["critic"] == 1
    context = policy.context().rendered
    assert '"planner_state"' in context
    assert '"critic_alert"' in context


def test_full_policy_rejects_done_without_fact_evidence(tmp_path: Path) -> None:
    policy = FullRavenMemoryPolicy(
        client=FullClient(),  # type: ignore[arg-type]
        planner_prompt="planner",
        critic_prompt="critic",
    )
    policy.reset(
        episode_dir=tmp_path,
        goal="Save the note",
        episode_id="episode-a",
        task_id="DevTask",
    )
    policy.context()
    with pytest.raises(ActionValidationError, match="Completion requires"):
        policy.validate_decision(
            {"status": "done", "memory_citations": []}
        )
