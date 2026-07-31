from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.history.policies import (
    FullRavenMemoryPolicyV2,
    make_history_policy_v2,
)
from raven_m.models.transformers_client import ModelCall


def call(content: str, label: str) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="e",
        idempotency_key=label,
        image_sha256="0" * 64,
        image_sha256s=("0" * 64,),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=content,
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        raven_meta={},
    )


class CriticClient:
    def __init__(self, verdict: str) -> None:
        self.verdict = verdict

    def generate(self, **kwargs) -> ModelCall:
        content = json.dumps(
            {
                "schema_version": "critic.v1",
                "verdict": self.verdict,
                "issue": "Completion candidate reviewed.",
                "recommended_constraint": "Re-observe the persisted result.",
                "memory_ids": [],
            }
        )
        return call(content, kwargs["call_label"])


def candidate() -> dict:
    return {
        "status": "done",
        "action": None,
        "memory_citations": [],
        "completion_evidence": [
            {
                "claim": "The saved item is visible.",
                "evidence": "direct_screen",
                "memory_ids": [],
            }
        ],
    }


def consequential_candidate() -> dict:
    return {
        "status": "continue",
        "action": {"type": "tap", "x": 0.9, "y": 0.1},
        "expected_outcome": "The item is saved.",
        "decision_summary": "Tap the SAVE button to persist the item.",
        "memory_citations": [],
        "completion_evidence": [],
    }


def policy(tmp_path: Path, verdict: str) -> tuple[FullRavenMemoryPolicyV2, Path]:
    image = tmp_path / "screen.png"
    Image.new("RGB", (8, 8), "white").save(image)
    value = FullRavenMemoryPolicyV2(
        client=CriticClient(verdict),  # type: ignore[arg-type]
        planner_prompt="planner",
        critic_prompt="critic",
    )
    value.reset(
        episode_dir=tmp_path,
        goal="Save the item",
        episode_id="e",
        task_id="T",
    )
    value.context()
    return value, image


def test_v2_accepts_current_screen_completion_same_turn(tmp_path: Path) -> None:
    value, image = policy(tmp_path, "proceed")
    value.validate_decision(candidate())
    result = value.adjudicate_completion(
        candidate(),
        image_path=image,
        episode_id="e",
        step=0,
        remaining_model_calls=2,
    )
    assert result.accepted
    assert len(result.calls) == 1
    assert result.record["trigger"] == "completion_candidate"


def test_v2_rejects_completion_when_same_turn_critic_rejects(
    tmp_path: Path,
) -> None:
    value, image = policy(tmp_path, "reject_completion")
    result = value.adjudicate_completion(
        candidate(),
        image_path=image,
        episode_id="e",
        step=0,
        remaining_model_calls=2,
    )
    assert not result.accepted
    assert "rejected completion" in result.error


def test_v2_rejects_consequential_action_without_critic_approval(
    tmp_path: Path,
) -> None:
    value, image = policy(tmp_path, "reobserve")
    decision = consequential_candidate()
    result = value.adjudicate_action(
        decision,
        image_path=image,
        episode_id="e",
        step=2,
        remaining_model_calls=2,
    )
    assert not result.accepted
    assert "rejected commit" in result.error
    assert result.record["trigger"] == "consequential_action_candidate"
    assert value.critic_constraint["blocked_action"] == decision["action"]


def test_v2_skips_action_critic_for_reversible_navigation(
    tmp_path: Path,
) -> None:
    value, image = policy(tmp_path, "reobserve")
    decision = {
        **consequential_candidate(),
        "expected_outcome": "The details page opens.",
        "decision_summary": "Open the visible details page.",
    }
    result = value.adjudicate_action(
        decision,
        image_path=image,
        episode_id="e",
        step=2,
        remaining_model_calls=2,
    )
    assert result.accepted
    assert not result.calls
    assert result.record is None


def test_v2_destination_picker_override_uses_actual_control_semantics(
    tmp_path: Path,
) -> None:
    value, image = policy(tmp_path, "reobserve")
    misleading_prose = {
        **consequential_candidate(),
        "expected_outcome": "The navigation drawer opens.",
        "decision_summary": (
            "Open the menu to confirm the destination before moving."
        ),
    }
    reversible = value.adjudicate_action(
        misleading_prose,
        image_path=image,
        episode_id="e",
        step=2,
        remaining_model_calls=2,
        consequential_action_candidate=False,
    )
    assert reversible.accepted
    assert not reversible.calls
    assert reversible.record is None

    visually_bound_commit = {
        **misleading_prose,
        "expected_outcome": "The next view opens.",
        "decision_summary": "Open the next view.",
    }
    commit = value.adjudicate_action(
        visually_bound_commit,
        image_path=image,
        episode_id="e",
        step=2,
        remaining_model_calls=2,
        consequential_action_candidate=True,
    )
    assert not commit.accepted
    assert len(commit.calls) == 1
    assert commit.record["trigger"] == "consequential_action_candidate"


def test_m0_and_mrel_share_v2_completion_implementation() -> None:
    kwargs = {
        "client": CriticClient("proceed"),
        "summary_system_prompt": "summary",
        "planner_system_prompt": "planner",
        "critic_system_prompt": "critic",
    }
    m0 = make_history_policy_v2("M0", **kwargs)  # type: ignore[arg-type]
    mrel = make_history_policy_v2("MREL", **kwargs)  # type: ignore[arg-type]
    assert isinstance(m0, FullRavenMemoryPolicyV2)
    assert isinstance(mrel, FullRavenMemoryPolicyV2)
    assert m0.manager.config.reliability_aware
    assert not mrel.manager.config.reliability_aware


def test_v2_critic_constraint_blocks_same_action(tmp_path: Path) -> None:
    value, _ = policy(tmp_path, "proceed")
    blocked = {"type": "tap", "x": 0.9, "y": 0.1}
    value.critic_constraint = {
        "schema_version": "critic_constraint.v1",
        "verdict": "reobserve",
        "blocked_action": blocked,
        "recommended_constraint": "re-observe before retrying",
        "created_step": 3,
    }
    decision = {
        "status": "continue",
        "action": blocked,
        "memory_citations": [],
        "completion_evidence": [],
    }
    with pytest.raises(ActionValidationError, match="CRITIC_CONSTRAINT"):
        value.validate_decision(decision)


def test_v2_late_transition_expires_stale_critic_constraint(
    tmp_path: Path,
) -> None:
    value, _ = policy(tmp_path, "proceed")
    value.critic_alert = {
        "schema_version": "critic.v1",
        "verdict": "reobserve",
        "issue": "Search did not change the UI.",
    }
    value.critic_constraint = {
        "schema_version": "critic_constraint.v1",
        "verdict": "reobserve",
        "blocked_action": {"type": "tap", "x": 0.72, "y": 0.085},
        "recommended_constraint": "Tap the location pin icon.",
        "created_step": 9,
    }
    value.manager.working = [
        {
            "step": 9,
            "decision_summary": "Open Search.",
            "action": {"type": "tap", "x": 0.72, "y": 0.085},
            "observed_outcome": (
                "Executed Search; the semantic UI did not change."
            ),
            "page_signature": "ui:old",
        }
    ]
    result = value.reconcile_late_semantic_transition(
        completed_step=9,
        previous_after_semantic_sha256="a" * 64,
        current_before_semantic_sha256="b" * 64,
    )
    assert result["reconciled"] is True
    assert result["critic_constraint_cleared"]["created_step"] == 9
    assert value.critic_constraint is None
    assert value.critic_alert is None
    assert "changed after delayed readiness" in (
        value.manager.working[-1]["observed_outcome"]
    )
