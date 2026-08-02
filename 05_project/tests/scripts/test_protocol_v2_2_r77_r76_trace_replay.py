from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from PIL import Image
import pytest

from raven_m.controller.episode_controller import (
    EpisodeController,
    ModelOutputInvalid,
)
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
R76_REPORT = ROOT / "reports/protocol_v2_2_r76_h17_candidate_stopped.json"
R76_REPORT_SHA256 = (
    "f88a60ec248dedf83677b054f7fab1ac1a9aa8fee04f38294c8c62a8441d772c"
)
R76_EPISODE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r76_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
CURRENT_LIST = R76_EPISODE / "step_016_before.png"
UPPER_FIELD = (
    R76_EPISODE
    / "step_014_before_target_row_y_0_747_requested_field.png"
)
LOWER_FIELD = (
    R76_EPISODE
    / "step_009_before_target_row_y_0_834_requested_field.png"
)
ACTION_SCHEMA = ROOT / "05_project/schemas/action.raven.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023 in the OpenTracks app? "
    "Answer with the activity type only. If there are multiple types, "
    "format your answer in a comma separated list."
)
ANSWER = "cycling, inline skating"
UPPER_KEY = "target-row-y:0.747"
LOWER_KEY = "target-row-y:0.834"
UPPER_SHA256 = (
    "6f30807e41f2eb51921496eac7000f0b7eae3b2e370dc69953e54de9daf75dae"
)
LOWER_SHA256 = (
    "1bd4dec3c9fb25996be95b8e59327986c6610dea36a959450f2027c050848704"
)


def answer_decision() -> dict[str, Any]:
    return {
        "status": "done",
        "action": {
            "type": "answer",
            "text": ANSWER,
            "text_origin": "current_screen",
            "source_memory_ids": [],
        },
        "expected_outcome": "The two exact activity types are returned.",
        "decision_summary": "Answer from the two routed detail frames.",
        "state_delta": [],
        "memory_citations": [],
        "completion_evidence": [
            {
                "claim": "Both exact values are visible in routed frames.",
                "evidence": "direct_screen",
                "memory_ids": [],
            }
        ],
    }


def model_call(label: str, content: dict[str, Any]) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="r77-r76-trace-replay",
        idempotency_key=label,
        image_sha256="0" * 64,
        image_sha256s=("0" * 64,),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=json.dumps(content),
        usage={
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        },
        raven_meta={},
    )


class R77VisualClient:
    def __init__(self, *, critic_verdict: str = "proceed") -> None:
        self.critic_verdict = critic_verdict
        self.requests: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.requests.append(kwargs)
        label = str(kwargs["call_label"])
        if label.startswith("critic_step_"):
            accepted = self.critic_verdict == "proceed"
            return model_call(
                label,
                {
                    "schema_version": "critic.v1",
                    "verdict": self.critic_verdict,
                    "issue": "" if accepted else "One crop is unreadable.",
                    "recommended_constraint": (
                        "Accept the exact ordered routed evidence."
                        if accepted
                        else "Obtain a readable crop for every target row."
                    ),
                    "memory_ids": [],
                },
            )
        return model_call(label, answer_decision())


def target_list_elements() -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for title, date, center in (
        ("Earlier activity", "1 Oct", 0.66),
        ("Skill work", "24 Sep", 0.747292),
        ("Recovery day", "24 Sep", 0.834375),
    ):
        elements.extend(
            [
                {
                    "text": title,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.08,
                        "x_max": 0.70,
                        "y_min": center - 0.025,
                        "y_max": center + 0.025,
                    },
                },
                {
                    "text": date,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.88,
                        "x_max": 0.98,
                        "y_min": center - 0.025,
                        "y_max": center + 0.025,
                    },
                },
            ]
        )
    return elements


def prepared_guard() -> ProtocolV2DecisionGuard:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=GOAL)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = [LOWER_KEY, UPPER_KEY]
    guard.target_row_identity_confirmed_visit_keys = [LOWER_KEY, UPPER_KEY]
    guard.target_date_row_observations = [
        {"target_row_centers": [0.747292, 0.834375]}
    ]
    guard.target_row_detail_frames = [
        {
            "visit_key": LOWER_KEY,
            "path": str(LOWER_FIELD),
            "sha256": LOWER_SHA256,
            "source_path": str(LOWER_FIELD),
            "source_sha256": LOWER_SHA256,
            "requested_field_evidence_explicit": True,
        },
        {
            "visit_key": UPPER_KEY,
            "path": str(UPPER_FIELD),
            "sha256": UPPER_SHA256,
            "source_path": str(UPPER_FIELD),
            "source_sha256": UPPER_SHA256,
            "requested_field_evidence_explicit": True,
        },
    ]
    return guard


def controller_for(
    client: R77VisualClient,
    guard: ProtocolV2DecisionGuard,
) -> EpisodeController:
    return EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=4,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=guard,
        protocol_v2=True,
        protocol_v2_2=True,
        visual_source_critic_prompt="critic",
    )


def call_and_parse(
    controller: EpisodeController,
) -> tuple[dict[str, Any], list[ModelCall], dict[str, Any]]:
    return controller._call_and_parse(
        image_path=CURRENT_LIST,
        page_semantic_sha256=(
            "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
        ),
        destination_picker_is_active=False,
        ui_elements=target_list_elements(),
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r77-r76-trace-replay",
        step=16,
        model_call_count=0,
    )


