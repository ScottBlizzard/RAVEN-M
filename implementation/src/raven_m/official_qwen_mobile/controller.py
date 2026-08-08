"""Minimal AndroidWorld loop for the published Qwen Mobile Agent recipe."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
import traceback
from typing import Any

import numpy as np
from PIL import Image

from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.models.vllm_client import VLLMClient

from .protocol import (
    DEFAULT_SWIPE_DURATION_MS,
    OFFICIAL_QWEN_COMMIT,
    OFFICIAL_QWEN_NOTEBOOK,
    OFFICIAL_QWEN_REPOSITORY,
    OFFICIAL_SYSTEM_PROMPT,
    OfficialProtocolError,
    build_user_prompt,
    parse_official_response,
)
from .source_document_coverage_gate import SourceDocumentCoverageGate


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


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return _json_safe(value.value)
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return repr(value)


def _ui_node_records(state: Any) -> list[dict[str, Any]]:
    """Serialize the environment's accessibility side-channel for audit only."""
    records: list[dict[str, Any]] = []
    for element in getattr(state, "ui_elements", ()) or ():
        if isinstance(element, dict):
            record = {str(key): _json_safe(value) for key, value in element.items()}
        else:
            record = {
                key: _json_safe(value)
                for key, value in vars(element).items()
                if not key.startswith("_")
            }
        records.append(record)
    return records


