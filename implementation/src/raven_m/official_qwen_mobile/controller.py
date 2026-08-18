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
from .working_memory import ActionWorkingMemory, append_working_memory
from .progress_memory import RepeatedNoProgressGuard, VerifiedProgressMemory
from .a345_memory import (
    FrozenWorkflowMemory,
    OnlinePageGraphMemory,
    ProactiveFoldedContextMemory,
)


EpisodeMemory = (
    ActionWorkingMemory
    | VerifiedProgressMemory
    | ProactiveFoldedContextMemory
    | FrozenWorkflowMemory
    | OnlinePageGraphMemory
)


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
        "pixel_shape": list(pixels.shape),
        "pixel_dtype": pixels.dtype.str,
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
        working_memory: EpisodeMemory | None = None,
        recovery_policy: Any | None = None,
        answer_consistency_guard: Any | None = None,
        cost_guard: RepeatedNoProgressGuard | None = None,
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
        self.working_memory = working_memory
        self.recovery_policy = recovery_policy
        self.answer_consistency_guard = answer_consistency_guard
        self.cost_guard = cost_guard

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

    def _map_action(
        self,
        action: dict[str, Any],
        *,
        screen_width: int,
        screen_height: int,
    ) -> tuple[Any | None, dict[str, Any]]:
        if action["type"] == "press_recents":
            return None, {
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
        return mapped, mapped.audit_record()

    def _execute_mapped(
        self,
        env: Any,
        *,
        mapped_object: Any | None,
        mapped_record: dict[str, Any],
    ) -> None:
        if mapped_record["canonical"]["type"] == "press_recents":
            self._press_recents(env)
            return
        if mapped_object is None:
            raise RuntimeError("Mapped Android action object is missing.")
        self.adapter.execute(env, mapped_object)

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
        auxiliary_model_call_attempts: list[dict[str, Any]] = []
        recovery_detector_cpu_seconds = 0.0
        recovery_projection_cpu_seconds = 0.0
        task_initialized = False
        termination_reason = "max_steps"
        claimed_status: str | None = None
        evaluator_reward: float | None = None
        error: dict[str, Any] | None = None
        lifecycle_errors: list[dict[str, Any]] = []

        episode_start_event = {
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
            "memory_mechanism": (
                self.working_memory.audit_record()
                if self.working_memory is not None
                else None
            ),
            "cost_guard": (
                self.cost_guard.audit_record()
                if self.cost_guard is not None
                else None
            ),
        }
        if self.recovery_policy is not None:
            episode_start_event["recovery_mechanism"] = (
                self.recovery_policy.audit_record()
            )
        if self.answer_consistency_guard is not None:
            episode_start_event["answer_consistency_guard"] = (
                self.answer_consistency_guard.audit_record()
            )
        log(episode_start_event)
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
                recovery_step: dict[str, Any] | None = None
                recovery_text = ""
                recovery_injection: dict[str, Any] | None = None
                auxiliary_attempt: dict[str, Any] | None = None
                if self.recovery_policy is not None:
                    recovery_step = {
                        "auxiliary_call_attempt_index": None,
                        "normal_injection": None,
                    }
                    if hasattr(self.recovery_policy, "prepare_direct_injection"):
                        direct = self.recovery_policy.prepare_direct_injection(
                            context={
                                "request_step": step_index,
                                "goal": effective_goal,
                                "recent_prior_executed_responses": [
                                    {
                                        "source_step": int(prior.get("step")),
                                        "thought": str((prior.get("decision") or {}).get("thought") or ""),
                                        "action_summary": str((prior.get("decision") or {}).get("action_summary") or ""),
                                        "response_sha256": str(((prior.get("model_call") or {}).get("response_sha256")) or ""),
                                    }
                                    for prior in steps
                                    if bool(prior.get("executed"))
                                    and isinstance(prior.get("decision"), dict)
                                ][-8:],
                                "r2_memory_audit": (
                                    self.working_memory.audit_record()
                                    if self.working_memory is not None else {}
                                ),
                                "current_screenshot_sha256": before["screenshot_sha256"],
                                "current_screenshot_path": str(screenshot.resolve()),
                            }
                        )
                        if direct is not None:
                            if not isinstance(direct, dict):
                                raise RuntimeError("Direct recovery injection must be a dict")
                            recovery_text = str(direct.get("injection_text") or "")
                            direct_ticket = str(direct.get("ticket_id") or "")
                            if not recovery_text or not direct_ticket:
                                raise RuntimeError("Direct recovery injection is incomplete")
                            recovery_injection = {
                                "ticket_id": direct_ticket,
                                "source_auxiliary_call_id": None,
                                "direct_injection": True,
                                "exact_injected_text": recovery_text,
                                "exact_injected_text_sha256": sha256(recovery_text.encode("utf-8")).hexdigest(),
                                "rendered_chars": len(recovery_text),
                                "source_steps": list(direct.get("source_steps") or []),
                                "source_response_sha256s": list(direct.get("source_response_sha256s") or []),
                            }
                            recovery_step["normal_injection"] = recovery_injection
                    recovery_prepare_started = time.perf_counter()
                    prepared_aux = self.recovery_policy.prepare_aux(
                        context={
                            "request_step": step_index,
                            "executed_action_count": sum(
                                1 for prior in steps if bool(prior.get("executed"))
                            ),
                            "native_max_steps": self.max_steps,
                            "goal": effective_goal,
                            "history": list(history),
                            "recent_action_summaries": list(history[-4:]),
                            "r2_memory_audit": (
                                self.working_memory.audit_record()
                                if self.working_memory is not None
                                else {}
                            ),
                            "current_screenshot_sha256": before["screenshot_sha256"],
                            "current_screenshot_path": str(screenshot.resolve()),
                            "current_pixel_sha256": before["pixel_sha256"],
                        }
                    )
                    recovery_prepare_seconds = (
                        time.perf_counter() - recovery_prepare_started
                    )
                    recovery_projection_cpu_seconds += recovery_prepare_seconds
                    recovery_step["prepare_aux_seconds"] = recovery_prepare_seconds
                    if prepared_aux is not None:
                        if recovery_injection is not None:
                            raise RuntimeError("Policy prepared direct and auxiliary injections together")
                        max_auxiliary_calls = int(
                            getattr(self.recovery_policy, "max_auxiliary_calls", 1)
                        )
                        if sum(
                            1
                            for attempt in auxiliary_model_call_attempts
                            if attempt.get("model_call") is not None
                        ) >= max_auxiliary_calls:
                            raise RuntimeError(
                                "Recovery policy attempted more than one auxiliary model call or exceeded its explicit cap"
                            )
                        if not isinstance(prepared_aux, dict):
                            raise RuntimeError("Recovery auxiliary preparation must be a dict")
                        aux_ticket_id = str(prepared_aux.get("ticket_id") or "")
                        aux_system_prompt = str(
                            prepared_aux.get("system_prompt") or ""
                        )
                        aux_user_prompt = str(prepared_aux.get("user_prompt") or "")
                        if not aux_ticket_id or not aux_system_prompt or not aux_user_prompt:
                            raise RuntimeError(
                                "Recovery auxiliary preparation is missing a required field"
                            )
                        try:
                            aux_max_tokens = int(
                                prepared_aux.get("max_tokens", self.max_tokens)
                            )
                        except (TypeError, ValueError) as exc:
                            raise RuntimeError(
                                "Recovery auxiliary max_tokens is invalid"
                            ) from exc
                        if aux_max_tokens < 1 or aux_max_tokens > self.max_tokens:
                            raise RuntimeError(
                                "Recovery auxiliary max_tokens exceeds controller bounds"
                            )
                        auxiliary_attempt = {
                            "role": "aux_recovery",
                            "request_step": step_index,
                            "preparation": _json_safe(prepared_aux),
                            "model_call": None,
                        }
                        auxiliary_model_call_attempts.append(auxiliary_attempt)
                        recovery_step["auxiliary_call_attempt_index"] = (
                            len(auxiliary_model_call_attempts) - 1
                        )
                        try:
                            auxiliary_call = self.client.generate(
                                image_path=screenshot,
                                system_prompt=aux_system_prompt,
                                user_prompt=aux_user_prompt,
                                episode_id=episode_id,
                                call_label=f"aux_recovery_{step_index:03d}",
                                max_tokens=aux_max_tokens,
                                context_images=[],
                                user_prompt_before_image=True,
                                current_image_label=None,
                                request_timeout_seconds=60.0,
                            )
                        except Exception as exc:
                            auxiliary_attempt["error"] = {
                                "type": type(exc).__name__,
                                "message": str(exc),
                            }
                            if hasattr(self.recovery_policy, "cancel_aux"):
                                auxiliary_attempt["cancellation"] = (
                                    self.recovery_policy.cancel_aux(
                                        aux_ticket_id,
                                        f"model_transport_failure:{type(exc).__name__}",
                                    )
                                )
                            log({"event": "aux_recovery_call", **auxiliary_attempt})
                            raise
                        auxiliary_call_audit = auxiliary_call.audit_record()
                        auxiliary_attempt["model_call"] = auxiliary_call_audit
                        auxiliary_attempt["commit"] = self.recovery_policy.commit_aux(
                            aux_ticket_id, auxiliary_call
                        )
                        aux_commit = auxiliary_attempt["commit"]
                        if not isinstance(aux_commit, dict):
                            raise RuntimeError(
                                "Recovery auxiliary commit must be a dict"
                            )
                        recovery_text = str(aux_commit.get("injection_text") or "")
                        injection_ticket_id = aux_commit.get("injection_ticket_id")
                        if bool(recovery_text) != bool(injection_ticket_id):
                            raise RuntimeError(
                                "Recovery auxiliary text and injection ticket must be paired"
                            )
                        recovery_injection = {
                            "ticket_id": injection_ticket_id,
                            "source_auxiliary_call_id": auxiliary_call.call_id,
                        }
                        recovery_injection["exact_injected_text"] = recovery_text
                        recovery_injection["exact_injected_text_sha256"] = sha256(
                            recovery_text.encode("utf-8")
                        ).hexdigest()
                        recovery_injection["rendered_chars"] = len(recovery_text)
                        recovery_step["normal_injection"] = recovery_injection
                        log({"event": "aux_recovery_call", **auxiliary_attempt})
                memory_read: dict[str, Any] | None = None
                rendered_memory = ""
                prompt_history = history
                if self.working_memory is not None and hasattr(
                    self.working_memory, "prompt_history"
                ):
                    prompt_history = self.working_memory.prompt_history(history)
                base_user_prompt = build_user_prompt(effective_goal, prompt_history)
                if self.working_memory is not None:
                    # The memory receives only the same pixels available to the
                    # policy.  Raw pixels are needed by A5's deterministic
                    # visual fingerprint but are never serialized into memory.
                    rendered_memory, memory_read = self.working_memory.read(
                        context={"before": before, "goal": effective_goal}
                    )
                    if memory_read is not None and rendered_memory:
                        # Causal-audit field for sparse controller-authored
                        # memory arms.  This is exactly the bounded text already
                        # appended to the visible prompt; it is not a new input
                        # or model call.  Keeping this generic prevents a new
                        # prospective arm from being silently omitted merely
                        # because its frozen mechanism ID differs from A10-v1.
                        memory_read["exact_injected_text"] = rendered_memory
                    if memory_read is not None:
                        memory_read["read_step"] = step_index
                        memory_read["resident_history_sha256"] = sha256(
                            json.dumps(
                                history,
                                ensure_ascii=False,
                                sort_keys=False,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest()
                        memory_read["prompt_history_sha256"] = sha256(
                            json.dumps(
                                prompt_history,
                                ensure_ascii=False,
                                sort_keys=False,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest()
                        memory_read["base_user_prompt_sha256"] = sha256(
                            base_user_prompt.encode("utf-8")
                        ).hexdigest()
                try:
                    user_prompt = append_working_memory(
                        base_user_prompt,
                        rendered_memory,
                    )
                    prompt_without_recovery = user_prompt
                    user_prompt = append_working_memory(user_prompt, recovery_text)
                    if recovery_injection is not None and recovery_text:
                        recovery_injection["advice_induced_executor_prompt_tokens"] = (
                            self.recovery_policy.count_advice_prompt_tokens(
                                prompt_without_recovery, user_prompt
                            )
                        )
                except Exception as exc:
                    ticket_id = (memory_read or {}).get("ticket_id")
                    if ticket_id and hasattr(self.working_memory, "cancel_injection"):
                        self.working_memory.cancel_injection(
                            str(ticket_id), f"prompt_build_failure:{type(exc).__name__}"
                        )
                    recovery_ticket_id = (recovery_injection or {}).get("ticket_id")
                    if recovery_ticket_id and hasattr(
                        self.recovery_policy, "cancel_normal_injection"
                    ):
                        cancellation = self.recovery_policy.cancel_normal_injection(
                            str(recovery_ticket_id),
                            f"prompt_build_failure:{type(exc).__name__}",
                        )
                        if auxiliary_attempt is not None:
                            auxiliary_attempt["normal_injection_cancellation"] = cancellation
                    raise
                if memory_read is not None:
                    memory_read["final_user_prompt_sha256"] = sha256(
                        user_prompt.encode("utf-8")
                    ).hexdigest()
                try:
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
                except Exception as exc:
                    ticket_id = (memory_read or {}).get("ticket_id")
                    if ticket_id and hasattr(self.working_memory, "cancel_injection"):
                        self.working_memory.cancel_injection(
                            str(ticket_id),
                            f"model_transport_failure:{type(exc).__name__}",
                        )
                    recovery_ticket_id = (recovery_injection or {}).get("ticket_id")
                    if recovery_ticket_id and hasattr(
                        self.recovery_policy, "cancel_normal_injection"
                    ):
                        cancellation = self.recovery_policy.cancel_normal_injection(
                            str(recovery_ticket_id),
                            f"model_transport_failure:{type(exc).__name__}",
                        )
                        if auxiliary_attempt is not None:
                            auxiliary_attempt["normal_injection_cancellation"] = cancellation
                    raise
                if memory_read is not None:
                    memory_read["transport_confirmation"] = {
                        "model_call_id": call.call_id,
                        "request_sha256": call.request_sha256,
                        "response_sha256": call.response_sha256,
                        "transport_attempts": call.raven_meta.get(
                            "transport_attempts"
                        ),
                    }
                    ticket_id = memory_read.get("ticket_id")
                    if rendered_memory and ticket_id and hasattr(
                        self.working_memory, "commit_injection"
                    ):
                        memory_read["injection_commit"] = (
                            self.working_memory.commit_injection(
                                str(ticket_id),
                                memory_read["final_user_prompt_sha256"],
                            )
                        )
                if recovery_injection is not None:
                    recovery_injection["final_user_prompt_sha256"] = sha256(
                        user_prompt.encode("utf-8")
                    ).hexdigest()
                    recovery_injection["transport_confirmation"] = {
                        "model_call_id": call.call_id,
                        "request_sha256": call.request_sha256,
                        "response_sha256": call.response_sha256,
                        "transport_attempts": call.raven_meta.get(
                            "transport_attempts"
                        ),
                    }
                    recovery_ticket_id = str(
                        recovery_injection.get("ticket_id") or ""
                    )
                    if recovery_text and not recovery_ticket_id:
                        raise RuntimeError(
                            "Recovery normal injection ticket is missing"
                        )
                    if recovery_text:
                        injection_commit = (
                            self.recovery_policy.commit_normal_injection(
                                recovery_ticket_id,
                                recovery_injection["final_user_prompt_sha256"],
                                call,
                            )
                        )
                        if not isinstance(injection_commit, dict):
                            raise RuntimeError(
                                "Recovery normal injection commit must be a dict"
                            )
                        recovery_injection["injection_commit"] = injection_commit
                record: dict[str, Any] = {
                    "event": "step",
                    "step": step_index,
                    "screen_size": [width, height],
                    "before": _snapshot_record(before),
                    "before_screenshot": before["screenshot"],
                    "before_screenshot_sha256": before["screenshot_sha256"],
                    "user_prompt": user_prompt,
                    "history_before": list(history),
                    "memory_read": memory_read,
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
                if recovery_step is not None:
                    record["recovery"] = recovery_step
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
                if self.recovery_policy is not None and hasattr(
                    self.recovery_policy, "review_result_action"
                ):
                    result_action_review = self.recovery_policy.review_result_action(
                        proposed_action=decision.canonical_action,
                        terminal_status=decision.terminal_status,
                        executed_action_count=sum(
                            1 for prior in steps if bool(prior.get("executed"))
                        ),
                        native_max_steps=self.max_steps,
                        remaining_native_decision_slots=(
                            self.max_steps - step_index - 1
                        ),
                        request_step=step_index,
                    )
                    record["late_raw_evidence_review"] = result_action_review
                    if bool(result_action_review.get("blocked")):
                        record["layers"]["L2_protocol_coordinate"] = {
                            "parse_valid": True,
                            "model_canonical_action": decision.canonical_action,
                            "executed_canonical_action": None,
                            "deferred_for_late_raw_evidence_rehydration": True,
                        }
                        record["layers"]["L3_execution"] = {
                            "attempted": False,
                            "completed": False,
                            "blocked_by_late_raw_evidence_rehydration": True,
                        }
                        record["history_commit"] = {
                            "policy": getattr(self.recovery_policy, "system_id", "unknown"),
                            "model_action_summary": decision.action_summary,
                            "committed_history_summary": None,
                            "attestation_applied": False,
                            "controller_guidance_applied": False,
                            "deferred_response_not_committed": True,
                        }
                        record["history_after"] = list(history)
                        steps.append(record)
                        log(record)
                        continue
                if isinstance(self.working_memory, VerifiedProgressMemory):
                    record["progress_parse"] = self.working_memory.record_progress_parse(
                        decision.action_summary
                    )
                elif self.working_memory is not None and hasattr(
                    self.working_memory, "record_protocol"
                ):
                    record["memory_protocol_parse"] = self.working_memory.record_protocol(
                        decision.action_summary
                    )
                canonical_action = decision.canonical_action
                if self.answer_consistency_guard is not None:
                    canonical_action, answer_guard_assessment = (
                        self.answer_consistency_guard.review(
                            proposed_action=canonical_action,
                            action_summary=decision.action_summary,
                        )
                    )
                    record["answer_consistency_guard"] = answer_guard_assessment
                route_guard_assessment: dict[str, Any] | None = None
                if (
                    self.answer_consistency_guard is not None
                    and hasattr(self.answer_consistency_guard, "review_route")
                ):
                    route_guard_assessment = self.answer_consistency_guard.review_route(
                        proposed_action=canonical_action,
                        action_summary=decision.action_summary,
                        memory_read=memory_read,
                        before_pixels=before["pixels"],
                        remaining_native_decision_slots=(
                            self.max_steps - step_index - 1
                        ),
                        executed_action_count=sum(
                            1 for prior in steps if bool(prior.get("executed"))
                        ),
                        native_max_steps=self.max_steps,
                    )
                    record["route_recurrence_consistency_guard"] = (
                        route_guard_assessment
                    )
                terminal_guard_assessment: dict[str, Any] | None = None
                if (
                    self.answer_consistency_guard is not None
                    and hasattr(self.answer_consistency_guard, "review_terminal")
                ):
                    previous_executed_action: dict[str, Any] | None = None
                    for previous_record in reversed(steps):
                        if not bool(previous_record.get("executed")):
                            continue
                        mapped = previous_record.get("mapped_action")
                        if isinstance(mapped, dict) and isinstance(
                            mapped.get("canonical"), dict
                        ):
                            previous_executed_action = dict(mapped["canonical"])
                        break
                    terminal_guard_assessment = (
                        self.answer_consistency_guard.review_terminal(
                            terminal_status=decision.terminal_status,
                            memory_read=memory_read,
                            previous_executed_action=previous_executed_action,
                            remaining_native_decision_slots=(
                                self.max_steps - step_index - 1
                            ),
                        )
                    )
                    record["pending_terminal_consistency_guard"] = (
                        terminal_guard_assessment
                    )
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
                if bool((route_guard_assessment or {}).get("blocked")):
                    guard_message = str(
                        route_guard_assessment.get("history_message") or ""
                    )
                    if not guard_message:
                        raise RuntimeError(
                            "Route-recurrence guard blocked without an audit message"
                        )
                    persist_guard_message = bool(
                        route_guard_assessment.get("persist_history_message", True)
                    )
                    if persist_guard_message:
                        history.append(guard_message)
                    record["layers"]["L3_execution"] = {
                        "attempted": False,
                        "completed": False,
                        "blocked_by_route_recurrence_consistency_guard": True,
                    }
                    record["history_commit"] = {
                        "policy": "sys_nag_v4_route_recurrence_guard",
                        "model_action_summary": decision.action_summary,
                        "committed_history_summary": (
                            guard_message if persist_guard_message else None
                        ),
                        "transient_controller_event": (
                            None if persist_guard_message else guard_message
                        ),
                        "attestation_applied": False,
                        "controller_guidance_applied": True,
                        "attestation_reason": None,
                    }
                    record["history_after"] = list(history)
                    steps.append(record)
                    log(record)
                    continue
                if bool((terminal_guard_assessment or {}).get("blocked")):
                    guard_message = str(
                        terminal_guard_assessment.get("history_message") or ""
                    )
                    if not guard_message:
                        raise RuntimeError(
                            "Pending-terminal guard blocked without an audit message"
                        )
                    history.append(guard_message)
                    record["layers"]["L3_execution"] = {
                        "attempted": False,
                        "completed": False,
                        "blocked_by_pending_terminal_consistency_guard": True,
                    }
                    record["layers"]["L5_completion_evaluator"][
                        "terminal_claim"
                    ] = decision.terminal_status
                    record["history_commit"] = {
                        "policy": "sys_nag_v3_pending_terminal_guard",
                        "model_action_summary": decision.action_summary,
                        "committed_history_summary": guard_message,
                        "attestation_applied": True,
                        "attestation_reason": (
                            "pending_survived_wait_before_success_termination"
                        ),
                    }
                    record["history_after"] = list(history)
                    steps.append(record)
                    log(record)
                    continue
                if canonical_action is None:
                    claimed_status = decision.terminal_status
                    termination_reason = f"model_terminate_{claimed_status}"
                    record["layers"]["L5_completion_evaluator"]["terminal_claim"] = (
                        claimed_status
                    )
                    steps.append(record)
                    log(record)
                    break
                mapped_object, mapped_record = self._map_action(
                    canonical_action,
                    screen_width=width,
                    screen_height=height,
                )
                record["mapped_action_proposal"] = mapped_record
                guard_assessment: dict[str, Any] | None = None
                if self.cost_guard is not None:
                    guard_assessment = self.cost_guard.assess(
                        before=before,
                        mapped_action=mapped_record,
                    )
                    record["cost_guard_assessment"] = guard_assessment
                    if guard_assessment.get("blocked"):
                        guard_block = self.cost_guard.record_block(guard_assessment)
                        record["cost_guard_block"] = guard_block
                        record["layers"]["L3_execution"] = {
                            "attempted": False,
                            "completed": False,
                            "blocked_by_cost_guard": True,
                        }
                        guard_history = str(guard_block["message"])
                        if guard_block.get("warning_emitted"):
                            history.append(guard_history)
                        record["history_commit"] = {
                            "policy": "a2_cost_guard_block_message",
                            "model_action_summary": decision.action_summary,
                            "committed_history_summary": guard_history,
                            "attestation_applied": bool(
                                guard_block.get("warning_emitted")
                            ),
                            "attestation_reason": "repeated_no_progress_cost_guard",
                        }
                        record["history_after"] = list(history)
                        steps.append(record)
                        log(record)
                        if guard_block.get("cost_stop"):
                            termination_reason = "a2_cost_guard_stop"
                            break
                        continue
                execution_started_utc = _utc_now()
                execution_started_monotonic = time.perf_counter()
                record["layers"]["L3_execution"] = {
                    "attempted": True,
                    "completed": False,
                    "started_at": execution_started_utc,
                }
                try:
                    self._execute_mapped(
                        env,
                        mapped_object=mapped_object,
                        mapped_record=mapped_record,
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
                record["mapped_action"] = mapped_record
                record["layers"]["L3_execution"] = {
                    "attempted": True,
                    "completed": True,
                    "started_at": execution_started_utc,
                    "finished_at": _utc_now(),
                    "latency_seconds": execution_latency,
                    "mapped_action": mapped_record,
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
                if self.cost_guard is not None:
                    record["cost_guard_observation"] = self.cost_guard.observe(
                        before=before,
                        after=after,
                        mapped_action=mapped_record,
                        transition=transition,
                    )
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
                if isinstance(self.working_memory, VerifiedProgressMemory):
                    committed_summary = self.working_memory.history_summary(
                        decision.action_summary
                    )
                    attestation_applied = True
                    attestation_reason = "a2_progress_prefix_stored_once_not_duplicated_in_history"
                elif self.working_memory is not None and hasattr(
                    self.working_memory, "history_summary"
                ):
                    committed_summary = self.working_memory.history_summary(
                        decision.action_summary
                    )
                    attestation_applied = (
                        committed_summary != decision.action_summary
                    )
                    attestation_reason = (
                        "memory_prefix_stored_once_not_duplicated_in_action_history"
                        if attestation_applied
                        else None
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
                if self.working_memory is not None:
                    if isinstance(self.working_memory, VerifiedProgressMemory):
                        record["memory_write"] = self.working_memory.observe_step(
                            source_step=step_index,
                            action_summary=decision.action_summary,
                            canonical_action=canonical_action,
                            transition=transition,
                            source_call_id=call.call_id,
                            source_response_sha256=call.response_sha256,
                            source_screenshot_sha256=str(before["screenshot_sha256"]),
                        )
                    elif hasattr(self.working_memory, "observe_step"):
                        if (
                            getattr(self.working_memory, "mechanism_id", "")
                            == "a1r3v3_one_shot_controller_nonprogress_receipt_v1"
                        ):
                            record["memory_write"] = self.working_memory.observe_step(
                                source_step=step_index,
                                action_summary=decision.action_summary,
                                canonical_action=canonical_action,
                                transition={
                                    "same_shape": transition.get("same_shape"),
                                    "changed_pixel_fraction_gt_5": transition.get(
                                        "changed_pixel_fraction_gt_5"
                                    ),
                                },
                                source_call_id=call.call_id,
                                source_response_sha256=call.response_sha256,
                                source_screenshot_sha256=str(
                                    before["screenshot_sha256"]
                                ),
                                source_after_screenshot_sha256=str(
                                    after["screenshot_sha256"]
                                ),
                            )
                        else:
                            record["memory_write"] = self.working_memory.observe_step(
                                source_step=step_index,
                                action_summary=decision.action_summary,
                                canonical_action=canonical_action,
                                transition=transition,
                                before=before,
                                after=after,
                                source_call_id=call.call_id,
                                source_response_sha256=call.response_sha256,
                                source_screenshot_sha256=str(
                                    before["screenshot_sha256"]
                                ),
                            )
                    else:
                        record["memory_write"] = self.working_memory.write(
                            source_step=step_index,
                            action_summary=decision.action_summary,
                            source_call_id=call.call_id,
                            source_response_sha256=call.response_sha256,
                            source_screenshot_sha256=str(before["screenshot_sha256"]),
                        )
                    if hasattr(self.working_memory, "write_model_response"):
                        record["memory_response_write"] = (
                            self.working_memory.write_model_response(
                                source_step=step_index,
                                model_response=call.content,
                                action_summary=decision.action_summary,
                                source_call_id=call.call_id,
                                source_response_sha256=call.response_sha256,
                                source_screenshot_sha256=str(
                                    before["screenshot_sha256"]
                                ),
                            )
                        )
                if self.recovery_policy is not None:
                    recovery_transition = dict(transition)
                    recovery_transition["remaining_native_decision_slots"] = (
                        self.max_steps - step_index - 1
                    )
                    recovery_observe_started = time.perf_counter()
                    recovery_observation = (
                        self.recovery_policy.observe_transition(
                            source_step=step_index,
                            action_summary=decision.action_summary,
                            canonical_action=canonical_action,
                            # Give the detector isolated copies so it cannot
                            # mutate the environment state reused by the next
                            # normal decision.
                            before_pixels=before["pixels"].copy(),
                            after_pixels=after["pixels"].copy(),
                            transition=recovery_transition,
                            source_call_id=call.call_id,
                            source_response_sha256=call.response_sha256,
                            source_before_screenshot_sha256=str(
                                before["screenshot_sha256"]
                            ),
                            source_after_screenshot_sha256=str(
                                after["screenshot_sha256"]
                            ),
                        )
                    )
                    recovery_detector_cpu_seconds += (
                        time.perf_counter() - recovery_observe_started
                    )
                    if not isinstance(recovery_observation, dict):
                        raise RuntimeError(
                            "Recovery transition observation must be a dict"
                        )
                    record["recovery_observation"] = recovery_observation
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
                    lifecycle_errors.append(
                        {"stage": "tear_down", "type": type(exc).__name__, "message": str(exc)}
                    )
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
                lifecycle_errors.append(
                    {"stage": "post_episode_reset", "type": type(exc).__name__, "message": str(exc)}
                )
                log(
                    {
                        "event": "reset_error",
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    }
                )

        recovery_episode_close: Any | None = None
        if self.recovery_policy is not None and hasattr(
            self.recovery_policy, "close_episode"
        ):
            try:
                recovery_episode_close = self.recovery_policy.close_episode(
                    termination_reason
                )
            except Exception as exc:
                termination_reason = "infrastructure_or_controller_error"
                if error is None:
                    error = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                log({"event": "recovery_close_error", "error": error})

        successful_auxiliary_calls = sum(
            int(attempt.get("model_call") is not None)
            for attempt in auxiliary_model_call_attempts
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
            "lifecycle_errors": lifecycle_errors,
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
            "memory_mechanism": (
                self.working_memory.audit_record()
                if self.working_memory is not None
                else None
            ),
            "cost_guard": (
                self.cost_guard.audit_record()
                if self.cost_guard is not None
                else None
            ),
            "answer_consistency_guard": (
                self.answer_consistency_guard.audit_record()
                if self.answer_consistency_guard is not None
                else None
            ),
        }
        if self.recovery_policy is not None:
            summary.update(
                {
                    "normal_decision_call_count": len(steps),
                    "aux_recovery_call_count": successful_auxiliary_calls,
                    "model_call_count": len(steps) + successful_auxiliary_calls,
                    "model_call_breakdown": {
                        "normal_decision": len(steps),
                        "aux_recovery": successful_auxiliary_calls,
                        "total": len(steps) + successful_auxiliary_calls,
                    },
                    "auxiliary_model_call_attempts": auxiliary_model_call_attempts,
                    "recovery_episode_close": recovery_episode_close,
                    "recovery_mechanism": self.recovery_policy.audit_record(),
                    "recovery_detector_cpu_seconds": recovery_detector_cpu_seconds,
                    "recovery_projection_cpu_seconds": recovery_projection_cpu_seconds,
                }
            )
        _write_json(episode_dir / "episode.json", summary)
        log(
            {
                "event": "episode_complete",
                "success": summary["success"],
                "termination_reason": termination_reason,
            }
        )
        return summary
