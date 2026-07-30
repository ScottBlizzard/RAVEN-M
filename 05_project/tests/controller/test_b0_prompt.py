from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController


ROOT = Path(__file__).resolve().parents[3]


def test_b0_prompt_excludes_hidden_state_and_memory() -> None:
    prompt = EpisodeController._user_prompt(
        goal="Create a contact.",
        step=0,
        max_steps=8,
        model_calls=0,
        max_model_calls=16,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="none",
    )
    assert "MEMORY_CONTEXT: []" in prompt
    assert "evaluator" not in prompt.lower()
    assert "package" not in prompt.lower()
    assert "activity" not in prompt.lower()
    assert "type_text may contain only a value explicitly requested" in prompt
    assert "1080x2400" in prompt
    assert "y=192 becomes y=0.0800" in prompt
    assert "a typical top-app-bar icon center" in prompt
    assert "y=438 becomes y=0.1826 and is in content" in prompt
    assert "do not use it for Search/menu icons" in prompt
    assert "ACTION_FIELD_CHECK" in prompt
    assert "long_press requires x, y, and duration_ms from 300-3000" in prompt
    assert "swipe requires x, y, x2, y2, and duration_ms" in prompt
    assert "FOCUSED_TEXT_INPUT_CHECK" in prompt
    assert "AndroidWorld clicks x,y before type_text" in prompt
    assert "preserve focus by omitting x and y" in prompt
    assert "using clear_text=false" in prompt
    assert "visible Save/Move/Done button is not proof" in prompt
    assert "schema named in the system prompt" in prompt
    assert "SEMANTIC_PROGRESS_CHECK" not in prompt


def test_v2_prompt_adds_semantic_progress_contract() -> None:
    prompt = EpisodeController._user_prompt(
        goal="Create a contact.",
        step=0,
        max_steps=8,
        model_calls=0,
        max_model_calls=16,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="none",
        protocol_v2=True,
    )
    assert "SEMANTIC_PROGRESS_CHECK" in prompt
    assert "status-bar clocks" in prompt
    assert "visible failure" in prompt


def test_v2_2_prompt_grounds_weekday_after_next_before_navigation() -> None:
    prompt = EpisodeController._user_prompt(
        goal="What events do I have the Wednesday after next?",
        step=0,
        max_steps=10,
        model_calls=0,
        max_model_calls=24,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="none",
        protocol_v2=True,
        protocol_v2_2=True,
    )
    assert "RELATIVE_DATE_GROUNDING" in prompt
    assert "first strictly future occurrence" in prompt
    assert "+7 and +14 days" in prompt
    assert "month grid or date picker" in prompt
    assert "one calendar row lower in the same weekday column" in prompt
    assert "verify the target day number before tapping" in prompt
    assert "selected date is closer to the computed target" in prompt
    assert "immediately reverse the swipe direction" in prompt
    assert "verify the visible absolute date" in prompt
    assert "FILES_SOURCE_NAVIGATION" in prompt
    assert "use the visible top-left roots/navigation-drawer" in prompt
    assert "Do not press_back to the launcher" in prompt


def test_v2_loop_guard_repair_requires_higher_level_selector() -> None:
    error = (
        "LOOP_GUARD: the same coordinate action has already been executed "
        "three consecutive times."
    )
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"status":"continue","action":{"type":"tap","x":0.93,"y":0.168}}',
        error,
        protocol_v2=True,
    )
    assert "higher level" in prompt
    assert "month grid, calendar control, or date picker" in prompt
    assert "swap its start and end points to reverse direction" in prompt
    assert "Do not evade the guard by perturbing the same coordinate" in prompt
    assert "use_higher_level_visible_selector" in prompt
    assert error in prompt
    assert prompt.index("LOOP_GUARD_REPAIR_PRIORITY") < prompt.index("original")


