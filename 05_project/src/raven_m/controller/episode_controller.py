"""Thin, memory-free B0 observe-act-evaluate controller."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict, is_dataclass
from enum import Enum
from hashlib import sha256
import html
import json
from pathlib import Path
import traceback
from typing import Any

from PIL import Image

from raven_m.actions.schema import ActionValidationError, parse_action_response
from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.history.policies import (
    HistoryEntry,
    HistoryPolicy,
)
from raven_m.models.transformers_client import ModelCall, TransformersClient


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
    ) -> None:
        super().__init__(repair_error)
        self.calls = calls
        self.initial_error = initial_error
        self.repair_error = repair_error


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
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls
        self.adapter = adapter or AndroidWorldAdapter()
        self.history_policy = history_policy or HistoryPolicy()
        self.action_schema_path = action_schema_path

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
    ) -> str:
        example_pixel_y = min(438, screen_height - 1)
        example_normalized_y = example_pixel_y / max(screen_height - 1, 1)
        return "\n".join(
            [
                f"TASK: {goal}",
                f"STEP/BUDGET: {step + 1}/{max_steps}; "
                f"model calls {model_calls}/{max_model_calls}",
                f"PREVIOUS_ACTION_AND_OBSERVED_OUTCOME: {previous_outcome}",
                f"MEMORY_CONTEXT: {memory_context}",
                "TEXT_SAFETY: type_text may contain only a value explicitly "
                "requested by TASK.",
                f"CURRENT_SCREENSHOT: attached image; size "
                f"{screen_width}x{screen_height} pixels.",
                "COORDINATE_CHECK: JSON coordinates must be normalized decimals "
                "in [0,1], never pixels. For this image, pixel "
                f"y={example_pixel_y} becomes y={example_normalized_y:.4f}.",
                "COMPLETION_CHECK: a visible Save/Move/Done button is not proof "
                "of completion; execute it and observe the result first.",
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
    ) -> str:
        return (
            original_prompt
            + "\n\nYour previous response was invalid. Correct its format only "
            "while choosing the action from the same screenshot.\n"
            f"VALIDATION_ERROR: {error}\n"
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
            "If a coordinate is above 1, convert it from pixels using "
            "CURRENT_SCREENSHOT size. If text is too long, shorten it below "
            "160 characters. status must be continue/done/fail; wait is an "
            "action type inside status=continue.\n"
            "Return exactly one strict JSON object and no surrounding text."
        )

    def _call_and_parse(
        self,
        *,
        image_path: Path,
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
        try:
            parse_kwargs = (
                {"schema_path": self.action_schema_path}
                if self.action_schema_path
                else {}
            )
            parsed = parse_action_response(initial.content, **parse_kwargs)
            self.history_policy.validate_decision(parsed.decision)
            return (
                parsed.decision,
                calls,
                {
                    "first_pass": parsed.first_pass,
                    "extraction_used": parsed.extraction_used,
                    "model_repair_used": False,
                    "schema_sha256": parsed.schema_sha256,
                },
            )
        except ActionValidationError as initial_error:
            if model_call_count + 1 >= self.max_model_calls:
                raise
            repair_prompt = self._repair_prompt(
                user_prompt,
                initial.content,
                str(initial_error),
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
                parsed = parse_action_response(repaired.content, **parse_kwargs)
                self.history_policy.validate_decision(parsed.decision)
            except ActionValidationError as repair_error:
                raise ModelOutputInvalid(
                    calls=calls,
                    initial_error=str(initial_error),
                    repair_error=str(repair_error),
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
        task_params = _json_safe(task.params)
        self.history_policy.reset(
            episode_dir=episode_dir,
            goal=str(task.goal),
            episode_id=episode_id,
            task_id=task.name,
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
                "task_goal": str(task.goal),
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
            logger.append({"event": "task_initialized"})

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
                state_before = env.get_state(wait_to_stabilize=True)
                height, width = state_before.pixels.shape[:2]
                before_path = logger.save_screenshot(
                    state_before.pixels,
                    f"step_{step:03d}_before.png",
                )
                history_context = self.history_policy.context()
                evidence_outcome = previous_outcome
                user_prompt = self._user_prompt(
                    goal=str(task.goal),
                    step=step,
                    max_steps=self.max_steps,
                    model_calls=model_call_count,
                    max_model_calls=self.max_model_calls,
                    screen_width=width,
                    screen_height=height,
                    previous_outcome=previous_outcome,
                    memory_context=history_context.rendered,
                )
                try:
                    decision, calls, parse_meta = self._call_and_parse(
                        image_path=before_path,
                        user_prompt=user_prompt,
                        episode_id=episode_id,
                        step=step,
                        model_call_count=model_call_count,
                        context_images=history_context.images,
                    )
                except ModelOutputInvalid as exc:
                    model_call_count += len(exc.calls)
                    executor_model_call_count += len(exc.calls)
                    termination_reason = "model_output_invalid_after_repair"
                    model_output_error = {
                        "type": "ActionValidationError",
                        "initial_validation_error": exc.initial_error,
                        "repair_validation_error": exc.repair_error,
                    }
                    step_record = {
                        "event": "step",
                        "step": step,
                        "before_screenshot": before_path.name,
                        "before_screenshot_sha256": _sha256_file(before_path),
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
                executor_model_call_count += len(calls)
                parse_meta["valid_after_one_repair"] = True
                step_record: dict[str, Any] = {
                    "event": "step",
                    "step": step,
                    "before_screenshot": before_path.name,
                    "before_screenshot_sha256": _sha256_file(before_path),
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
                }

                if decision["status"] != "continue":
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
                state_after = env.get_state(wait_to_stabilize=True)
                after_path = logger.save_screenshot(
                    state_after.pixels,
                    f"step_{step:03d}_after.png",
                )
                before_sha = step_record["before_screenshot_sha256"]
                after_sha = _sha256_file(after_path)
                changed = before_sha != after_sha
                step_record.update(
                    {
                        "executed": True,
                        "mapped_action": mapped.audit_record(),
                        "after_screenshot": after_path.name,
                        "after_screenshot_sha256": after_sha,
                        "screenshot_changed": changed,
                    }
                )
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
                        before_screenshot_path=before_path,
                        before_screenshot_sha256=before_sha,
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
            "task_goal": str(task.goal),
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
            "first_pass_parse_count": first_pass_count,
            "first_pass_parse_rate": (
                first_pass_count / decision_attempt_count
                if decision_attempt_count
                else None
            ),
            "error": error_record,
            "model_output_error": model_output_error,
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
