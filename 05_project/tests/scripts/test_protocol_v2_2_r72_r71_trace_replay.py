from __future__ import annotations

import json
from pathlib import Path

import pytest

from android_world.env import adb_utils
from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    requested_field_value_assessment,
)
from raven_m.env.androidworld_adapter import (
    current_native_popup_menu_ui_elements,
    native_popup_menu_ui_elements_from_xml,
)
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
MENU_SCREENSHOT = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r71_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/"
    "step_006_before.png"
)
ACTION_SCHEMA = ROOT / "05_project/schemas/action.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023? "
    "Answer with the activity type only."
)


def popup_xml(
    *,
    labels: tuple[str, ...] = (
        "Markers",
        "Edit",
        "Delete",
        "Resume track",
        "Settings",
    ),
    row_height: int = 126,
    gap_after_first: int = 0,
) -> str:
    rows = []
    y_min = 1519
    for index, label in enumerate(labels):
        y_max = y_min + row_height
        rows.append(
            '<node class="android.widget.LinearLayout" '
            'package="example.app" enabled="true" '
            f'bounds="[0,{y_min}][515,{y_max}]">'
            '<node class="android.widget.RelativeLayout" '
            'package="example.app" enabled="true" '
            f'bounds="[42,{y_min + 34}][473,{y_max - 35}]">'
            f'<node text="{label}" resource-id="example.app:id/title" '
            'class="android.widget.TextView" package="example.app" '
            'enabled="true" clickable="false" '
            f'bounds="[42,{y_min + 34}][473,{y_max - 35}]" />'
            "</node></node>"
        )
        y_min = y_max + (gap_after_first if index == 0 else 0)
    list_y_max = y_min
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hierarchy rotation="0"><node class="android.widget.FrameLayout" '
        'package="example.app" enabled="true" bounds="[0,0][1080,2400]">'
        '<node class="android.widget.ListView" package="example.app" '
        f'enabled="true" bounds="[0,1519][515,{list_y_max}]">'
        + "".join(rows)
        + "</node></node></hierarchy>"
    )


def parsed_rows(xml: str | None = None) -> list[dict]:
    return native_popup_menu_ui_elements_from_xml(
        xml if xml is not None else popup_xml(),
        screen_width=1080,
        screen_height=2400,
    )


class EditClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        decision = {
            "status": "continue",
            "action": {"type": "tap", "x": 0.25, "y": 0.71},
            "expected_outcome": (
                "The existing activity details open for read-only inspection."
            ),
            "decision_summary": (
                "Tap Edit to inspect the existing activity type."
            ),
            "state_delta": [],
            "memory_citations": [],
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


def test_native_popup_parser_recovers_exact_row_geometry() -> None:
    rows = parsed_rows()
    assert [item["text"] for item in rows] == [
        "Markers",
        "Edit",
        "Delete",
        "Resume track",
        "Settings",
    ]
    assert all(item["source"] == "native_uiautomator_popup_row" for item in rows)
    assert all(item["is_clickable"] is True for item in rows)
    assert rows[1]["bbox_pixels"] == {
        "x_min": 0,
        "x_max": 515,
        "y_min": 1645,
        "y_max": 1771,
    }


def test_edit_is_inspection_candidate_but_adjacent_delete_is_mutation() -> None:
    rows = parsed_rows()
    edit = requested_field_value_assessment(
        GOAL,
        rows,
        {"status": "continue", "action": {"type": "tap", "x": 0.25,
                                           "y": 0.71}},
        screen_width=1080,
        screen_height=2400,
    )
    assert edit["inspection_control_hit"] is True
    assert edit["mutation_control_hit"] is False
    assert edit["native_inspection_candidate_count"] == 1
    assert edit["visual_inspection_fallback_evaluated"] is False
    assert edit["inspection_control_candidates"] == [
        {
            "label": "Edit",
            "bbox": {
                "x_min": 0.0,
                "x_max": 0.476852,
                "y_min": 0.685417,
                "y_max": 0.737917,
            },
            "center": {"x": 0.238426, "y": 0.711667},
            "source": "native_uiautomator_popup_row",
        }
    ]

    delete = requested_field_value_assessment(
        GOAL,
        rows,
        {"status": "continue", "action": {"type": "tap", "x": 0.25,
                                           "y": 0.765}},
        screen_width=1080,
        screen_height=2400,
    )
    assert delete["inspection_control_hit"] is False
    assert delete["mutation_control_hit"] is True
    assert delete["mutation_control_hit_labels"] == ["Delete"]


@pytest.mark.parametrize(
    "xml",
    [
        "not xml",
        popup_xml(labels=("Markers", "Edit", "Settings")),
        popup_xml(gap_after_first=8),
        popup_xml(labels=("Edit", "Delete", "Edit")),
        popup_xml(row_height=1),
    ],
)
def test_native_popup_parser_fails_closed_on_ambiguous_structures(
    xml: str,
) -> None:
    assert parsed_rows(xml) == []


def test_multiple_valid_popup_lists_fail_closed() -> None:
    one = popup_xml()
    inner = one.split(">", 2)[2].rsplit("</node></hierarchy>", 1)[0]
    ambiguous = (
        '<hierarchy rotation="0"><node class="android.widget.FrameLayout" '
        'package="example.app" enabled="true" bounds="[0,0][1080,2400]">'
        + inner
        + inner
        + "</node></hierarchy>"
    )
    assert parsed_rows(ambiguous) == []


def test_current_native_provider_uses_one_bounded_dump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_dump(controller, timeout_sec):
        calls.append((controller, timeout_sec))
        return popup_xml()

    monkeypatch.setattr(adb_utils, "uiautomator_dump", fake_dump)
    controller = object()
    env = type("Env", (), {"controller": controller})()
    rows = current_native_popup_menu_ui_elements(
        env,
        screen_width=1080,
        screen_height=2400,
    )
    assert calls == [(controller, 10.0)]
    assert len(rows) == 5


def test_r72_accepts_recorded_r71_edit_on_exact_frozen_screenshot() -> None:
    client = EditClient()
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=GOAL)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.800"]
    guard.active_target_row_visit_key = "target-row-y:0.800"
    guard.requested_answer_role = "activity type"
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=guard,
        protocol_v2=True,
        protocol_v2_2=True,
    )

    decision, calls, meta = controller._call_and_parse(
        image_path=MENU_SCREENSHOT,
        page_semantic_sha256=(
            "e1c54259eae15772b668e316408b2501c2bd0d0ab95bf7ff7e993b50303cd089"
        ),
        destination_picker_is_active=False,
        ui_elements=[],
        requested_field_ui_elements=parsed_rows(),
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r72-r71-popup-replay",
        step=6,
        model_call_count=0,
    )

    assert len(calls) == 1
    assert len(client.requests) == 1
    assert decision["action"] == {"type": "tap", "x": 0.25, "y": 0.71}
    assert meta["first_pass"] is True
    assessment = meta["requested_field_value_assessment"]
    assert assessment["inspection_control_hit"] is True
    assert assessment["native_inspection_candidate_count"] == 1
    assert assessment["mutation_control_hit"] is False
    assert guard.target_row_non_control_tap_block_count == 0