def test_v2_loop_guard_repair_breaks_blocked_open_app_cycle() -> None:
    error = (
        "LOOP_GUARD: this action is blocked on the current semantic UI "
        "state after no progress."
    )
    prompt = EpisodeController._repair_prompt(
        "original",
        (
            '{"status":"continue","action":'
            '{"type":"open_app","app_name":"Files"}}'
        ),
        error,
        protocol_v2=True,
    )
    assert "BLOCKED_OPEN_APP_CYCLE" in prompt
    assert "action.type must not be open_app or press_back" in prompt
    assert "swipe upward from lower launcher content" in prompt
    assert "reveal the app drawer" in prompt
    assert "Do not guess a hidden icon coordinate" in prompt
    assert prompt.index("BLOCKED_OPEN_APP_CYCLE") < prompt.rindex("original")


def test_repair_prompt_forbids_invented_working_memory_citations() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"memory_citations":["working_memory_0"]}',
        "memory_citations.0 does not match pattern",
    )
    assert "MEMORY_CONTEXT.items[].memory_id" in prompt
    assert "Working-memory slots are not citable" in prompt
    assert "use []" in prompt
    assert "do not repeat done" in prompt
    assert "supports_completion_requirements" in prompt


def test_v2_repair_prompt_spells_out_canonical_open_and_swipe() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"action":"open_app","action_details":{"app":"Contacts"}}',
        "invalid",
        protocol_v2=True,
    )
    assert '{"type":"open_app","app_name":"Contacts"}' in prompt
    assert '"x2":0.5' in prompt
    assert "Never use action_details, action_args, direction, or distance" in prompt


def test_v2_semantic_action_repair_requires_a_different_action() -> None:
    error = (
        'EXACT_TARGET_GUARD: The exact task-literal filename '
        '"nature_sounds.mp3" is not visible; the proposed coordinate is '
        'nearest to "nature_sounds_2023_02_11.mp3".'
    )
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"action":{"type":"long_press","x":0.75,"y":0.75}}',
        error,
        protocol_v2=True,
    )
    assert "GUI action was semantically rejected" in prompt
    assert "choose a materially different action" in prompt
    assert "Do not repeat the same action type with the same coordinates" in prompt
    assert "using Search, scrolling, changing view" in prompt
    assert 'action.type must not be "long_press"' in prompt
    assert "Do not infer or try another file coordinate" in prompt
    assert "only on a later policy step" in prompt
    assert "y in 0.06-0.10" in prompt
    assert "y around 0.18 is content" in prompt
    assert "a later type_text must omit x and y" in prompt
    assert "the extra click cannot destroy focus" in prompt
    assert "Correct its format only" not in prompt
    assert error in prompt


def test_v2_structural_repair_retains_format_only_directive() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"action":"tap"}',
        "$.action is not of type object",
        protocol_v2=True,
    )
    assert "Correct its format only" in prompt
    assert "GUI action was semantically rejected" not in prompt


def test_v2_repair_prompt_spells_out_canonical_state_delta() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"state_delta":[{"current_page":"calendar"}]}',
        "state_delta.0: 'kind' is a required property",
        protocol_v2=True,
    )
    assert '"kind":"fact"' in prompt
    assert '"subject":"page"' in prompt
    assert '"predicate":"identity"' in prompt
    assert '"natural_language":' in prompt
    assert '"evidence":"direct_screen"' in prompt
    assert "Never use free-form key/value state objects" in prompt
    assert "If the system prompt requires an empty state_delta, use []" in prompt


def test_v2_swipe_direction_repair_is_geometry_specific() -> None:
    prompt = EpisodeController._repair_prompt(
        "ORIGINAL",
        (
            '{"status":"continue","action":{"type":"swipe","x":0.5,'
            '"y":0.34,"x2":0.5,"y2":0.15,"duration_ms":500},'
            '"expected_outcome":"More categories appear.",'
            '"decision_summary":"Swipe left to reveal more categories.",'
            '"state_delta":[],"memory_citations":[]}'
        ),
        (
            "SWIPE_DIRECTION_GUARD: decision_summary declares 'left', but "
            "the canonical coordinate geometry is 'up' (vertical_dominant)."
        ),
        protocol_v2=True,
    )
    assert "sentence and numeric coordinates declared different directions" in prompt
    assert "left requires x2<x" in prompt
    assert "right x2>x" in prompt
    assert "up y2<y" in prompt
    assert "down y2>y" in prompt


