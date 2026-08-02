from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard


ROOT = Path(__file__).resolve().parents[3]
R77_REPORT = ROOT / "reports/protocol_v2_2_r77_h17_candidate_stopped.json"
R77_REPORT_SHA256 = (
    "c989588c4655ee4912fba95991142cc4a87d3f9051c9bf7e967f6e416d6ae872"
)
R77_EPISODE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r77_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
UPPER_FIELD = (
    R77_EPISODE
    / "step_005_before_target_row_y_0_747_requested_field.png"
)
LOWER_FIELD = (
    R77_EPISODE
    / "step_010_before_target_row_y_0_834_requested_field.png"
)
UPPER_KEY = "target-row-y:0.747"
LOWER_KEY = "target-row-y:0.834"
UPPER_SHA256 = (
    "0883f3b6359871bf13740050bf0321a48cc0f6901d5d067da0cbf7640cd7a088"
)
LOWER_SHA256 = (
    "9c0242a6473e07535e56f824e76db53d1bb77201d4c7c47aa72f6a690bf82768"
)


def episode() -> dict:
    return json.loads(
        (R77_EPISODE / "episode.json").read_text(encoding="utf-8")
    )


def prepared_guard() -> ProtocolV2DecisionGuard:
    source = episode()["protocol_v2_guard"]
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=episode()["task_goal"])
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = list(source["target_row_visit_keys"])
    guard.target_row_identity_confirmed_visit_keys = list(
        source["target_row_identity_confirmed_visit_keys"]
    )
    guard.target_date_row_observations = list(
        source["target_date_row_observations"]
    )
    guard.target_row_detail_frames = [
        {
            "visit_key": UPPER_KEY,
            "path": str(UPPER_FIELD),
            "sha256": UPPER_SHA256,
            "source_path": str(R77_EPISODE / "step_005_before.png"),
            "source_sha256": (
                "1ecf47c64513339ae1f3f1c8356e7aac13805359b05d911684701eecb75a9a80"
            ),
            "requested_field_evidence_explicit": True,
        },
        {
            "visit_key": LOWER_KEY,
            "path": str(LOWER_FIELD),
            "sha256": LOWER_SHA256,
            "source_path": str(R77_EPISODE / "step_010_before.png"),
            "source_sha256": (
                "86557899a6b65a9db2d4a2004a119dc95f99a1e52524c4763bc25563329e565f"
            ),
            "requested_field_evidence_explicit": True,
        },
    ]
    return guard


def terminal_prompt() -> str:
    guard = prepared_guard()
    return EpisodeController._user_prompt(
        goal=episode()["task_goal"],
        step=12,
        max_steps=20,
        model_calls=21,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome=(
            'Executed {"type": "press_back"}; the screenshot changed; '
            "the semantic UI changed."
        ),
        memory_context="stale history must not enter terminal evidence",
        protocol_v2=True,
        protocol_v2_2=True,
        target_row_progress=guard.target_row_progress_record(),
        target_row_routed_evidence_manifest=(
            guard.target_row_detail_evidence_manifest()
        ),
    )


def test_r78_replays_exact_r77_success_and_context_cap_stop() -> None:
    assert sha256(R77_REPORT.read_bytes()).hexdigest() == R77_REPORT_SHA256
    report = json.loads(R77_REPORT.read_text(encoding="utf-8"))
    assert report["result"]["success"] is True
    assert report["result"]["evaluator_reward"] == 1.0
    assert report["r77_mechanism_live_validation"][
        "target_row_visual_answer_accept_count"
    ] == 1
    cap = report["context_cap_bottleneck"]
    assert cap["configured_prompt_token_cap"] == 8192
    assert cap["maximum_observed_prompt_tokens"] == 8982
    assert cap["overage_tokens"] == 790
    assert cap["offending_step"] == 12


def test_r78_projects_exact_r77_terminal_prompt_with_large_margin() -> None:
    live_prompt = episode()["steps"][12]["user_prompt"]
    projected = terminal_prompt()
    assert len(live_prompt) == 9185
    assert len(projected) == 2912
    assert len(live_prompt) - len(projected) == 6273
    assert len(projected) < 3200
    assert len(projected) / len(live_prompt) < 0.33


