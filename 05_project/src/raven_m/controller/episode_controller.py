"""Thin, memory-free B0 observe-act-evaluate controller."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict, is_dataclass
from enum import Enum
from hashlib import sha256
import html
import json
from pathlib import Path
import time
import traceback
from typing import Any

from PIL import Image

from raven_m.actions.schema import ActionValidationError, parse_action_response
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    coordinate_type_text_target_assessment,
    declared_text_source_assessment,
    destination_picker_active,
    destination_picker_commit_action,
    destination_picker_empty_stall_assessment,
    destination_picker_navigation_drawer_action,
    exact_selection_long_press_assessment,
    files_roots_drawer_action_assessment,
    focused_editable_input_assessment,
    post_destination_transfer_command_action,
    semantic_ui_snapshot,
    soft_keyboard_swipe_assessment,
    task_literal_field_role_assessment,
)
from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.history.policies import (
    HistoryEntry,
    HistoryPolicy,
)
from raven_m.models.transformers_client import ModelCall, TransformersClient
from raven_m.roles.orchestrator import RoleOrchestrator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json_safe(value: Any) -> Any:
    """Convert AndroidWorld parameter objects into stable JSON values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Image.Image):
        return {
            "__type__": "PIL.Image.Image",
            "mode": value.mode,
            "size": list(value.size),
            "pixel_sha256": sha256(value.tobytes()).hexdigest(),
        }
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "_asdict"):
        return _json_safe(value._asdict())
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return repr(value)