def test_r77_replays_exact_r76_authority_bottleneck() -> None:
    assert sha256(R76_REPORT.read_bytes()).hexdigest() == R76_REPORT_SHA256
    report = json.loads(R76_REPORT.read_text(encoding="utf-8"))
    bottleneck = report["terminal_provenance_bottleneck"]
    assert bottleneck["answer_candidate_text"] == ANSWER
    assert bottleneck["initial_executor_failure"][
        "invalid_source_memory_ids"
    ] == [UPPER_KEY, LOWER_KEY]
    assert bottleneck["repair_executor_candidate"] == {
        "text_origin": "current_screen",
        "source_memory_ids": [],
        "memory_citations": [],
        "schema_valid": True,
    }
    assert bottleneck["visual_critic"]["accepted"] is False
    assert "historical screenshots" in bottleneck["visual_critic"][
        "misclassification"
    ]


def test_r77_manifest_is_ordered_hash_bound_and_answer_free() -> None:
    manifest = prepared_guard().target_row_detail_evidence_manifest()
    assert manifest["authority"] == (
        "controller_bound_same_episode_current_visual_evidence"
    )
    assert manifest["answer_values_in_manifest"] is False
    assert manifest["frame_count"] == 2
    assert manifest["ordered_frames"] == [
        {
            "ordinal": 1,
            "visit_key": UPPER_KEY,
            "crop_sha256": UPPER_SHA256,
            "requested_field_evidence_explicit": True,
            "row_identity_confirmed": True,
        },
        {
            "ordinal": 2,
            "visit_key": LOWER_KEY,
            "crop_sha256": LOWER_SHA256,
            "requested_field_evidence_explicit": True,
            "row_identity_confirmed": True,
        },
    ]
    rendered = json.dumps(manifest).lower()
    assert "cycling" not in rendered
    assert "inline skating" not in rendered


def test_r77_manifest_fails_closed_on_crop_hash_drift(tmp_path: Path) -> None:
    guard = prepared_guard()
    replacement = tmp_path / "changed.png"
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(replacement)
    guard.target_row_detail_frames[0]["path"] = str(replacement)
    with pytest.raises(RuntimeError, match="frame hash mismatch"):
        guard.target_row_detail_evidence_manifest()


def test_r77_manifest_fails_closed_without_row_identity_confirmation() -> None:
    guard = prepared_guard()
    guard.target_row_identity_confirmed_visit_keys.remove(LOWER_KEY)
    with pytest.raises(RuntimeError, match="identity-unconfirmed row"):
        guard.target_row_detail_evidence_manifest()


def test_r77_executor_prompt_uses_current_screen_provenance() -> None:
    guard = prepared_guard()
    prompt = EpisodeController._user_prompt(
        goal=GOAL,
        step=16,
        max_steps=24,
        model_calls=29,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="Returned to the verified target-date list.",
        protocol_v2=True,
        protocol_v2_2=True,
        target_row_progress=guard.target_row_progress_record(),
        target_row_routed_evidence_manifest=(
            guard.target_row_detail_evidence_manifest()
        ),
    )
    assert "DATED_TARGET_ROUTED_VISUAL_EVIDENCE_AUTHORITY" in prompt
    assert "not a historical memory record" in prompt
    assert "values do not also need to appear on the current list" in prompt
    assert "action.text_origin=current_screen" in prompt
    assert "action.source_memory_ids=[]" in prompt
    assert "memory_citations=[]" in prompt
    assert "memory_ids=[]" in prompt
    assert "visit_key is an evidence handle, never a memory ID" in prompt


def test_r77_critic_receives_same_episode_authority_and_ordered_manifest(
) -> None:
    guard = prepared_guard()
    client = R77VisualClient()
    parsed, calls, meta = call_and_parse(controller_for(client, guard))
    assert len(calls) == 2
    assert parsed["action"] == answer_decision()["action"]
    assert meta["dated_visual_answer_assessment"]["accepted"] is True
    critic_request = next(
        request for request in client.requests
        if str(request["call_label"]).startswith("critic_step_")
    )
    payload = json.loads(critic_request["user_prompt"])
    contract = payload["same_episode_routed_visual_evidence_contract"]
    assert contract["authority"] == (
        "controller_bound_same_episode_current_visual_evidence"
    )
    assert contract[
        "requested_field_values_must_also_appear_on_current_list"
    ] is False
    assert contract["routed_frames_are_historical_memory"] is False
    assert contract["visit_keys_are_memory_ids"] is False
    assert contract["required_memory_ids"] == []
    manifest = payload["same_episode_routed_visual_evidence"]
    assert [
        item["crop_sha256"] for item in manifest["ordered_frames"]
    ] == [UPPER_SHA256, LOWER_SHA256]
    assert ANSWER not in json.dumps(manifest)
    labels = [
        label for label, _ in critic_request["context_images"]
    ]
    assert labels == [
        "DATED_TARGET_REQUESTED_FIELD SAME_EPISODE_CONTROLLER_BOUND "
        f"ROW_1_OF_2 {UPPER_KEY}",
        "DATED_TARGET_REQUESTED_FIELD SAME_EPISODE_CONTROLLER_BOUND "
        f"ROW_2_OF_2 {LOWER_KEY}",
    ]
    assert guard.target_row_visual_answer_accept_count == 1


def test_r77_critic_rejection_still_blocks_answer() -> None:
    guard = prepared_guard()
    client = R77VisualClient(critic_verdict="reject_completion")
    with pytest.raises(ModelOutputInvalid):
        call_and_parse(controller_for(client, guard))
    assert guard.target_row_visual_answer_accept_count == 0
    assert guard.answer_association_block_count == 2
    assert all(
        record["reason"] == "dated_list_answer_association_blocked"
        for record in guard.validation_blocks
    )