def test_v2_focused_empty_tap_repair_enters_task_value_directly() -> None:
    prompt = EpisodeController._repair_prompt(
        "ORIGINAL",
        (
            '{"status":"continue","action":{"type":"tap","x":0.5,'
            '"y":0.18},"expected_outcome":"The field is focused.",'
            '"decision_summary":"Tap the field again.",'
            '"state_delta":[],"memory_citations":[]}'
        ),
        (
            "FOCUSED_EMPTY_TAP_GUARD: the proposed tap hits an "
            "already-focused empty editable control."
        ),
        protocol_v2=True,
    )
    assert "already visibly focused and empty" in prompt
    assert "action.type=type_text" in prompt
    assert "no x or y" in prompt
    assert "clear_text=false" in prompt


def test_v2_unverified_progress_repair_uses_visible_layout_axis() -> None:
    prompt = EpisodeController._repair_prompt(
        "ORIGINAL",
        (
            '{"status":"continue","action":{"type":"tap","x":0.5,'
            '"y":0.34},"expected_outcome":"Options open.",'
            '"decision_summary":"Tap the same control.",'
            '"state_delta":[],"memory_citations":[]}'
        ),
        (
            "LOOP_GUARD: UNVERIFIED_PROGRESS_REPEAT_REQUIRED: the "
            "immediately preceding identical action produced no semantic "
            "UI change."
        ),
        protocol_v2=True,
    )
    assert "Discard the unconfirmed popup/page assumption" in prompt
    assert "side by side in a horizontal row or carousel" in prompt
    assert "change x while keeping y approximately fixed" in prompt
    assert "stacked in a vertical list" in prompt


def test_v2_repair_prompt_has_complete_status_action_matrix() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"status":"done","action":{"type":"answer","text":"value"}}',
        "answer is permitted only for an information-return goal.",
        protocol_v2=True,
    )
    assert "completed ordinary GUI task use status=done and action=null" in prompt
    assert "Only a completed information-return task" in prompt
    assert "Creating, editing, moving, deleting, saving, or sending" in prompt
    assert "remove the answer action and use action=null" in prompt
    assert "never repeat the forbidden answer" in prompt
    assert "continue and fail use []" in prompt
    assert '"claim":"The requested result is complete."' in prompt


def test_v2_repair_prompt_requires_all_top_level_fields_in_one_repair() -> None:
    prompt = EpisodeController._repair_prompt(
        "original",
        '{"status":"done","action":null}',
        "$: 'expected_outcome' is required; "
        "$: 'memory_citations' is required",
        protocol_v2=True,
    )
    for field in (
        "status",
        "action",
        "expected_outcome",
        "decision_summary",
        "state_delta",
        "memory_citations",
        "completion_evidence",
    ):
        assert field in prompt
    assert "Fix every missing required property" in prompt
    assert "do not fix only the first" in prompt
    assert '"expected_outcome":"The screen stabilizes."' in prompt


def test_v2_system_prompts_distinguish_ordinary_and_answer_completion() -> None:
    for filename in ("executor_v2.md", "executor_raven_v2.md"):
        prompt = (ROOT / "05_project/prompts" / filename).read_text(
            encoding="utf-8"
        )
        normalized = " ".join(prompt.split())
        assert "unfinished task: status=continue" in normalized
        assert (
            "completed ordinary GUI task: status=done with action=null"
            in normalized
        )
        assert "completed information-return task only" in normalized
        assert "infeasible task: status=fail with action=null" in normalized
        assert (
            "Creating, editing, moving, deleting, saving, or sending"
            in normalized
        )
        assert "Never use answer for such a task" in normalized
        assert "Never omit expected_outcome" in normalized
        assert '"memory_citations":[]' in normalized
        if filename == "executor_raven_v2.md":
            assert '"completion_evidence":[]' in normalized