def action_authority_record(
    decision: dict[str, Any],
    *,
    completion_adjudications: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive a conservative, auditable action-risk/authority record."""
    action = decision.get("action")
    action_type = action.get("type") if isinstance(action, dict) else None
    if decision.get("status") != "continue":
        risk_class = "terminal_answer_or_completion"
    elif action_type in {"swipe", "press_back", "press_home", "open_app", "wait"}:
        risk_class = "observe_navigation"
    elif action_type == "type_text":
        risk_class = "reversible_edit"
    else:
        # A tap, long press, or Enter may activate Save/Delete/Send. Treat it
        # conservatively as a possible commit rather than guessing from pixels.
        risk_class = "irreversible_commit"
    citations = list(decision.get("memory_citations", []))
    sources = ["current_screen"]
    if citations:
        sources.append("routed_memory")
    adjudications = completion_adjudications or []
    if any(item.get("output") is not None for item in adjudications):
        sources.append("same_turn_critic")
    return {
        "schema_version": "action_authority.v2",
        "risk_class": risk_class,
        "authority_sources": sources,
        "memory_citations": citations,
        "text_origin": (
            action.get("text_origin") if isinstance(action, dict) else None
        ),
        "source_memory_ids": (
            list(action.get("source_memory_ids", []))
            if isinstance(action, dict)
            else []
        ),
        "same_turn_adjudication_count": len(adjudications),
    }


class EpisodeLogger:
    def __init__(self, episode_dir: Path) -> None:
        self.episode_dir = episode_dir
        self.episode_dir.mkdir(parents=True, exist_ok=False)
        self.events_path = self.episode_dir / "events.jsonl"

    def append(self, event: dict[str, Any]) -> None:
        record = {"time": _utc_now(), **event}
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )
            stream.flush()

    def save_screenshot(self, pixels: Any, name: str) -> Path:
        path = self.episode_dir / name
        Image.fromarray(pixels).save(path)
        return path


class ModelOutputInvalid(RuntimeError):
    """Carries both model calls when one repair still fails validation."""

    def __init__(
        self,
        *,
        calls: list[ModelCall],
        initial_error: str,
        repair_error: str,
        adjudication_model_call_count: int = 0,
        action_adjudications: list[dict[str, Any]] | None = None,
        completion_adjudications: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(repair_error)
        self.calls = calls
        self.initial_error = initial_error
        self.repair_error = repair_error
        self.adjudication_model_call_count = adjudication_model_call_count
        self.action_adjudications = action_adjudications or []
        self.completion_adjudications = completion_adjudications or []


class VisibleInfrastructureFailure(RuntimeError):
    """A visible OS/app failure that must be retried outside the policy."""

    def __init__(self, messages: list[str]) -> None:
        rendered = " | ".join(messages)
        super().__init__(f"INFRA_EMULATOR_ANR: {rendered}")
        self.messages = tuple(messages)


def classify_failure_code(
    *,
    error_record: dict[str, Any] | None,
    model_output_error: dict[str, Any] | None,
    evaluator_reward: float | None,
    termination_reason: str,
) -> str | None:
    if error_record:
        return "INFRA_OR_CONTROLLER"
    # The native evaluator is authoritative. A formatting failure remains in
    # model_output_error and the validity-rate fields, but a successful task
    # must not also carry a contradictory failure-code label.
    if evaluator_reward == 1.0:
        return None
    if model_output_error:
        return "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    if termination_reason == "model_done":
        return "PREMATURE_COMPLETION"
    if termination_reason == "model_answer":
        return "INCORRECT_ANSWER"
    if termination_reason == "model_fail":
        return "MODEL_DECLARED_INFEASIBLE"
    if termination_reason == "model_call_budget_exhausted":
        return "MODEL_CALL_BUDGET_EXHAUSTED"
    return "TASK_UNSUCCESSFUL_AT_BUDGET"


class EpisodeController:
    """Runs one non-scored B0 episode without memory or evaluator leakage."""

    def __init__(
        self,
        *,
        client: TransformersClient,
        system_prompt: str,
        max_steps: int = 8,
        max_model_calls: int = 16,
        adapter: AndroidWorldAdapter | None = None,
        history_policy: HistoryPolicy | None = None,
        action_schema_path: Path | None = None,
        decision_guard: ProtocolV2DecisionGuard | None = None,
        protocol_v2: bool = False,
        protocol_v2_2: bool = False,
        visual_source_critic_prompt: str = "",
        readiness_max_observations: int = 12,
        readiness_retry_delay_seconds: float = 0.75,
        readiness_reconnect_after_observations: int = 3,
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls
        self.adapter = adapter or AndroidWorldAdapter()
        self.history_policy = history_policy or HistoryPolicy()
        self.action_schema_path = action_schema_path
        self.decision_guard = decision_guard
        self.protocol_v2 = protocol_v2
        self.protocol_v2_2 = protocol_v2_2
        self.visual_source_roles = (
            RoleOrchestrator(
                client=client,
                planner_prompt="",
                critic_prompt=visual_source_critic_prompt,
            )
            if protocol_v2_2 and visual_source_critic_prompt
            else None
        )
        self.readiness_max_observations = max(1, readiness_max_observations)
        self.readiness_retry_delay_seconds = max(
            0.0, readiness_retry_delay_seconds
        )
        self.readiness_reconnect_after_observations = max(
            1, readiness_reconnect_after_observations
        )

    def _observe_state(
        self,
        env: Any,
        *,
        require_accessibility: bool,
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Observe without spending a policy step until an opened app is ready."""
        maximum = (
            self.readiness_max_observations
            if self.protocol_v2_2 and require_accessibility
            else 1
        )
        observations: list[dict[str, Any]] = []
        state = None
        accessibility_recovery_attempted = False
        for attempt in range(1, maximum + 1):
            state = env.get_state(wait_to_stabilize=True)
            raw_pixel_sha = sha256(state.pixels.tobytes()).hexdigest()
            semantic = (
                semantic_ui_snapshot(
                    getattr(state, "ui_elements", ()),
                    fallback_sha256=raw_pixel_sha,
                )
                if self.protocol_v2
                else {
                    "source": "protocol_v1_screenshot",
                    "element_count": 0,
                    "visible_failure_texts": [],
                    "infrastructure_failure_texts": [],
                }
            )
            observation = {
                "attempt": attempt,
                "source": semantic["source"],
                "element_count": int(semantic["element_count"]),
                "foreground_package": self._foreground_package(env),
                "accessibility_packages": self._accessibility_packages(state),
                "matches_foreground": (
                    self._accessibility_matches_foreground(
                        env,
                        state,
                        semantic,
                    )
                ),
                "infrastructure_failure_texts": list(
                    semantic.get("infrastructure_failure_texts", [])
                ),
                "accessibility_recovery_attempted": False,
                "accessibility_recovery_error": None,
            }
            observations.append(observation)
            if semantic.get("infrastructure_failure_texts"):
                break
            if not require_accessibility or (
                semantic["source"] == "accessibility"
                and self._accessibility_matches_foreground(
                    env,
                    state,
                    semantic,
                )
            ):
                break
            if (
                self.protocol_v2_2
                and require_accessibility
                and not accessibility_recovery_attempted
                and attempt >= self.readiness_reconnect_after_observations
                and attempt < maximum
            ):
                refresh = getattr(
                    getattr(env, "controller", None),
                    "refresh_env",
                    None,
                )
                if callable(refresh):
                    observation["accessibility_recovery_attempted"] = True
                    accessibility_recovery_attempted = True
                    try:
                        refresh()
                    except Exception as exc:  # pragma: no cover - runtime only
                        observation["accessibility_recovery_error"] = (
                            f"{type(exc).__name__}: {exc}"
                        )
            if attempt < maximum and self.readiness_retry_delay_seconds:
                time.sleep(self.readiness_retry_delay_seconds)
        assert state is not None
        return state, observations

    @staticmethod
    def _foreground_package(env: Any) -> str | None:
        activity = getattr(env, "foreground_activity_name", None)
        if not isinstance(activity, str) or not activity:
            return None
        return activity.split("/", 1)[0]

    @staticmethod
    def _accessibility_packages(state: Any) -> list[str]:
        packages = set()
        for element in getattr(state, "ui_elements", ()):
            package = (
                element.get("package_name")
                if isinstance(element, dict)
                else getattr(element, "package_name", None)
            )
            if package:
                packages.add(str(package))
        return sorted(packages)

    @classmethod
    def _accessibility_matches_foreground(
        cls,
        env: Any,
        state: Any,
        semantic: dict[str, Any],
    ) -> bool:
        if semantic["source"] != "accessibility":
            return False
        foreground_package = cls._foreground_package(env)
        if foreground_package is None:
            # Test doubles and non-Android adapters may not expose an
            # activity name. Accessibility itself remains the best signal.
            return True
        return foreground_package in cls._accessibility_packages(state)

    @staticmethod
    def _user_prompt(
        *,
        goal: str,
        step: int,
        max_steps: int,
        model_calls: int,
        max_model_calls: int,
        screen_width: int,
        screen_height: int,
        previous_outcome: str,
        memory_context: str = "[]",
        protocol_v2: bool = False,
        protocol_v2_2: bool = False,
        post_destination_commit_active: bool = False,
    ) -> str:
        coordinate_denominator = max(screen_height - 1, 1)
        app_bar_pixel_y = min(
            round(0.08 * coordinate_denominator),
            screen_height - 1,
        )
        app_bar_normalized_y = (
            app_bar_pixel_y / coordinate_denominator
        )
        content_pixel_y = min(438, screen_height - 1)
        content_normalized_y = content_pixel_y / coordinate_denominator
        return "\n".join(
            [
                f"TASK: {goal}",
                f"STEP/BUDGET: {step + 1}/{max_steps}; "
                f"model calls {model_calls}/{max_model_calls}",
                f"PREVIOUS_ACTION_AND_OBSERVED_OUTCOME: {previous_outcome}",
                f"MEMORY_CONTEXT: {memory_context}",
                (
                    "TEXT_PROVENANCE: type_text/answer text must come from a "
                    "TASK literal, the current screen, verified routed memory, "
                    "or a deterministic calculation; declare text_origin and "
                    "source_memory_ids exactly as required by the schema. A "
                    "task_literal value must occur in TASK, and a "
                    "current_screen value must occur in the visible current "
                    "UI; do not invent optional field values or relabel them."
                    " A coordinate-bearing task literal must target a visible "
                    "editable field whose label matches the value's role; "
                    "Search/Filter/Query fields may accept task queries."
                    if protocol_v2
                    else
                    "TEXT_SAFETY: type_text may contain only a value explicitly "
                    "requested by TASK."
                ),
                f"CURRENT_SCREENSHOT: attached image; size "
                f"{screen_width}x{screen_height} pixels.",
                "COORDINATE_CHECK: JSON coordinates must be normalized decimals "
                "in [0,1], never pixels. For this image, pixel "
                f"y={app_bar_pixel_y} becomes "
                f"y={app_bar_normalized_y:.4f}, a typical top-app-bar icon "
                f"center. Pixel y={content_pixel_y} becomes "
                f"y={content_normalized_y:.4f} and is in content, not the "
                "top app bar; do not use it for Search/menu icons.",
                "ACTION_FIELD_CHECK: long_press requires x, y, and duration_ms "
                "from 300-3000; swipe requires x, y, x2, y2, and duration_ms; "
                "wait requires duration_ms. Do not omit required action fields.",
                "FOCUSED_TEXT_INPUT_CHECK: AndroidWorld clicks x,y before "
                "type_text. If an empty text field already visibly has a caret, "
                "preserve focus by omitting x and y and using clear_text=false. "
                "Supply x,y only when a visible field is not already focused.",
                "COMPLETION_CHECK: a visible Save/Move/Done button is not proof "
                "of completion; execute it and observe the result first.",
                *(
                    [
                        "SEMANTIC_PROGRESS_CHECK: status-bar clocks, toast "
                        "animation, and other transient pixels are not task "
                        "progress. If the previous outcome says the semantic "
                        "UI did not change or reports a visible failure, do "
                        "not repeat the same action; change the invalid input "
                        "or use a named recovery class."
                    ]
                    if protocol_v2
                    else []
                ),
                *(
                    [
                        "PLANNER_CONSISTENCY: when MEMORY_CONTEXT contains "
                        "planner_state, its current_subgoal and "
                        "required_variables are frozen anchors. Do not "
                        "re-resolve a relative date or replace a target "
                        "because the UI has navigated; recover toward the "
                        "anchored target. A reobserve/recover critic "
                        "constraint is binding until a materially different "
                        "action changes the semantic state."
                    ]
                    if protocol_v2_2
                    else []
                ),
                *(
                    [
                        "RELATIVE_DATE_GROUNDING: resolve relative calendar "
                        "language from the TASK and the visible reference date "
                        "before selecting a day. The next named weekday is its "
                        "first strictly future occurrence; that weekday after "
                        "next is the following occurrence. When today already "
                        "has that weekday, these are +7 and +14 days. Prefer a "
                        "visible month grid or date picker that selects the "
                        "computed date directly instead of repeated next-day "
                        "arrows. In a month grid, locate the first future named "
                        "weekday, then move exactly one calendar row lower in "
                        "the same weekday column for 'weekday after next'; "
                        "verify the target day number before tapping. In a "
                        "date wheel, a swipe is progress only if the next "
                        "visible selected date is closer to the computed "
                        "target. If it moved farther away, immediately reverse "
                        "the swipe direction and never repeat the worsening "
                        "motion. Before answering, verify the visible absolute "
                        "date; do not answer from the first matching weekday."
                    ]
                    if protocol_v2_2
                    else []
                ),
                *(
                    [
                        "POST_DESTINATION_COMMIT_ACTIVE: exactly one bottom "
                        "Copy/Move commit has already executed in this task. "
                        "Do not select or long-press the task item, open an "
                        "overflow menu for Move/Copy, initiate another transfer, "
                        "or wait on an unchanged stale source/search view. Use "
                        "only reversible navigation to inspect the requested "
                        "destination, or return terminal status only when the "
                        "current screen and allowed completion evidence support "
                        "it. A stale source/search screen is unverified state, "
                        "not authority to repeat the mutation."
                    ]
                    if protocol_v2_2 and post_destination_commit_active
                    else []
                ),
                "LENGTH_CHECK: expected_outcome and decision_summary must each "
                "be one short sentence under 160 characters.",
                "Return one JSON object matching the action schema named in "
                "the system prompt now.",
            ]
        )

    @staticmethod
    def _repair_prompt(
        original_prompt: str,
        invalid_content: str,
        error: str,
        protocol_v2: bool = False,
    ) -> str:
        semantic_action_error_prefixes = (
            "EXACT_TARGET_GUARD:",
            "FOCUSED_INPUT_GUARD:",
            "UNFOCUSED_CLEAR_TEXT_GUARD:",
            "TEXT_TARGET_GUARD:",
            "DECLARED_TEXT_SOURCE_GUARD:",
            "FIELD_VALUE_BINDING_GUARD:",
            "POST_DESTINATION_COMMIT_GUARD:",
            "DESTINATION_PICKER_GUARD:",
            "FILES_ROOTS_DRAWER_GUARD:",
            "SOFT_KEYBOARD_SWIPE_GUARD:",
            "LOOP_GUARD:",
            "CRITIC_CONSTRAINT:",
            "Same-turn action adjudication rejected",
        )
        semantic_action_rejected = error.startswith(
            semantic_action_error_prefixes
        )
        exact_target_rejected = error.startswith("EXACT_TARGET_GUARD:")
        focused_input_rejected = error.startswith("FOCUSED_INPUT_GUARD:")
        unfocused_clear_text_rejected = error.startswith(
            "UNFOCUSED_CLEAR_TEXT_GUARD:"
        )
        text_target_rejected = error.startswith("TEXT_TARGET_GUARD:")
        declared_source_rejected = error.startswith(
            "DECLARED_TEXT_SOURCE_GUARD:"
        )
        field_value_rejected = error.startswith(
            "FIELD_VALUE_BINDING_GUARD:"
        )
        keyboard_dismiss_required = (
            "SOFT_KEYBOARD_DISMISS_REQUIRED:" in error
        )
        keyboard_swipe_forbidden = (
            "SOFT_KEYBOARD_SWIPE_FORBIDDEN:" in error
        )
        empty_picker_stall_required = (
            "DESTINATION_PICKER_EMPTY_STALL_REQUIRED:" in error
        )
        destination_picker_renavigation_required = (
            "DESTINATION_PICKER_RENAVIGATION_REQUIRED:" in error
        )
        files_roots_drawer_selection_required = (
            "FILES_ROOTS_DRAWER_SELECTION_REQUIRED:" in error
        )
        post_destination_commit_rejected = error.startswith(
            "POST_DESTINATION_COMMIT_GUARD:"
        )
        loop_guard_rejected = error.startswith("LOOP_GUARD:")
        visual_source_rejected = (
            "VISUAL_SOURCE_ADJUDICATION_REJECTED:" in error
        )
        if visual_source_rejected:
            repair_directive = (
                "\n\nThe bounded visual-source critic did not verify the "
                "terminal answer on this unchanged screenshot. For this one "
                "repair, return status=continue with exactly one reversible "
                "GUI action that opens the relevant visible detail or obtains "
                "a materially clearer view of the task-bound text. Do not "
                "return an answer, do not repeat the candidate, do not change "
                "text_origin, and do not commit any mutation. Use only a "
                "control visibly supported by the current screenshot.\n"
            )
        elif post_destination_commit_rejected:
            repair_directive = (
                "\n\nA bottom Copy/Move commit already executed once, so the "
                "proposed action would start or submit a second transaction. "
                "For this one repair, return status=continue with action "
                'exactly {"type":"press_back"} to dismiss the current overflow '
                "menu, selection mode, or unintended second destination "
                "picker. Do not tap, wait, swipe, type, select an item, commit, "
                "or declare success on this unchanged screenshot. Observe the "
                "next screen before using reversible navigation to verify the "
                "requested destination.\n"
            )
        elif destination_picker_renavigation_required:
            repair_directive = (
                "\n\nThe consequential-action critic rejected a Copy/Move "
                "commit while the Android destination picker is still active "
                "in the wrong or unverified directory. For this one repair, "
                "return status=continue and action.type=tap, targeting only "
                "the visible enabled top-left Show roots/navigation-drawer "
                "control. Do not tap Copy/Move or Cancel, do not press_back, "
                "wait, swipe, type, or guess a content-area coordinate. The "
                "next policy step may choose the requested destination after "
                "observing the roots drawer.\n"
            )
        elif files_roots_drawer_selection_required:
            repair_directive = (
                "\n\nThe Android Files roots drawer is already open and "
                "contains visible enabled category/storage rows. For this "
                "one repair, return status=continue and action.type=tap, "
                "targeting one visible enabled drawer row that advances "
                "toward the TASK storage or category. Do not tap the title "
                "or menu area, wait, swipe, press_back, type, close/reopen "
                "the drawer, or guess outside a visible row. No coordinate "
                "is supplied; bind the tap only from this unchanged "
                "screenshot.\n"
            )
        elif empty_picker_stall_required:
            repair_directive = (
                "\n\nYour previous JSON would stall in a fully rendered "
                "empty destination directory. For this one repair, "
                "action.type must be tap. If the visible current directory "
                "is the requested TASK destination, tap the visible bottom "
                "Copy/Move control; otherwise tap the visible top-left "
                "navigation drawer. Do not wait, swipe, press_back, type, "
                "or guess a content-area coordinate. Use only a control "
                "visibly supported by the unchanged screenshot.\n"
            )
        elif keyboard_dismiss_required:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid, but the soft "
                "keyboard is visible and the focused field must not be "
                "modified. For this one repair, return status=continue with "
                'action exactly {"type":"press_back"} to dismiss only the '
                "soft keyboard. Do not swipe, type, tap, save, or change any "
                "task value on this unchanged screenshot. Observe the next "
                "screen before choosing the role-matched field.\n"
            )
        elif field_value_rejected:
            repair_directive = (
                "\n\nYour previous JSON used a requested task value but "
                "targeted an editable field with a conflicting role. Keep "
                "action.type=type_text, the exact same text, text_origin, and "
                "source_memory_ids. Choose the visible editable field whose "
                "label matches the value's task role. Do not fill an "
                "unrelated optional field and do not invent a coordinate "
                "that is not visibly supported.\n"
            )
            if keyboard_swipe_forbidden:
                repair_directive += (
                    "SOFT_KEYBOARD_FIELD_REPAIR_CONTRACT: The soft keyboard "
                    "is visible, so action.type must not be swipe. If the "
                    "role-matched editable field is visibly supported, enter "
                    "the same requested value there directly. Otherwise "
                    'return action exactly {"type":"press_back"} to dismiss '
                    "only the keyboard and observe the next screen before "
                    "typing.\n"
                )
        elif declared_source_rejected:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid, but its "
                "declared text source did not contain the proposed text. Do "
                "not merely change text_origin and do not invent an optional "
                "field value. A task_literal value must occur in TASK; a "
                "current_screen value must occur in the visible current UI. "
                "If a visible empty editable field corresponds to a remaining "
                "TASK value, fill that requested value in its matching field "
                "now. Otherwise choose one non-commit action that leaves the "
                "unspecified field untouched. Do not repeat a navigation "
                "action that has already produced no semantic progress.\n"
            )
        elif focused_input_rejected:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid, but its "
                "type_text action would destroy an already-active input. "
                "Keep action.type=type_text, the exact same text, text_origin, "
                "and source_memory_ids. Remove x and y. If VALIDATION_ERROR "
                "says the target input is empty, set clear_text=false. Do not "
                "tap, navigate, change the text, or add a coordinate.\n"
            )
        elif unfocused_clear_text_rejected:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid and its "
                "coordinate matched a visible editable control, but input "
                "was not visibly active. For this one repair, action.type "
                "must not be type_text. Tap that same visibly supported input "
                "control without committing any task mutation, then observe "
                "the resulting screen on a later policy step. Type only "
                "after a focused editable or the soft keyboard is visible; "
                "then omit x,y and use clear_text=false when the field is "
                "empty. Do not send Ctrl+A to an unfocused screen.\n"
            )
        elif text_target_rejected:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid, but its "
                "type_text coordinate was not bound to a visible editable "
                "control. For this one repair, action.type must not be "
                "type_text. Use a reversible tap or navigation action to "
                "activate or reopen a visible input control, then observe "
                "the resulting screen on a later policy step before typing. "
                "Do not guess another text coordinate or commit any task "
                "mutation.\n"
            )
        elif loop_guard_rejected:
            repair_directive = (
                "\n\nLOOP_GUARD_REPAIR_PRIORITY: Your previous JSON repeated "
                "a blocked action on this "
                "screenshot. For this one repair, use a materially different "
                "visible control that can reach the target at a higher level "
                "instead of continuing stepwise repetition. For calendar/date "
                "navigation, prefer the visible month grid, calendar control, "
                "or date picker and bind the exact computed date. If the "
                "blocked action is a swipe whose observed values moved away "
                "from the target, swap its start and end points to reverse "
                "direction. Do not evade the guard by perturbing the same "
                "coordinate, and do not repeat the same arrow, swipe, or "
                "target. This priority contract appears before the original "
                "prompt and is binding.\n"
            )
        elif semantic_action_rejected:
            repair_directive = (
                "\n\nYour previous JSON was structurally valid, but its GUI "
                "action was semantically rejected on this screenshot. Keep "
                "the required JSON schema and choose a materially different "
                "action. Do not repeat the same action type with the same "
                "coordinates. Follow VALIDATION_ERROR even when that means "
                "using Search, scrolling, changing view, or another "
                "non-commit navigation action.\n"
            )
            if exact_target_rejected:
                repair_directive += (
                    "EXACT_TARGET_REPAIR_CONTRACT: For this one repair, "
                    'action.type must not be "long_press". Do not infer or '
                    "try another file coordinate on the unchanged screen. "
                    "Return status=continue with a non-long-press "
                    "information-gathering action; prefer the visible Search "
                    "control, a view-mode change, or scrolling. Selection may "
                    "be attempted only on a later policy step after the new "
                    "screen is observed. For a visible magnifying-glass Search "
                    "icon in a portrait top app bar, target its icon center "
                    "with y in 0.06-0.10; y around 0.18 is content and must "
                    "not be used for that app-bar control. After Search opens, "
                    "if its empty field visibly has a caret, a later type_text "
                    "must omit x and y and use clear_text=false so the extra "
                    "click cannot destroy focus.\n"
                )
        else:
            repair_directive = (
                "\n\nYour previous response was invalid. Correct its format "
                "only while choosing the action from the same screenshot.\n"
            )
        v2_contract = (
            "\nPROTOCOL_V2_ACTION_CONTRACT: The action field is the object "
            "itself. open_app is "
            '{"type":"open_app","app_name":"Contacts"}. swipe is '
            '{"type":"swipe","x":0.5,"y":0.8,"x2":0.5,"y2":0.2,'
            '"duration_ms":500}. Never use action_details, action_args, '
            "direction, or distance. type_text and answer require "
            "text_origin and source_memory_ids. If the system prompt permits "
            "a non-empty state_delta, every entry must look like "
            '{"kind":"fact","subject":"page","predicate":"identity",'
            '"object":"calendar month view","natural_language":'
            '"The calendar month view is visible.","evidence":'
            '"direct_screen","confidence":0.98}. Never use free-form '
            "key/value state objects. If the system prompt requires an empty "
            "state_delta, use [].\n"
            "PROTOCOL_V2_STATUS_MATRIX: For an unfinished task use "
            "status=continue with one GUI action. For a completed ordinary "
            "GUI task use status=done and action=null. Only a completed "
            "information-return task may use status=done with an answer "
            "object. For an infeasible task use status=fail and action=null. "
            "Creating, editing, moving, deleting, saving, or sending is an "
            "ordinary GUI task, not an information-return task. If "
            "VALIDATION_ERROR says answer is permitted only for an "
            "information-return goal, remove the answer action and use "
            "action=null; never repeat the forbidden answer. For a schema "
            "that requires completion_evidence: continue and fail use [], "
            "while done uses one or more exact "
            '{"claim":"The requested result is complete.",'
            '"evidence":"direct_screen","memory_ids":[]} objects.\n'
            "PROTOCOL_V2_REQUIRED_FIELDS: Every response must include "
            "status, action, expected_outcome, decision_summary, "
            "state_delta, and memory_citations. If the system prompt names "
            "completion_evidence, include it too. Fix every missing required "
            "property listed in VALIDATION_ERROR in this one repair; do not "
            "fix only the first. Use this complete M0-shaped top-level "
            "skeleton when completion_evidence is required: "
            '{"status":"continue","action":{"type":"wait",'
            '"duration_ms":1000},"expected_outcome":"The screen '
            'stabilizes.","decision_summary":"Wait for the visible page to '
            'stabilize.","state_delta":[],"memory_citations":[],'
            '"completion_evidence":[]}.\n'
            if protocol_v2
            else ""
        )
        repair_prefix = repair_directive if loop_guard_rejected else ""
        repair_suffix = "" if loop_guard_rejected else repair_directive
        return (
            repair_prefix
            + original_prompt
            + repair_suffix
            + f"VALIDATION_ERROR: {error}\n"
            f"INVALID_RESPONSE: {invalid_content}\n"
            "The action field must be an object such as "
            '{"type":"tap","x":0.5,"y":0.5}, never an action name plus '
            "action_args/action_details. state_delta must be an array of "
            "at most two structured objects matching the system-prompt "
            "example, or []. For status=done/fail it must be [].\n"
            "memory_citations may contain only exact IDs copied from "
            "MEMORY_CONTEXT.items[].memory_id. Working-memory slots are not "
            "citable. If an ID is unavailable, malformed, or invented, "
            "remove it and use [] when no valid item remains.\n"
            "If VALIDATION_ERROR says completion requires a routed FACT, do "
            "not repeat done. Return status=continue with a 1000 ms wait and "
            "one direct_screen fact linked through "
            "supports_completion_requirements; cite it only on a later "
            "observation if it is then routed as FACT.\n"
            "If VALIDATION_ERROR says the completion critic rejected an "
            "answer, do not repeat the partial answer. Open the relevant "
            "detail view or obtain a second view where the exact full text "
            "is readable without clipping, then answer on a later step.\n"
            "If VALIDATION_ERROR says the action critic rejected a commit, "
            "do not repeat that action. Use a non-commit navigation or "
            "re-observation action until the exact task target and selected "
            "destination/value are visibly bound on the current screen.\n"
            "For protocol-v2 text actions, preserve valid text_origin and "
            "source_memory_ids provenance. An answer action is terminal and "
                "only valid for information-return tasks. If LOOP_GUARD appears, "
                "use one named recovery class: change_target, "
                "reverse_scroll_direction, navigate_back, reopen_app, "
                "inspect_different_visible_control, "
                "use_higher_level_visible_selector, or fail_safely.\n"
            + v2_contract
            + "If a coordinate is above 1, convert it from pixels using "
            "CURRENT_SCREENSHOT size. If text is too long, shorten it below "
            "160 characters. status must be continue/done/fail; wait is an "
            "action type inside status=continue.\n"
            "Return exactly one strict JSON object and no surrounding text."
        )

    def _call_and_parse(
        self,
        *,
        image_path: Path,
        page_semantic_sha256: str,
        destination_picker_is_active: bool,
        ui_elements: Any,
        screen_width: int,
        screen_height: int,
        task_goal: str,
        user_prompt: str,
        episode_id: str,
        step: int,
        model_call_count: int,
        context_images: list[tuple[str, Path]] | None = None,
    ) -> tuple[dict[str, Any], list[ModelCall], dict[str, Any]]:
        if model_call_count >= self.max_model_calls:
            raise RuntimeError("Model-call budget exhausted.")
        initial = self.client.generate(
            image_path=image_path,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"step_{step:03d}_initial",
            context_images=context_images,
        )
        calls = [initial]
        adjudication_model_call_count = 0
        action_adjudications: list[dict[str, Any]] = []
        completion_adjudications: list[dict[str, Any]] = []
        visual_source_cache: dict[str, dict[str, Any]] = {}
        parse_kwargs = (
            {"schema_path": self.action_schema_path}
            if self.action_schema_path
            else {}
        )

        def parse_and_validate(
            content: str,
            *,
            repair_contract_error: str | None = None,
        ) -> Any:
            nonlocal adjudication_model_call_count
            parsed_candidate = parse_action_response(content, **parse_kwargs)
            if (
                repair_contract_error
                and "SOFT_KEYBOARD_DISMISS_REQUIRED:"
                in repair_contract_error
                and parsed_candidate.decision.get("action")
                != {"type": "press_back"}
            ):
                raise ActionValidationError(
                    "REPAIR_CONTRACT_GUARD: "
                    "SOFT_KEYBOARD_DISMISS_REQUIRED permits only the exact "
                    '{"type":"press_back"} action in this bounded repair.'
                )
            if (
                repair_contract_error
                and "DESTINATION_PICKER_RENAVIGATION_REQUIRED:"
                in repair_contract_error
                and not destination_picker_navigation_drawer_action(
                    ui_elements,
                    parsed_candidate.decision.get("action"),
                    screen_width=screen_width,
                    screen_height=screen_height,
                )
            ):
                raise ActionValidationError(
                    "REPAIR_CONTRACT_GUARD: "
                    "DESTINATION_PICKER_RENAVIGATION_REQUIRED permits only a "
                    "tap that hits the visible enabled top-left Show roots/"
                    "navigation-drawer control in this bounded repair."
                )
            if (
                repair_contract_error
                and "FILES_ROOTS_DRAWER_SELECTION_REQUIRED:"
                in repair_contract_error
            ):
                roots_repair_assessment = (
                    files_roots_drawer_action_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                if (
                    roots_repair_assessment.get("adjudicable") is not True
                    or roots_repair_assessment.get(
                        "matched_root_control_count"
                    )
                    < 1
                ):
                    raise ActionValidationError(
                        "REPAIR_CONTRACT_GUARD: "
                        "FILES_ROOTS_DRAWER_SELECTION_REQUIRED permits only "
                        "one tap that hits a visible enabled Android Files "
                        "roots-drawer row on this unchanged screenshot."
                    )
            if (
                repair_contract_error
                and repair_contract_error.startswith(
                    "POST_DESTINATION_COMMIT_GUARD:"
                )
                and parsed_candidate.decision.get("action")
                != {"type": "press_back"}
            ):
                raise ActionValidationError(
                    "REPAIR_CONTRACT_GUARD: POST_DESTINATION_COMMIT_GUARD "
                    "permits only the exact "
                    '{"type":"press_back"} action in this bounded repair.'
                )
            self.history_policy.validate_decision(parsed_candidate.decision)
            picker_commit_is_action = False
            if self.decision_guard is not None:
                picker_commit_is_action = destination_picker_commit_action(
                    ui_elements,
                    parsed_candidate.decision.get("action"),
                    screen_width=screen_width,
                    screen_height=screen_height,
                )
                empty_picker_stall_assessment = (
                    destination_picker_empty_stall_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                roots_drawer_action_assessment = (
                    files_roots_drawer_action_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                transfer_command_is_action = (
                    post_destination_transfer_command_action(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                selection_assessment = (
                    exact_selection_long_press_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        required_text=(
                            self.decision_guard.required_selection_text
                        ),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                focused_input_assessment = (
                    focused_editable_input_assessment(ui_elements)
                )
                keyboard_swipe_assessment = (
                    soft_keyboard_swipe_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                text_target_assessment = (
                    coordinate_type_text_target_assessment(
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                source_assessment = declared_text_source_assessment(
                    task_goal,
                    ui_elements,
                    parsed_candidate.decision.get("action"),
                )
                candidate_action = parsed_candidate.decision.get("action")
                visual_source_required = bool(
                    self.protocol_v2_2
                    and parsed_candidate.decision.get("status") == "done"
                    and isinstance(candidate_action, dict)
                    and candidate_action.get("type") == "answer"
                    and candidate_action.get("text_origin")
                    == "current_screen"
                    and source_assessment.get("matched") is not True
                )
                if visual_source_required:
                    candidate_text = str(candidate_action.get("text", ""))
                    candidate_sha256 = sha256(
                        candidate_text.encode("utf-8")
                    ).hexdigest()
                    cached = visual_source_cache.get(candidate_sha256)
                    if cached is None:
                        if self.visual_source_roles is None:
                            record = {
                                "schema_version": (
                                    "visual_text_source_adjudication.v1"
                                ),
                                "trigger": (
                                    "current_screen_text_source_candidate"
                                ),
                                "candidate_sha256": candidate_sha256,
                                "candidate_length": len(candidate_text),
                                "accepted": False,
                                "output": None,
                                "error": {
                                    "type": "VisualSourceCriticUnavailable",
                                    "message": (
                                        "No visual-source critic prompt was "
                                        "configured."
                                    ),
                                },
                                "model_call_ids": [],
                            }
                            cached = {
                                "accepted": False,
                                "adjudicated": False,
                                "record": record,
                            }
                        else:
                            visual_source = self.visual_source_roles.call(
                                role="critic",
                                image_path=image_path,
                                payload={
                                    "task": task_goal,
                                    "step": step,
                                    "trigger": (
                                        "current_screen_text_source_candidate"
                                    ),
                                    "answer_candidate": candidate_action,
                                    "completion_evidence": (
                                        parsed_candidate.decision.get(
                                            "completion_evidence",
                                            [],
                                        )
                                    ),
                                    "accessibility_source_assessment": (
                                        source_assessment
                                    ),
                                },
                                episode_id=episode_id,
                                step=step,
                                remaining_model_calls=max(
                                    0,
                                    self.max_model_calls
                                    - model_call_count
                                    - len(calls),
                                ),
                                allowed_memory_ids=set(),
                            )
                            calls.extend(visual_source.calls)
                            adjudication_model_call_count += len(
                                visual_source.calls
                            )
                            accepted = bool(
                                visual_source.error is None
                                and visual_source.output is not None
                                and visual_source.output.get("verdict")
                                == "proceed"
                            )
                            record = {
                                "schema_version": (
                                    "visual_text_source_adjudication.v1"
                                ),
                                "trigger": (
                                    "current_screen_text_source_candidate"
                                ),
                                "candidate_sha256": candidate_sha256,
                                "candidate_length": len(candidate_text),
                                "accepted": accepted,
                                "output": visual_source.output,
                                "error": visual_source.error,
                                "model_call_ids": [
                                    call.call_id
                                    for call in visual_source.calls
                                ],
                            }
                            cached = {
                                "accepted": accepted,
                                "adjudicated": True,
                                "record": record,
                            }
                        visual_source_cache[candidate_sha256] = cached
                        completion_adjudications.append(cached["record"])
                    source_assessment = {
                        **source_assessment,
                        "adjudicable": True,
                        "visual_adjudication_required": True,
                        "visual_adjudicated": cached["adjudicated"],
                        "visual_adjudication_accepted": cached["accepted"],
                        "matched": cached["accepted"],
                    }
                field_role_assessment = (
                    task_literal_field_role_assessment(
                        task_goal,
                        ui_elements,
                        parsed_candidate.decision.get("action"),
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                )
                self.decision_guard.validate_decision(
                    parsed_candidate.decision,
                    page_sha256=page_semantic_sha256,
                    destination_picker_is_active=(
                        destination_picker_is_active
                    ),
                    destination_picker_commit_is_action=(
                        picker_commit_is_action
                    ),
                    destination_picker_empty_stall_assessment=(
                        empty_picker_stall_assessment
                    ),
                    files_roots_drawer_action_assessment=(
                        roots_drawer_action_assessment
                    ),
                    post_destination_transfer_command_is_action=(
                        transfer_command_is_action
                    ),
                    exact_selection_assessment=selection_assessment,
                    focused_input_assessment=focused_input_assessment,
                    soft_keyboard_swipe_assessment=(
                        keyboard_swipe_assessment
                    ),
                    coordinate_text_target_assessment=(
                        text_target_assessment
                    ),
                    declared_text_source_assessment=source_assessment,
                    declared_source_soft_keyboard_present=bool(
                        self.protocol_v2_2
                        and focused_input_assessment.get(
                            "soft_keyboard_present"
                        )
                    ),
                    task_literal_field_role_assessment=(
                        field_role_assessment
                    ),
                )
            action_adjudication = self.history_policy.adjudicate_action(
                parsed_candidate.decision,
                image_path=image_path,
                episode_id=episode_id,
                step=step,
                remaining_model_calls=max(
                    0,
                    self.max_model_calls - model_call_count - len(calls),
                ),
                consequential_action_candidate=(
                    picker_commit_is_action
                    if self.protocol_v2_2
                    and destination_picker_is_active
                    else None
                ),
            )
            calls.extend(action_adjudication.calls)
            adjudication_model_call_count += len(
                action_adjudication.calls
            )
            if action_adjudication.record is not None:
                action_adjudications.append(action_adjudication.record)
            if not action_adjudication.accepted:
                adjudication_error = (
                    action_adjudication.error
                    or "Same-turn action adjudication rejected the action."
                )
                if (
                    self.protocol_v2_2
                    and destination_picker_is_active
                    and picker_commit_is_action
                ):
                    adjudication_error = (
                        "DESTINATION_PICKER_GUARD: "
                        "DESTINATION_PICKER_RENAVIGATION_REQUIRED: the "
                        "consequential-action critic rejected the visible "
                        "Copy/Move commit while the destination picker remains "
                        "active. Keep the pending operation open and use its "
                        "visible top-left Show roots/navigation-drawer control "
                        "to choose another directory. Original critic result: "
                        + adjudication_error
                    )
                raise ActionValidationError(
                    adjudication_error
                )
            adjudication = self.history_policy.adjudicate_completion(
                parsed_candidate.decision,
                image_path=image_path,
                episode_id=episode_id,
                step=step,
                remaining_model_calls=max(
                    0,
                    self.max_model_calls - model_call_count - len(calls),
                ),
            )
            calls.extend(adjudication.calls)
            adjudication_model_call_count += len(adjudication.calls)
            if adjudication.record is not None:
                completion_adjudications.append(adjudication.record)
            if not adjudication.accepted:
                raise ActionValidationError(
                    adjudication.error
                    or "Same-turn completion adjudication rejected completion."
                )
            return parsed_candidate

        try:
            parsed = parse_and_validate(initial.content)
            return (
                parsed.decision,
                calls,
                {
                    "first_pass": parsed.first_pass,
                    "extraction_used": parsed.extraction_used,
                    "model_repair_used": False,
                    "schema_sha256": parsed.schema_sha256,
                    "adjudication_model_call_count": (
                        adjudication_model_call_count
                    ),
                    "action_adjudications": action_adjudications,
                    "completion_adjudications": completion_adjudications,
                },
            )
        except ActionValidationError as initial_error:
            if model_call_count + len(calls) >= self.max_model_calls:
                raise ModelOutputInvalid(
                    calls=calls,
                    initial_error=str(initial_error),
                    repair_error=(
                        "Repair unavailable because the model-call budget "
                        "was exhausted after validation/adjudication."
                    ),
                    adjudication_model_call_count=(
                        adjudication_model_call_count
                    ),
                    action_adjudications=action_adjudications,
                    completion_adjudications=completion_adjudications,
                ) from initial_error
            repair_prompt = self._repair_prompt(
                user_prompt,
                initial.content,
                str(initial_error),
                protocol_v2=self.protocol_v2,
            )
            repaired = self.client.generate(
                image_path=image_path,
                system_prompt=self.system_prompt,
                user_prompt=repair_prompt,
                episode_id=episode_id,
                call_label=f"step_{step:03d}_repair",
                context_images=context_images,
            )
            calls.append(repaired)
            try:
                parsed = parse_and_validate(
                    repaired.content,
                    repair_contract_error=str(initial_error),
                )
            except ActionValidationError as repair_error:
                raise ModelOutputInvalid(
                    calls=calls,
                    initial_error=str(initial_error),
                    repair_error=str(repair_error),
                    adjudication_model_call_count=(
                        adjudication_model_call_count
                    ),
                    action_adjudications=action_adjudications,
                    completion_adjudications=completion_adjudications,
                ) from repair_error
            return (
                parsed.decision,
                calls,
                {
                    "first_pass": False,
                    "extraction_used": parsed.extraction_used,
                    "model_repair_used": True,
                    "initial_validation_error": str(initial_error),
                    "schema_sha256": parsed.schema_sha256,
                    "adjudication_model_call_count": (
                        adjudication_model_call_count
                    ),
                    "action_adjudications": action_adjudications,
                    "completion_adjudications": completion_adjudications,
                },
            )

    def run(
        self,
        *,
        env: Any,
        task: Any,
        episode_id: str,
        episode_dir: Path,
        seed: int,
        protocol: str = "excluded_protocol_dry_run",
        variant: str = "B0",
    ) -> dict[str, Any]:
        logger = EpisodeLogger(episode_dir)
        started = _utc_now()
        steps: list[dict[str, Any]] = []
        model_call_count = 0
        executor_model_call_count = 0
        history_model_call_count = 0
        previous_outcome = "none; this is the first observation"
        termination_reason = "max_steps"
        evaluator_reward: float | None = None
        task_initialized = False
        error_record: dict[str, Any] | None = None
        model_output_error: dict[str, Any] | None = None
        readiness_observation_count = 0
        readiness_retry_count = 0
        task_params = _json_safe(task.params)
        initial_task_goal = str(task.goal)
        effective_task_goal = initial_task_goal
        self.history_policy.reset(
            episode_dir=episode_dir,
            goal=initial_task_goal,
            episode_id=episode_id,
            task_id=task.name,
        )
        if self.decision_guard is not None:
            required_selection_text = None
            if str(task.name) in {"FilesMoveFile", "FilesDeleteFile"}:
                candidate = task_params.get("file_name")
                if isinstance(candidate, str) and candidate:
                    required_selection_text = candidate
            self.decision_guard.reset(
                goal=initial_task_goal,
                required_selection_text=required_selection_text,
            )

        logger.append(
            {
                "event": "episode_start",
                "episode_id": episode_id,
                "protocol": protocol,
                "variant": variant,
                "history_variant": self.history_policy.variant,
                "seed": seed,
                "task_name": task.name,
                "task_goal": initial_task_goal,
                "task_params": task_params,
                "max_steps": self.max_steps,
                "max_model_calls": self.max_model_calls,
            }
        )

        try:
            env.reset(go_home=True)
            env.hide_automation_ui()
            task.initialize_task(env)
            task_initialized = True
            post_initialization_task_goal = str(task.goal)
            effective_task_goal = (
                initial_task_goal
                if self.protocol_v2_2
                else post_initialization_task_goal
            )
            logger.append(
                {
                    "event": "task_initialized",
                    "task_goal_before_initialization": initial_task_goal,
                    "task_goal_after_initialization": (
                        post_initialization_task_goal
                    ),
                    "task_goal_changed": (
                        initial_task_goal != post_initialization_task_goal
                    ),
                    "effective_task_goal": effective_task_goal,
                }
            )

            for step in range(self.max_steps):
                if model_call_count >= self.max_model_calls:
                    termination_reason = "model_call_budget_exhausted"
                    logger.append(
                        {
                            "event": "model_call_budget_exhausted",
                            "model_call_count": model_call_count,
                            "max_model_calls": self.max_model_calls,
                        }
                    )
                    break
                state_before, before_readiness = self._observe_state(
                    env,
                    require_accessibility=False,
                )
                readiness_observation_count += len(before_readiness)
                readiness_retry_count += max(0, len(before_readiness) - 1)
                height, width = state_before.pixels.shape[:2]
                before_path = logger.save_screenshot(
                    state_before.pixels,
                    f"step_{step:03d}_before.png",
                )
                before_pixel_sha = _sha256_file(before_path)
                before_semantic = (
                    semantic_ui_snapshot(
                        getattr(state_before, "ui_elements", ()),
                        fallback_sha256=before_pixel_sha,
                    )
                    if self.protocol_v2
                    else {
                        "source": "protocol_v1_screenshot",
                        "sha256": before_pixel_sha,
                        "element_count": 0,
                        "visible_failure_texts": [],
                        "infrastructure_failure_texts": [],
                    }
                )
                if before_semantic.get("infrastructure_failure_texts"):
                    messages = list(
                        before_semantic["infrastructure_failure_texts"]
                    )
                    logger.append(
                        {
                            "event": "visible_infrastructure_failure",
                            "phase": "before_decision",
                            "step": step,
                            "messages": messages,
                            "screenshot": before_path.name,
                            "readiness_observations": before_readiness,
                        }
                    )
                    raise VisibleInfrastructureFailure(messages)
                history_context = self.history_policy.context()
                evidence_outcome = previous_outcome
                user_prompt = self._user_prompt(
                    goal=effective_task_goal,
                    step=step,
                    max_steps=self.max_steps,
                    model_calls=model_call_count,
                    max_model_calls=self.max_model_calls,
                    screen_width=width,
                    screen_height=height,
                    previous_outcome=previous_outcome,
                    memory_context=history_context.rendered,
                    protocol_v2=self.protocol_v2,
                    protocol_v2_2=self.protocol_v2_2,
                    post_destination_commit_active=bool(
                        self.decision_guard is not None
                        and self.decision_guard.post_destination_commit_active
                    ),
                )
                try:
                    picker_active = destination_picker_active(
                        getattr(state_before, "ui_elements", ()),
                        screen_height=height,
                    )
                    decision, calls, parse_meta = self._call_and_parse(
                        image_path=before_path,
                        page_semantic_sha256=before_semantic["sha256"],
                        destination_picker_is_active=picker_active,
                        ui_elements=getattr(
                            state_before, "ui_elements", ()
                        ),
                        screen_width=width,
                        screen_height=height,
                        task_goal=effective_task_goal,
                        user_prompt=user_prompt,
                        episode_id=episode_id,
                        step=step,
                        model_call_count=model_call_count,
                        context_images=history_context.images,
                    )
                except ModelOutputInvalid as exc:
                    model_call_count += len(exc.calls)
                    history_model_call_count += (
                        exc.adjudication_model_call_count
                    )
                    executor_model_call_count += (
                        len(exc.calls) - exc.adjudication_model_call_count
                    )
                    termination_reason = "model_output_invalid_after_repair"
                    model_output_error = {
                        "type": "ActionValidationError",
                        "initial_validation_error": exc.initial_error,
                        "repair_validation_error": exc.repair_error,
                        "action_adjudications": (
                            exc.action_adjudications
                        ),
                        "completion_adjudications": (
                            exc.completion_adjudications
                        ),
                    }
                    step_record = {
                        "event": "step",
                        "step": step,
                        "before_screenshot": before_path.name,
                        "before_screenshot_sha256": before_pixel_sha,
                        "screen_size": [width, height],
                        "user_prompt": user_prompt,
                        "history_context": {
                            "variant": self.history_policy.variant,
                            "rendered": history_context.rendered,
                            "images": [
                                {
                                    "label": label,
                                    "path": path.name,
                                    "sha256": _sha256_file(path),
                                }
                                for label, path in history_context.images
                            ],
                        },
                        "model_calls": [
                            call.audit_record() for call in exc.calls
                        ],
                        "parse": {
                            "first_pass": False,
                            "model_repair_used": True,
                            "valid_after_one_repair": False,
                            **model_output_error,
                        },
                        "decision": None,
                        "executed": False,
                    }
                    if self.protocol_v2:
                        step_record["before_semantic_ui"] = before_semantic
                    steps.append(step_record)
                    logger.append(step_record)
                    logger.append(
                        {
                            "event": "model_output_invalid_after_repair",
                            "error": model_output_error,
                        }
                    )
                    break
                model_call_count += len(calls)
                adjudication_call_count = int(
                    parse_meta.get("adjudication_model_call_count", 0)
                )
                history_model_call_count += adjudication_call_count
                executor_model_call_count += (
                    len(calls) - adjudication_call_count
                )
                parse_meta["valid_after_one_repair"] = True
                step_record: dict[str, Any] = {
                    "event": "step",
                    "step": step,
                    "before_screenshot": before_path.name,
                    "before_screenshot_sha256": before_pixel_sha,
                    "screen_size": [width, height],
                    "user_prompt": user_prompt,
                    "history_context": {
                        "variant": self.history_policy.variant,
                        "rendered": history_context.rendered,
                        "images": [
                            {
                                "label": label,
                                "path": path.name,
                                "sha256": _sha256_file(path),
                            }
                            for label, path in history_context.images
                        ],
                    },
                    "model_calls": [call.audit_record() for call in calls],
                    "parse": parse_meta,
                    "decision": decision,
                    "action_authority": action_authority_record(
                        decision,
                        completion_adjudications=[
                            *parse_meta.get("action_adjudications", []),
                            *parse_meta.get(
                                "completion_adjudications",
                                [],
                            ),
                        ],
                    ),
                    "before_readiness_observations": before_readiness,
                }
                if self.protocol_v2:
                    step_record["before_semantic_ui"] = before_semantic

                picker_commit_executed = destination_picker_commit_action(
                    getattr(state_before, "ui_elements", ()),
                    decision.get("action"),
                    screen_width=width,
                    screen_height=height,
                )
                answer_action = bool(
                    decision["status"] == "done"
                    and isinstance(decision.get("action"), dict)
                    and decision["action"].get("type") == "answer"
                )
                if decision["status"] != "continue" and not answer_action:
                    termination_reason = f"model_{decision['status']}"
                    step_record["executed"] = False
                    steps.append(step_record)
                    logger.append(step_record)
                    break

                mapped = self.adapter.map_action(
                    decision["action"],
                    screen_width=width,
                    screen_height=height,
                )
                try:
                    self.adapter.execute(env, mapped)
                except Exception as exc:
                    step_record.update(
                        {
                            "executed": False,
                            "mapped_action": mapped.audit_record(),
                            "execution_error": {
                                "type": type(exc).__name__,
                                "message": str(exc),
                            },
                        }
                    )
                    steps.append(step_record)
                    logger.append(step_record)
                    raise
                state_after, after_readiness = self._observe_state(
                    env,
                    # Any action can transiently change the foreground
                    # activity (for example, an Android chooser overlay).
                    # Do not pair a new screenshot with the previous
                    # activity's stale accessibility tree.
                    require_accessibility=self.protocol_v2_2,
                )
                readiness_observation_count += len(after_readiness)
                readiness_retry_count += max(0, len(after_readiness) - 1)
                after_path = logger.save_screenshot(
                    state_after.pixels,
                    f"step_{step:03d}_after.png",
                )
                before_sha = step_record["before_screenshot_sha256"]
                after_sha = _sha256_file(after_path)
                after_semantic = (
                    semantic_ui_snapshot(
                        getattr(state_after, "ui_elements", ()),
                        fallback_sha256=after_sha,
                    )
                    if self.protocol_v2
                    else {
                        "source": "protocol_v1_screenshot",
                        "sha256": after_sha,
                        "element_count": 0,
                        "visible_failure_texts": [],
                        "infrastructure_failure_texts": [],
                    }
                )
                changed = before_sha != after_sha
                step_record.update(
                    {
                        "executed": True,
                        "mapped_action": mapped.audit_record(),
                        "after_screenshot": after_path.name,
                        "after_screenshot_sha256": after_sha,
                        "screenshot_changed": changed,
                        "after_readiness_observations": after_readiness,
                    }
                )
                if self.protocol_v2:
                    step_record["after_semantic_ui"] = after_semantic
                if after_semantic.get("infrastructure_failure_texts"):
                    messages = list(
                        after_semantic["infrastructure_failure_texts"]
                    )
                    step_record["visible_infrastructure_failure"] = {
                        "phase": "after_action",
                        "messages": messages,
                    }
                    steps.append(step_record)
                    logger.append(step_record)
                    raise VisibleInfrastructureFailure(messages)
                guard_transition = None
                if self.decision_guard is not None:
                    guard_transition = self.decision_guard.observe_transition(
                        before_sha256=before_semantic["sha256"],
                        action=decision["action"],
                        after_sha256=after_semantic["sha256"],
                        before_pixel_sha256=before_sha,
                        after_pixel_sha256=after_sha,
                        before_visible_failures=before_semantic[
                            "visible_failure_texts"
                        ],
                        after_visible_failures=after_semantic[
                            "visible_failure_texts"
                        ],
                        destination_picker_commit_executed=(
                            picker_commit_executed
                        ),
                    )
                    step_record["protocol_v2_guard"] = guard_transition
                if answer_action:
                    answer_text = str(decision["action"]["text"])
                    interaction_cache = getattr(
                        env, "interaction_cache", None
                    )
                    step_record["answer_audit"] = {
                        "text_sha256": sha256(
                            answer_text.encode("utf-8")
                        ).hexdigest(),
                        "text_length": len(answer_text),
                        "interaction_cache_populated": (
                            bool(interaction_cache)
                        ),
                        "interaction_cache_matches_answer": (
                            interaction_cache == answer_text
                        ),
                    }
                    termination_reason = "model_answer"
                    steps.append(step_record)
                    logger.append(step_record)
                    break
                semantic_changed = (
                    guard_transition["semantic_changed"]
                    if guard_transition is not None
                    else changed
                )
                new_visible_failures = (
                    guard_transition["new_visible_failures"]
                    if guard_transition is not None
                    else []
                )
                if self.protocol_v2:
                    previous_outcome = (
                        f"Executed {json.dumps(decision['action'], ensure_ascii=False)}; "
                        f"the screenshot {'changed' if changed else 'did not change'}; "
                        "the semantic UI "
                        f"{'changed' if semantic_changed else 'did not change'}."
                    )
                    if new_visible_failures:
                        previous_outcome += (
                            " Visible failure: "
                            + " | ".join(new_visible_failures)
                            + "."
                        )
                else:
                    previous_outcome = (
                        f"Executed {json.dumps(decision['action'], ensure_ascii=False)}; "
                        f"the screenshot {'changed' if changed else 'did not change'}."
                    )
                history_update = self.history_policy.observe(
                    HistoryEntry(
                        step=step,
                        decision_summary=decision["decision_summary"],
                        action=decision["action"],
                        observed_outcome=previous_outcome,
                        screenshot_path=after_path,
                        screenshot_sha256=after_sha,
                        semantic_ui_sha256=(
                            after_semantic["sha256"]
                            if self.protocol_v2
                            else ""
                        ),
                        before_screenshot_path=before_path,
                        before_screenshot_sha256=before_sha,
                        before_semantic_ui_sha256=(
                            before_semantic["sha256"]
                            if self.protocol_v2
                            else ""
                        ),
                        visible_failure_texts=(
                            tuple(new_visible_failures)
                            if self.protocol_v2
                            else ()
                        ),
                        evidence_outcome=evidence_outcome,
                        expected_outcome=decision["expected_outcome"],
                        state_delta=tuple(decision["state_delta"]),
                        model_call_id=(
                            calls[-1].call_id if calls else None
                        ),
                    ),
                    episode_id=episode_id,
                    remaining_model_calls=(
                        self.max_model_calls - model_call_count
                    ),
                )
                model_call_count += len(history_update.calls)
                history_model_call_count += len(history_update.calls)
                step_record["history_update"] = {
                    "summary_updated": history_update.summary_updated,
                    "summary_schema_sha256": (
                        history_update.summary_schema_sha256
                    ),
                    "error": history_update.error,
                    "details": history_update.details,
                    "model_calls": [
                        call.audit_record() for call in history_update.calls
                    ],
                }
                steps.append(step_record)
                logger.append(step_record)

            evaluator_reward = float(task.is_successful(env))
            logger.append(
                {
                    "event": "evaluator_result",
                    "reward": evaluator_reward,
                    "visible_to_agent": False,
                }
            )
        except Exception as exc:
            termination_reason = "infrastructure_or_controller_error"
            error_record = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            logger.append({"event": "episode_error", "error": error_record})
        finally:
            if task_initialized:
                try:
                    task.tear_down(env)
                    logger.append({"event": "task_torn_down"})
                except Exception as exc:
                    logger.append(
                        {
                            "event": "teardown_error",
                            "error": {
                                "type": type(exc).__name__,
                                "message": str(exc),
                            },
                        }
                    )
            try:
                env.reset(go_home=True)
                logger.append({"event": "post_episode_reset"})
            except Exception as exc:
                logger.append(
                    {
                        "event": "reset_error",
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    }
                )

        first_pass_count = sum(
            int(step["parse"]["first_pass"]) for step in steps if "parse" in step
        )
        decision_attempt_count = sum(1 for step in steps if "parse" in step)
        valid_decision_count = sum(
            int(step["parse"].get("valid_after_one_repair", True))
            for step in steps
            if "parse" in step
        )
        executed_count = sum(int(step.get("executed", False)) for step in steps)
        failure_code = classify_failure_code(
            error_record=error_record,
            model_output_error=model_output_error,
            evaluator_reward=evaluator_reward,
            termination_reason=termination_reason,
        )

        summary = {
            "episode_id": episode_id,
            "protocol": protocol,
            "variant": variant,
            "history_variant": self.history_policy.variant,
            "started_at": started,
            "finished_at": _utc_now(),
            "task_name": task.name,
            "task_goal": effective_task_goal,
            "task_params": task_params,
            "seed": seed,
            "termination_reason": termination_reason,
            "evaluator_reward": evaluator_reward,
            "success": evaluator_reward == 1.0,
            "failure_code": failure_code,
            "decision_count": valid_decision_count,
            "decision_attempt_count": decision_attempt_count,
            "valid_after_one_repair_count": valid_decision_count,
            "executed_action_count": executed_count,
            "model_call_count": model_call_count,
            "executor_model_call_count": executor_model_call_count,
            "history_model_call_count": history_model_call_count,
            "readiness_observation_count": readiness_observation_count,
            "readiness_retry_count": readiness_retry_count,
            "first_pass_parse_count": first_pass_count,
            "first_pass_parse_rate": (
                first_pass_count / decision_attempt_count
                if decision_attempt_count
                else None
            ),
            "error": error_record,
            "model_output_error": model_output_error,
            "protocol_v2_guard": (
                self.decision_guard.audit_record()
                if self.decision_guard is not None
                else None
            ),
            "steps": steps,
        }
        _write_json(episode_dir / "episode.json", summary)
        self._write_replay(episode_dir, summary)
        logger.append(
            {
                "event": "episode_complete",
                "success": summary["success"],
                "failure_code": failure_code,
            }
        )
        return summary

    @staticmethod
    def _write_replay(episode_dir: Path, summary: dict[str, Any]) -> None:
        rows = []
        for step in summary["steps"]:
            before = step.get("before_screenshot")
            after = step.get("after_screenshot")
            decision = html.escape(
                json.dumps(step.get("decision"), ensure_ascii=False, indent=2)
            )
            rows.append(
                "<section>"
                f"<h2>Step {step.get('step')}</h2>"
                f"<pre>{decision}</pre>"
                f"<img src='{html.escape(before or '')}' alt='before'>"
                + (
                    f"<img src='{html.escape(after)}' alt='after'>"
                    if after
                    else ""
                )
                + "</section>"
            )
        document = (
            "<!doctype html><meta charset='utf-8'>"
            "<style>body{font-family:sans-serif;max-width:1200px;margin:auto}"
            "img{width:320px;margin:8px;border:1px solid #aaa}"
            "pre{white-space:pre-wrap;background:#f4f4f4;padding:12px}</style>"
            f"<h1>{html.escape(summary['episode_id'])}</h1>"
            f"<p>{html.escape(summary['task_goal'])}</p>"
            + "".join(rows)
        )
        (episode_dir / "replay.html").write_text(document, encoding="utf-8")