def _current_activity(env: Any) -> dict[str, Any]:
    try:
        from android_env.proto import adb_pb2
        from android_world.env import adb_utils

        activity, response = adb_utils.get_current_activity(
            env.controller,
            timeout_sec=10.0,
        )
        return {
            "available": response.status == adb_pb2.AdbResponse.Status.OK,
            "activity": activity,
            "package": activity.split("/", 1)[0] if activity and "/" in activity else None,
            "error": response.error_message or None,
        }
    except Exception as exc:  # Audit evidence must never change agent execution.
        return {
            "available": False,
            "activity": None,
            "package": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _audit_snapshot(
    *,
    env: Any,
    state: Any,
    episode_dir: Path,
    label: str,
) -> dict[str, Any]:
    pixels = np.asarray(state.pixels)
    screenshot = episode_dir / f"{label}.png"
    Image.fromarray(pixels).save(screenshot)
    ui_records = _ui_node_records(state)
    ui_payload = json.dumps(
        ui_records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    ui_path = episode_dir / f"{label}.ui.json"
    ui_path.write_text(
        json.dumps(ui_records, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    packages = sorted(
        {
            str(item.get("package_name") or item.get("package") or "")
            for item in ui_records
            if item.get("package_name") or item.get("package")
        }
    )
    return {
        "screenshot": screenshot.name,
        "screenshot_sha256": _sha256(screenshot),
        "pixel_sha256": sha256(pixels.tobytes()).hexdigest(),
        "ui_record": ui_path.name,
        "ui_sha256": sha256(ui_payload).hexdigest(),
        "ui_node_count": len(ui_records),
        "ui_packages": packages,
        "foreground": _current_activity(env),
        "pixels": pixels,
    }


def _snapshot_record(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in snapshot.items() if key != "pixels"}


def _pixel_transition(before: np.ndarray, after: np.ndarray) -> dict[str, Any]:
    if before.shape != after.shape:
        return {
            "same_shape": False,
            "before_shape": list(before.shape),
            "after_shape": list(after.shape),
            "mean_absolute_difference": None,
            "changed_pixel_fraction_gt_5": None,
            "exactly_unchanged": False,
        }
    difference = np.abs(before.astype(np.int16) - after.astype(np.int16))
    per_pixel = np.max(difference, axis=2) if difference.ndim == 3 else difference
    return {
        "same_shape": True,
        "before_shape": list(before.shape),
        "after_shape": list(after.shape),
        "mean_absolute_difference": float(difference.mean()),
        "changed_pixel_fraction_gt_5": float(np.mean(per_pixel > 5)),
        "exactly_unchanged": bool(np.array_equal(before, after)),
    }


class OfficialQwenMobileController:
    """No-memory, no-repair, no-critic implementation of the official loop."""

    def __init__(
        self,
        client: VLLMClient,
        *,
        max_steps: int = 60,
        max_tokens: int = 32768,
        adapter: AndroidWorldAdapter | None = None,
        run_metadata: dict[str, Any] | None = None,
        system_prompt: str = OFFICIAL_SYSTEM_PROMPT,
        history_policy: str = "official_text_action_summaries_only",
        source_document_coverage_gate: SourceDocumentCoverageGate | None = None,
        stop_after_markor_source_exit: bool = False,
    ) -> None:
        self.client = client
        self.max_steps = max(1, int(max_steps))
        self.max_tokens = max(1, int(max_tokens))
        self.adapter = adapter or AndroidWorldAdapter()
        self.run_metadata = dict(run_metadata or {})
        self.system_prompt = str(system_prompt)
        self.history_policy = str(history_policy)
        self.source_document_coverage_gate = source_document_coverage_gate
        self.stop_after_markor_source_exit = bool(stop_after_markor_source_exit)

    def _committed_history_summary(
        self,
        *,
        model_action_summary: str,
        canonical_action: dict[str, Any],
        transition: dict[str, Any],
    ) -> tuple[str, bool, str | None]:
        """Commit model prose only when the selected history policy permits it.

        The transition-attested diagnostic does not infer whether the task-level
        action succeeded.  It only prevents a visibly unchanged step from being
        carried forward as if the model's semantic description were observed.
        """

        if self.history_policy != "transition_attested_action_summaries_v1":
            return model_action_summary, False, None
        changed_fraction = transition.get("changed_pixel_fraction_gt_5")
        no_observable_transition = (
            isinstance(changed_fraction, (int, float))
            and float(changed_fraction) < 0.001
            and not bool(transition.get("activity_changed"))
            and not bool(transition.get("ui_sha_changed"))
        )
        if not no_observable_transition:
            return model_action_summary, False, None
        executed = json.dumps(
            canonical_action,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        committed = (
            f"Executed canonical action {executed}, but observed no page, "
            "activity, or UI-tree transition. The semantic effect described "
            "by the model is unverified; do not repeat the same action under "
            "the same visible state."
        )
        return committed, True, "no_observable_transition"

    @staticmethod
    def _press_recents(env: Any) -> None:
        from android_env.proto import adb_pb2
        from android_world.env import adb_utils

        response = adb_utils.issue_generic_request(
            ["shell", "input", "keyevent", "187"],
            env.controller,
            timeout_sec=10.0,
        )
        if response.status != adb_pb2.AdbResponse.Status.OK:
            raise RuntimeError(
                "Android recent-apps key failed: "
                f"status={response.status}, error={response.error_message!r}"
            )

    def _execute(
        self,
        env: Any,
        action: dict[str, Any],
        *,
        screen_width: int,
        screen_height: int,
    ) -> dict[str, Any]:
        if action["type"] == "press_recents":
            self._press_recents(env)
            return {
                "canonical": action,
                "screen_size": [screen_width, screen_height],
                "actual_pixels": {},
                "upstream_action": {"action_type": "adb_keyevent", "keycode": 187},
            }
        mapped = self.adapter.map_action(
            action,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        self.adapter.execute(env, mapped)
        return mapped.audit_record()

    def run(
        self,
        *,
        env: Any,
        task: Any,
        episode_id: str,
        episode_dir: Path,
        seed: int,
    ) -> dict[str, Any]:
        episode_dir.mkdir(parents=True, exist_ok=False)
        events_path = episode_dir / "events.jsonl"

        def log(event: dict[str, Any]) -> None:
            with events_path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"time": _utc_now(), **event},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

        started_at = _utc_now()
        prompt_sha = sha256(self.system_prompt.encode("utf-8")).hexdigest()
        initial_goal = str(task.goal)
        effective_goal = initial_goal
        history: list[str] = []
        steps: list[dict[str, Any]] = []
        task_initialized = False
        termination_reason = "max_steps"
        claimed_status: str | None = None
        evaluator_reward: float | None = None
        error: dict[str, Any] | None = None

        log(
            {
                "event": "episode_start",
                "episode_id": episode_id,
                "seed": seed,
                "task_name": str(task.name),
                "task_goal_before_initialization": initial_goal,
                "task_params": _json_safe(task.params),
                "max_steps": self.max_steps,
                "max_tokens": self.max_tokens,
                "baseline": "qwen3_vl_32b_official_public_recipe_port",
                "reference_notebook_model": "qwen3vl-235A22-instruct",
                "experiment_model": "Qwen/Qwen3-VL-32B-Instruct",
                "official_repository": OFFICIAL_QWEN_REPOSITORY,
                "official_commit": OFFICIAL_QWEN_COMMIT,
                "official_notebook": OFFICIAL_QWEN_NOTEBOOK,
                "official_system_prompt_sha256": prompt_sha,
                "generation_sampling": getattr(self.client, "sampling", None),
                "history_policy": self.history_policy,
                "image_policy": "current_screenshot_only",
                "swipe_duration_ms": DEFAULT_SWIPE_DURATION_MS,
                "run_metadata": self.run_metadata,
            }
        )
        try:
            env.reset(go_home=True)
            hide_automation_ui = getattr(env, "hide_automation_ui", None)
            if callable(hide_automation_ui):
                hide_automation_ui()
            task.initialize_task(env)
            task_initialized = True
            effective_goal = str(task.goal)
            log(
                {
                    "event": "task_initialized",
                    "task_goal_after_initialization": effective_goal,
                }
            )

            pending_state: Any | None = None
            for step_index in range(self.max_steps):
                state = (
                    pending_state
                    if pending_state is not None
                    else env.get_state(wait_to_stabilize=True)
                )
                pending_state = None
                height, width = state.pixels.shape[:2]
                before = _audit_snapshot(
                    env=env,
                    state=state,
                    episode_dir=episode_dir,
                    label=f"step_{step_index:03d}_before",
                )
                screenshot = episode_dir / str(before["screenshot"])
                user_prompt = build_user_prompt(effective_goal, history)
                call = self.client.generate(
                    image_path=screenshot,
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    episode_id=episode_id,
                    call_label=f"official_step_{step_index:03d}",
                    max_tokens=self.max_tokens,
                    context_images=[],
                    user_prompt_before_image=True,
                    current_image_label=None,
                )
                record: dict[str, Any] = {
                    "event": "step",
                    "step": step_index,
                    "screen_size": [width, height],
                    "before": _snapshot_record(before),
                    "before_screenshot": before["screenshot"],
                    "before_screenshot_sha256": before["screenshot_sha256"],
                    "user_prompt": user_prompt,
                    "history_before": list(history),
                    "model_call": call.audit_record(),
                    "executed": False,
                    "layers": {
                        "L0_runtime": {
                            "model_call_returned": True,
                            "latency_seconds": call.raven_meta.get("latency_seconds"),
                            "transport_attempts": call.raven_meta.get("transport_attempts"),
                        },
                        "L1_perception_grounding": {
                            "model_received_current_screenshot_only": True,
                            "audit_ui_visible_to_model": False,
                            "before_pixel_sha256": before["pixel_sha256"],
                        },
                        "L2_protocol_coordinate": {"parse_valid": None},
                        "L3_execution": {"attempted": False, "completed": False},
                        "L4_transition_progress": {"observed": False},
                        "L5_completion_evaluator": {
                            "terminal_claim": None,
                            "evaluator_visible_to_model": False,
                        },
                    },
                }
                try:
                    decision = parse_official_response(call.content)
                except OfficialProtocolError as exc:
                    record["parse_error"] = str(exc)
                    record["layers"]["L2_protocol_coordinate"] = {
                        "parse_valid": False,
                        "error": str(exc),
                    }
                    steps.append(record)
                    log(record)
                    termination_reason = "official_output_invalid"
                    break
                record["decision"] = decision.audit_record()
                canonical_action = decision.canonical_action
                gate_decision: dict[str, Any] | None = None
                if self.source_document_coverage_gate is not None:
                    canonical_action, gate_decision = (
                        self.source_document_coverage_gate.filter_action(
                            before_activity=before["foreground"].get("activity"),
                            proposed_action=decision.canonical_action,
                            terminal_status=decision.terminal_status,
                        )
                    )
                    record["source_document_coverage_gate"] = {
                        "decision": gate_decision,
                        "state_before_execution": (
                            self.source_document_coverage_gate.audit_record()
                        ),
                    }
                record["layers"]["L2_protocol_coordinate"] = {
                    "parse_valid": True,
                    "model_canonical_action": decision.canonical_action,
                    "executed_canonical_action": canonical_action,
                }
                if canonical_action is None:
                    claimed_status = decision.terminal_status
                    termination_reason = f"model_terminate_{claimed_status}"
                    record["layers"]["L5_completion_evaluator"]["terminal_claim"] = (
                        claimed_status
                    )
                    steps.append(record)
                    log(record)
                    break
                execution_started_utc = _utc_now()
                execution_started_monotonic = time.perf_counter()
                record["layers"]["L3_execution"] = {
                    "attempted": True,
                    "completed": False,
                    "started_at": execution_started_utc,
                }
                try:
                    mapped = self._execute(
                        env,
                        canonical_action,
                        screen_width=width,
                        screen_height=height,
                    )
                except Exception as exc:
                    record["layers"]["L3_execution"].update(
                        {
                            "finished_at": _utc_now(),
                            "latency_seconds": (
                                time.perf_counter() - execution_started_monotonic
                            ),
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    steps.append(record)
                    log(record)
                    raise
                execution_latency = time.perf_counter() - execution_started_monotonic
                record["executed"] = True
                record["mapped_action"] = mapped
                record["layers"]["L3_execution"] = {
                    "attempted": True,
                    "completed": True,
                    "started_at": execution_started_utc,
                    "finished_at": _utc_now(),
                    "latency_seconds": execution_latency,
                    "mapped_action": mapped,
                }
                after_state = env.get_state(wait_to_stabilize=True)
                pending_state = after_state
                after = _audit_snapshot(
                    env=env,
                    state=after_state,
                    episode_dir=episode_dir,
                    label=f"step_{step_index:03d}_after",
                )
                transition = _pixel_transition(before["pixels"], after["pixels"])
                before_activity = before["foreground"].get("activity")
                after_activity = after["foreground"].get("activity")
                transition.update(
                    {
                        "before_activity": before_activity,
                        "after_activity": after_activity,
                        "activity_changed": before_activity != after_activity,
                        "ui_sha_changed": before["ui_sha256"] != after["ui_sha256"],
                    }
                )
                record["after"] = _snapshot_record(after)
                record["transition"] = transition
                record["layers"]["L4_transition_progress"] = {
                    "observed": True,
                    **transition,
                }
                gate_observation: dict[str, Any] | None = None
                if self.source_document_coverage_gate is not None:
                    gate_observation = self.source_document_coverage_gate.observe(
                        before_activity=before_activity,
                        executed_action=canonical_action,
                        transition=transition,
                    )
                    record["source_document_coverage_gate"].update(
                        {
                            "observation": gate_observation,
                            "state_after_execution": (
                                self.source_document_coverage_gate.audit_record()
                            ),
                        }
                    )
                committed_summary, attestation_applied, attestation_reason = (
                    self._committed_history_summary(
                        model_action_summary=decision.action_summary,
                        canonical_action=canonical_action,
                        transition=transition,
                    )
                )
                if gate_decision and gate_decision.get("overridden"):
                    committed_summary = (
                        "Coverage gate blocked the model's proposed source-document "
                        "exit or non-scan action and executed one forward vertical "
                        "swipe. Source coverage remains open until a forward swipe "
                        "produces no new page evidence."
                    )
                    attestation_applied = True
                    attestation_reason = "source_document_coverage_override"
                record["history_commit"] = {
                    "policy": self.history_policy,
                    "model_action_summary": decision.action_summary,
                    "committed_history_summary": committed_summary,
                    "attestation_applied": attestation_applied,
                    "attestation_reason": attestation_reason,
                    "threshold_changed_pixel_fraction_gt_5": 0.001,
                }
                history.append(committed_summary)
                record["history_after"] = list(history)
                steps.append(record)
                log(record)
                if (
                    self.stop_after_markor_source_exit
                    and before_activity
                    == "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"
                    and after_activity
                    != "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"
                ):
                    termination_reason = "source_stage_exit"
                    break
                if (
                    decision.terminal_status == "answer"
                    and not (gate_decision and gate_decision.get("overridden"))
                ):
                    claimed_status = "answer"
                    termination_reason = "model_answer"
                    break

            if termination_reason == "source_stage_exit":
                log(
                    {
                        "event": "evaluator_skipped",
                        "reason": "bounded_source_capture_diagnostic",
                        "visible_to_agent": False,
                    }
                )
            else:
                evaluator_reward = float(task.is_successful(env))
                log(
                    {
                        "event": "evaluator_result",
                        "reward": evaluator_reward,
                        "visible_to_agent": False,
                        "model_claimed_status": claimed_status,
                    }
                )
        except Exception as exc:
            termination_reason = "infrastructure_or_controller_error"
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            log({"event": "episode_error", "error": error})
        finally:
            if task_initialized:
                try:
                    task.tear_down(env)
                    log({"event": "task_torn_down"})
                except Exception as exc:
                    log(
                        {
                            "event": "teardown_error",
                            "error": {"type": type(exc).__name__, "message": str(exc)},
                        }
                    )
            try:
                env.reset(go_home=True)
                log({"event": "post_episode_reset"})
            except Exception as exc:
                log(
                    {
                        "event": "reset_error",
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    }
                )

        summary = {
            "episode_id": episode_id,
            "baseline": "qwen3_vl_32b_official_public_recipe_port",
            "task_name": str(task.name),
            "task_goal": effective_goal,
            "seed": seed,
            "run_metadata": self.run_metadata,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "termination_reason": termination_reason,
            "model_claimed_status": claimed_status,
            "evaluator_reward": evaluator_reward,
            "success": evaluator_reward == 1.0,
            "step_count": len(steps),
            "executed_action_count": sum(int(item["executed"]) for item in steps),
            "model_call_count": len(steps),
            "error": error,
            "layers": {
                "L0_runtime": {
                    "episode_error": error,
                    "all_model_calls_returned": all(
                        item.get("layers", {})
                        .get("L0_runtime", {})
                        .get("model_call_returned", False)
                        for item in steps
                    ),
                },
                "L1_perception_grounding": {
                    "evidence": "screenshots plus hidden accessibility audit artifacts"
                },
                "L2_protocol_coordinate": {
                    "all_outputs_parse_valid": all(
                        item.get("layers", {})
                        .get("L2_protocol_coordinate", {})
                        .get("parse_valid", False)
                        for item in steps
                    ),
                },
                "L3_execution": {
                    "executed_action_count": sum(int(item["executed"]) for item in steps)
                },
                "L4_transition_progress": {
                    "observed_transition_count": sum(
                        int(
                            item.get("layers", {})
                            .get("L4_transition_progress", {})
                            .get("observed", False)
                        )
                        for item in steps
                    )
                },
                "L5_completion_evaluator": {
                    "model_claimed_status": claimed_status,
                    "evaluator_reward": evaluator_reward,
                    "evaluator_visible_to_model": False,
                    "success": evaluator_reward == 1.0,
                },
            },
            "steps": steps,
            "source_document_coverage_gate": (
                self.source_document_coverage_gate.audit_record()
                if self.source_document_coverage_gate is not None
                else None
            ),
        }
        _write_json(episode_dir / "episode.json", summary)
        log(
            {
                "event": "episode_complete",
                "success": summary["success"],
                "termination_reason": termination_reason,
            }
        )
        return summary
