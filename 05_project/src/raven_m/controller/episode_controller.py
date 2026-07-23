"""Thin, memory-free B0 observe-act-evaluate controller."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import html
import json
from pathlib import Path
import traceback
from typing import Any

from PIL import Image

from raven_m.actions.schema import ActionValidationError, parse_action_response
from raven_m.env.androidworld_adapter import AndroidWorldAdapter
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
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls
        self.adapter = adapter or AndroidWorldAdapter()

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
    ) -> str:
        return "\n".join(
            [
                f"TASK: {goal}",
                f"STEP/BUDGET: {step + 1}/{max_steps}; "
                f"model calls {model_calls}/{max_model_calls}",
                f"PREVIOUS_ACTION_AND_OBSERVED_OUTCOME: {previous_outcome}",
                "MEMORY_CONTEXT: []",
                "CURRENT_SCREENSHOT: attached image",
                "Return one action.v1 JSON object now.",
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
    ) -> tuple[dict[str, Any], list[ModelCall], dict[str, Any]]:
        if model_call_count >= self.max_model_calls:
            raise RuntimeError("Model-call budget exhausted.")
        initial = self.client.generate(
            image_path=image_path,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"step_{step:03d}_initial",
        )
        calls = [initial]
        try:
            parsed = parse_action_response(initial.content)
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
            )
            calls.append(repaired)
            parsed = parse_action_response(repaired.content)
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
    ) -> dict[str, Any]:
        logger = EpisodeLogger(episode_dir)
        started = _utc_now()
        steps: list[dict[str, Any]] = []
        model_call_count = 0
        previous_outcome = "none; this is the first observation"
        termination_reason = "max_steps"
        evaluator_reward: float | None = None
        task_initialized = False
        error_record: dict[str, Any] | None = None

        logger.append(
            {
                "event": "episode_start",
                "episode_id": episode_id,
                "protocol": "excluded_protocol_dry_run",
                "variant": "B0",
                "seed": seed,
                "task_name": task.name,
                "task_goal": str(task.goal),
                "task_params": task.params,
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
                state_before = env.get_state(wait_to_stabilize=True)
                height, width = state_before.pixels.shape[:2]
                before_path = logger.save_screenshot(
                    state_before.pixels,
                    f"step_{step:03d}_before.png",
                )
                user_prompt = self._user_prompt(
                    goal=str(task.goal),
                    step=step,
                    max_steps=self.max_steps,
                    model_calls=model_call_count,
                    max_model_calls=self.max_model_calls,
                    screen_width=width,
                    screen_height=height,
                    previous_outcome=previous_outcome,
                )
                decision, calls, parse_meta = self._call_and_parse(
                    image_path=before_path,
                    user_prompt=user_prompt,
                    episode_id=episode_id,
                    step=step,
                    model_call_count=model_call_count,
                )
                model_call_count += len(calls)
                step_record: dict[str, Any] = {
                    "event": "step",
                    "step": step,
                    "before_screenshot": before_path.name,
                    "before_screenshot_sha256": _sha256_file(before_path),
                    "screen_size": [width, height],
                    "user_prompt": user_prompt,
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
                self.adapter.execute(env, mapped)
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
        decision_count = sum(1 for step in steps if "parse" in step)
        executed_count = sum(int(step.get("executed", False)) for step in steps)
        if error_record:
            failure_code = "INFRA_OR_CONTROLLER"
        elif evaluator_reward == 1.0:
            failure_code = None
        elif termination_reason == "model_done":
            failure_code = "PREMATURE_COMPLETION"
        elif termination_reason == "model_fail":
            failure_code = "MODEL_DECLARED_INFEASIBLE"
        else:
            failure_code = "TASK_UNSUCCESSFUL_AT_BUDGET"

        summary = {
            "episode_id": episode_id,
            "protocol": "excluded_protocol_dry_run",
            "variant": "B0",
            "started_at": started,
            "finished_at": _utc_now(),
            "task_name": task.name,
            "task_goal": str(task.goal),
            "task_params": task.params,
            "seed": seed,
            "termination_reason": termination_reason,
            "evaluator_reward": evaluator_reward,
            "success": evaluator_reward == 1.0,
            "failure_code": failure_code,
            "decision_count": decision_count,
            "executed_action_count": executed_count,
            "model_call_count": model_call_count,
            "first_pass_parse_count": first_pass_count,
            "first_pass_parse_rate": (
                first_pass_count / decision_count if decision_count else None
            ),
            "error": error_record,
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