def test_r78_terminal_projection_retains_every_answer_safety_contract() -> None:
    prompt = terminal_prompt()
    for required in (
        "TASK:",
        "STEP/BUDGET:",
        "PREVIOUS_ACTION_AND_OBSERVED_OUTCOME:",
        "MEMORY_CONTEXT:",
        "DATED_TARGET_ROW_PROGRESS:",
        "DATED_TARGET_ROUTED_VISUAL_EVIDENCE:",
        "DATED_TARGET_ROUTED_VISUAL_EVIDENCE_AUTHORITY:",
        "DATED_TARGET_ROUTED_ANSWER_PROVENANCE:",
        "TERMINAL_EVIDENCE_SCOPE:",
        "CURRENT_SCREENSHOT:",
        "text_origin=current_screen",
        "source_memory_ids=[]",
        "memory_citations=[]",
        "memory_ids=[]",
        "status=fail and action=null",
        "matching the action schema",
    ):
        assert required in prompt
    assert "cycling" not in prompt.lower()
    assert "inline skating" not in prompt.lower()


def test_r78_terminal_projection_omits_only_irrelevant_navigation_guidance(
) -> None:
    prompt = terminal_prompt()
    for omitted in (
        "COORDINATE_CHECK:",
        "ACTION_FIELD_CHECK:",
        "FOCUSED_TEXT_INPUT_CHECK:",
        "SEMANTIC_PROGRESS_CHECK:",
        "TASK_SCOPE_CHECK:",
        "PLANNER_CONSISTENCY:",
        "HORIZONTAL_CLIPPED_ROW_NAVIGATION:",
        "CHRONOLOGICAL_HISTORY_NAVIGATION:",
        "RELATIVE_DATE_GROUNDING:",
        "FILES_SOURCE_NAVIGATION:",
    ):
        assert omitted not in prompt


def test_r78_nonterminal_prompt_is_not_projected() -> None:
    prompt = EpisodeController._user_prompt(
        goal="Inspect the requested current-screen field.",
        step=2,
        max_steps=20,
        model_calls=3,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="The app opened.",
        protocol_v2=True,
        protocol_v2_2=True,
    )
    assert "COORDINATE_CHECK:" in prompt
    assert "ACTION_FIELD_CHECK:" in prompt
    assert "CHRONOLOGICAL_HISTORY_NAVIGATION:" in prompt
    assert "TERMINAL_EVIDENCE_SCOPE:" not in prompt


def test_r78_terminal_projection_fails_closed_on_incomplete_progress() -> None:
    guard = prepared_guard()
    progress = guard.target_row_progress_record()
    assert progress is not None
    progress["all_detail_frames_captured"] = False
    with pytest.raises(RuntimeError, match="complete target-row progress"):
        EpisodeController._user_prompt(
            goal=episode()["task_goal"],
            step=12,
            max_steps=20,
            model_calls=21,
            max_model_calls=64,
            screen_width=1080,
            screen_height=2400,
            previous_outcome="Returned to the list.",
            protocol_v2=True,
            protocol_v2_2=True,
            target_row_progress=progress,
            target_row_routed_evidence_manifest=(
                guard.target_row_detail_evidence_manifest()
            ),
        )


def test_r78_keeps_exact_r77_visual_evidence_bytes_and_order() -> None:
    guard = prepared_guard()
    images = guard.target_row_detail_context_images()
    assert [label for label, _ in images] == [
        "DATED_TARGET_REQUESTED_FIELD SAME_EPISODE_CONTROLLER_BOUND "
        f"ROW_1_OF_2 {UPPER_KEY}",
        "DATED_TARGET_REQUESTED_FIELD SAME_EPISODE_CONTROLLER_BOUND "
        f"ROW_2_OF_2 {LOWER_KEY}",
    ]
    assert [
        sha256(Path(path).read_bytes()).hexdigest()
        for _, path in images
    ] == [UPPER_SHA256, LOWER_SHA256]
    assert sha256(
        (R77_EPISODE / "step_012_before.png").read_bytes()
    ).hexdigest() == (
        "7843428657b432b600a3300ed3f6b00dd9639146ba3e389bffe6e9158af71088"
    )


def test_r78_keeps_shared_system_prompts_byte_exact() -> None:
    assert sha256(
        (ROOT / "05_project/prompts/executor_raven_v2.md").read_bytes()
    ).hexdigest() == (
        "4810e577f19c987ee8ec875c8c5e042e6af314a7d2a409166f28dcd7d7910877"
    )
    assert sha256(
        (ROOT / "05_project/prompts/critic_v1.md").read_bytes()
    ).hexdigest() == (
        "82f0be700752aa38cd229e6ea66feeee7974b5a6ce5760326616ea2be053c7a5"
    )
