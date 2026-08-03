"""Shared three-arm controller for the EEST-AC v0.2 blind smoke."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import time
import traceback
from typing import Any

from PIL import Image

from raven_m.eest_ac.compiler_v0_2 import ContextCompilerV02
from raven_m.eest_ac.completion_v0_2 import CompletionPolicyV02
from raven_m.eest_ac.models import EvidenceScope, EvidenceSource
from raven_m.eest_ac.observation_v0_2 import (
    CapturedObservation,
    ObservationStabilizer,
)
from raven_m.eest_ac.recovery_v0_2 import RecoveryRegistryV02
from raven_m.eest_ac.risk import RiskDetector
from raven_m.eest_ac.schema import EestDecisionValidationError, parse_eest_decision
from raven_m.eest_ac.state import EvidenceLedger, EventLog, GoalLedger, TaskLiteralStore
from raven_m.eest_ac.task_roles import (
    TaskRoleFrame,
    TaskRoleParser,
    verify_exact_spans,
)
from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.models.transformers_client import ModelCall, TransformersClient


ONLINE_ARMS_V02 = frozenset({"B3", "B3_MATCH", "M_SLOTS"})
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_V02 = PROJECT_ROOT / "schemas/eest_ac_decision.v0_2.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical_json(value) + "\n")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Image.Image):
        return {"mode": value.mode, "size": list(value.size), "pixel_sha256": sha256(value.tobytes()).hexdigest()}
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


def _parse_summary(raw: str) -> str:
    value = json.loads(raw.strip())
    if set(value) != {"summary"} or not isinstance(value["summary"], str):
        raise ValueError("Summary must contain exactly one string field.")
    summary = value["summary"].strip()
    if not summary or len(summary) > 1200:
        raise ValueError("Summary is empty or too long.")
    return summary


def _failure_class(exc: Exception) -> str:
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return "infrastructure"
    text = f"{type(exc).__name__} {exc}".casefold()
    if any(marker in text for marker in ("grpc", "device offline", "adb server", "connection refused")):
        return "infrastructure"
    return "model_or_controller_invalid"


class EestAcV02Controller:
    """One controller and policy stack shared by all v0.2 online arms."""

    def __init__(
        self,
        *,
        client: TransformersClient,
        executor_prompt: str,
        summary_prompt: str,
        arm: str,
        max_environment_actions: int,
        max_model_calls: int,
        max_new_tokens: int = 256,
        context_cap_tokens: int = 8192,
        task_role_frame: TaskRoleFrame | None = None,
        adapter: AndroidWorldAdapter | None = None,
        stabilizer: ObservationStabilizer | None = None,
        completion_policy: CompletionPolicyV02 | None = None,
        compiler: ContextCompilerV02 | None = None,
        schema_path: Path = DEFAULT_SCHEMA_V02,
        periodic_summary_actions: int = 5,
    ) -> None:
        if arm not in ONLINE_ARMS_V02:
            raise ValueError(f"Arm is not online in EEST-AC v0.2: {arm}")
        if max_environment_actions < 1 or max_model_calls < 1:
            raise ValueError("Episode budgets must be positive.")
        if max_new_tokens != 256:
            raise ValueError("v0.2 freezes max_new_tokens at 256.")
        self.client = client
        self.executor_prompt = executor_prompt
        self.summary_prompt = summary_prompt
        self.arm = arm
        self.max_environment_actions = max_environment_actions
        self.max_model_calls = max_model_calls
        self.max_new_tokens = max_new_tokens
        self.context_cap_tokens = context_cap_tokens
        self.task_role_frame = task_role_frame
        self.adapter = adapter or AndroidWorldAdapter()
        self.stabilizer = stabilizer or ObservationStabilizer()
        self.completion_policy = completion_policy or CompletionPolicyV02()
        self.compiler = compiler or ContextCompilerV02()
        self.schema_path = schema_path
        self.periodic_summary_actions = periodic_summary_actions
        self.risk_detector = RiskDetector()

    @property
    def uses_slots(self) -> bool:
        return self.arm == "M_SLOTS"

    def _record_call(
        self,
        *,
        call: ModelCall,
        role: str,
        calls: list[dict[str, Any]],
        calls_path: Path,
    ) -> None:
        record = {"role": role, **call.audit_record()}
        calls.append(record)
        _append_jsonl(calls_path, record)
        prompt_tokens = int(call.usage.get("prompt_tokens", 0))
        if prompt_tokens + self.max_new_tokens > self.context_cap_tokens:
            raise RuntimeError(
                f"CONTEXT_CAP_EXCEEDED:{prompt_tokens}+{self.max_new_tokens}>{self.context_cap_tokens}"
            )

    def _generate(
        self,
        *,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        episode_id: str,
        call_label: str,
        role: str,
        calls: list[dict[str, Any]],
        calls_path: Path,
        attempts: list[dict[str, Any]],
    ) -> ModelCall:
        if len(calls) >= self.max_model_calls:
            raise RuntimeError("MODEL_CALL_BUDGET_EXHAUSTED")
        attempt = {"label": call_label, "role": role, "started_at_utc": _utc_now(), "completed": False}
        attempts.append(attempt)
        try:
            call = self.client.generate(
                image_path=image_path,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                episode_id=episode_id,
                call_label=call_label,
                max_tokens=self.max_new_tokens,
            )
            self._record_call(call=call, role=role, calls=calls, calls_path=calls_path)
            attempt["completed"] = True
            attempt["call_id"] = call.call_id
            return call
        except Exception as exc:
            attempt["error_type"] = type(exc).__name__
            attempt["error"] = str(exc)
            raise

    def _decision(
        self,
        *,
        image_path: Path,
        user_prompt: str,
        episode_id: str,
        decision_index: int,
        calls: list[dict[str, Any]],
        calls_path: Path,
        attempts: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        initial = self._generate(
            image_path=image_path,
            system_prompt=self.executor_prompt,
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"executor_d{decision_index:03d}_initial",
            role="executor",
            calls=calls,
            calls_path=calls_path,
            attempts=attempts,
        )
        try:
            parsed = parse_eest_decision(initial.content, schema_path=self.schema_path)
            return parsed.decision, {
                "first_pass": parsed.first_pass,
                "extraction_used": parsed.extraction_used,
                "schema_sha256": parsed.schema_sha256,
                "repaired": False,
            }
        except EestDecisionValidationError as initial_error:
            if len(calls) >= self.max_model_calls:
                raise
            repair_prompt = "\n".join(
                (
                    user_prompt,
                    "INVALID_JSON_REPAIR. Return only compact v0.2 JSON.",
                    f"ERROR:{str(initial_error)[:500]}",
                    f"OUTPUT:{initial.content[:1600]}",
                )
            )
            repaired = self._generate(
                image_path=image_path,
                system_prompt=self.executor_prompt,
                user_prompt=repair_prompt,
                episode_id=episode_id,
                call_label=f"executor_d{decision_index:03d}_repair",
                role="executor_repair",
                calls=calls,
                calls_path=calls_path,
                attempts=attempts,
            )
            parsed = parse_eest_decision(repaired.content, schema_path=self.schema_path)
            return parsed.decision, {
                "first_pass": False,
                "extraction_used": parsed.extraction_used,
                "schema_sha256": parsed.schema_sha256,
                "repaired": True,
                "initial_error": str(initial_error),
            }

    def _summary_call(
        self,
        *,
        image_path: Path,
        episode_id: str,
        label: str,
        goal: str,
        role_frame: TaskRoleFrame,
        previous_summary: str | None,
        recent_transitions: list[dict[str, Any]],
        candidate: dict[str, Any] | None,
        calls: list[dict[str, Any]],
        calls_path: Path,
        attempts: list[dict[str, Any]],
    ) -> tuple[str | None, dict[str, Any]]:
        prompt = _canonical_json(
            {
                "task": goal,
                "task_roles": role_frame.record(),
                "previous_summary": previous_summary,
                "recent_transitions": recent_transitions[-4:],
                "candidate": candidate,
            }
        )
        call = self._generate(
            image_path=image_path,
            system_prompt=self.summary_prompt,
            user_prompt=prompt,
            episode_id=episode_id,
            call_label=label,
            role="ordinary_summary",
            calls=calls,
            calls_path=calls_path,
            attempts=attempts,
        )
        try:
            return _parse_summary(call.content), {"valid": True, "call_id": call.call_id}
        except (json.JSONDecodeError, ValueError) as exc:
            return previous_summary, {"valid": False, "call_id": call.call_id, "error": str(exc)}

    @staticmethod
    def _trigger(decision: dict[str, Any]) -> dict[str, Any]:
        compatible = {
            "status": decision["status"],
            "action": decision["action"],
            "decision_summary": decision["intent"],
        }
        return asdict(RiskDetector().detect(compatible))

    @staticmethod
    def _prompt(
        *,
        goal: str,
        role_frame: TaskRoleFrame,
        arm: str,
        decision_index: int,
        action_count: int,
        max_actions: int,
        call_count: int,
        max_calls: int,
        previous_outcome: str,
        context: dict[str, Any],
        width: int,
        height: int,
    ) -> str:
        return "\n".join(
            (
                f"IMMUTABLE_TASK:{goal}",
                "TASK_ROLES:" + _canonical_json(role_frame.record()),
                f"ARM:{arm}",
                f"STEP:{decision_index};ACTIONS:{action_count}/{max_actions};CALLS:{call_count}/{max_calls}",
                f"PREVIOUS_OUTCOME:{previous_outcome}",
                "CONTEXT:" + _canonical_json(context),
                f"SCREEN:{width}x{height}",
                "Return compact schema-valid JSON only.",
            )
        )

    @staticmethod
    def _validate_citations(
        *,
        decision: dict[str, Any],
        literals: TaskLiteralStore,
        evidence: EvidenceLedger,
        visible_texts: tuple[str, ...],
    ) -> str | None:
        task_ids = {item.literal_id for item in literals.literals}
        cited = []
        for citation in decision.get("citations", []):
            if citation.startswith("task:"):
                if citation not in task_ids:
                    return f"unknown_task_citation:{citation}"
            else:
                record = evidence.get(citation)
                if record is None:
                    return f"unknown_evidence_citation:{citation}"
                cited.append(record)
        action = decision.get("action")
        if not isinstance(action, dict) or action.get("type") != "type_text":
            return None
        text = str(action.get("text", "")).casefold()
        visible = "\n".join(visible_texts).casefold()
        grounded = literals.contains_exact(str(action.get("text", ""))) or text in visible
        grounded = grounded or any(text == item.value.casefold() or text in item.value.casefold() for item in cited)
        return None if grounded else "typed_text_has_no_allowed_provenance"

    @staticmethod
    def _save_observation(
        observation: CapturedObservation,
        path: Path,
    ) -> None:
        Image.fromarray(observation.state.pixels).save(path)

    def run(
        self,
        *,
        env: Any,
        task: Any,
        episode_id: str,
        episode_dir: Path,
        seed: int,
        study_id: str,
    ) -> dict[str, Any]:
        if episode_dir.exists() and any(episode_dir.iterdir()):
            raise FileExistsError(f"Episode directory is not empty: {episode_dir}")
        episode_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir = episode_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        calls_path = episode_dir / "model_calls.jsonl"
        event_log = EventLog(episode_dir / "events.jsonl")
        started_wall = time.monotonic()
        started_utc = _utc_now()
        goal = str(task.goal)
        literals = TaskLiteralStore(goal)
        goals = GoalLedger(literals)
        role_frame = self.task_role_frame or TaskRoleParser().parse(goal)
        if not verify_exact_spans(goal, role_frame):
            raise ValueError("Shared task-role frame does not match immutable task.")
        evidence = EvidenceLedger()
        recoveries = RecoveryRegistryV02()
        calls: list[dict[str, Any]] = []
        call_attempts: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []
        recent_transitions: list[dict[str, Any]] = []
        ordinary_summary: str | None = None
        action_count = 0
        decision_index = 0
        eligible_opportunities = 0
        planned_auxiliary_calls = 0
        realized_auxiliary_calls = 0
        missed_auxiliary_calls: list[dict[str, Any]] = []
        repeated_action_blocks = 0
        different_class_after_recovery = 0
        task_initialized = False
        predicted_completion = False
        completion_reason: str | None = None
        termination_reason = "environment_action_budget_exhausted"
        error_record: dict[str, Any] | None = None
        failure_class: str | None = None
        evaluator_reward: float | None = None
        evaluator_status = "not_run"
        evaluator_error: dict[str, Any] | None = None
        previous_outcome = "first_observation"

        event_log.append(
            kind="episode_start_v0_2",
            step=0,
            payload={
                "episode_id": episode_id,
                "study_id": study_id,
                "arm": self.arm,
                "seed": seed,
                "task_name": str(task.name),
                "task_goal_sha256": literals.goal_sha256,
                "task_role_frame": role_frame.record(),
                "max_environment_actions": self.max_environment_actions,
                "max_model_calls": self.max_model_calls,
            },
        )
        try:
            env.reset(go_home=True)
            env.hide_automation_ui()
            task.initialize_task(env)
            task_initialized = True
            while action_count < self.max_environment_actions and len(calls) < self.max_model_calls:
                before = self.stabilizer.capture(env.get_state(wait_to_stabilize=True))
                height, width = before.state.pixels.shape[:2]
                before_path = screenshots_dir / f"d{decision_index:03d}_before.png"
                self._save_observation(before, before_path)
                event_log.append(
                    kind="observation_v0_2",
                    step=decision_index,
                    payload={"screenshot": before_path.name, **before.fingerprint.record()},
                )
                base_context = {
                    "authority": "current_screen_highest",
                    "previous_outcome": previous_outcome,
                }
                if self.uses_slots:
                    method_context = self.compiler.compile(
                        frame=role_frame,
                        evidence_ledger=evidence,
                        recovery_registry=recoveries,
                        current_state_signature=before.fingerprint.state_signature,
                        current_a11y_sha256=before.fingerprint.a11y_sha256,
                        intent="apply requested field to destination",
                    )
                else:
                    method_context = {
                        "summary": ordinary_summary,
                        "recent_transitions": recent_transitions[-2:],
                    }
                context = {**base_context, **method_context}
                prompt = self._prompt(
                    goal=goal,
                    role_frame=role_frame,
                    arm=self.arm,
                    decision_index=decision_index,
                    action_count=action_count,
                    max_actions=self.max_environment_actions,
                    call_count=len(calls),
                    max_calls=self.max_model_calls,
                    previous_outcome=previous_outcome,
                    context=context,
                    width=width,
                    height=height,
                )
                decision, parse_record = self._decision(
                    image_path=before_path,
                    user_prompt=prompt,
                    episode_id=episode_id,
                    decision_index=decision_index,
                    calls=calls,
                    calls_path=calls_path,
                    attempts=call_attempts,
                )
                step_record: dict[str, Any] = {
                    "decision_index": decision_index,
                    "action_index_before": action_count,
                    "before_screenshot": before_path.name,
                    "before_state_signature": before.fingerprint.state_signature,
                    "before_visible_texts": list(before.fingerprint.visible_texts),
                    "before_package_names": list(before.fingerprint.package_names),
                    "context": context,
                    "decision": decision,
                    "parse": parse_record,
                    "executed": False,
                }
                event_log.append(
                    kind="decision_v0_2",
                    step=decision_index,
                    payload={"status": decision["status"], "action": decision["action"], "intent": decision["intent"]},
                )

                accepted: list[str] = []
                rejected: list[dict[str, str]] = []
                if self.uses_slots:
                    for proposed in decision["evidence"]:
                        try:
                            record = evidence.add(
                                entity=proposed["entity"],
                                field=proposed["field"],
                                value=proposed["value"],
                                source=EvidenceSource.CURRENT_SCREEN,
                                scope=EvidenceScope(proposed["scope"]),
                                acquisition_step=decision_index,
                                source_sha256=before.fingerprint.a11y_sha256 or before.fingerprint.pixel_sha256,
                                expected_source_sha256=before.fingerprint.a11y_sha256 or before.fingerprint.pixel_sha256,
                                relevance_tags=tuple(
                                    item.text for item in (role_frame.source, role_frame.requested_field, role_frame.destination) if item
                                ),
                                visible_texts=before.fingerprint.visible_texts,
                            )
                            accepted.append(record.evidence_id)
                            event_log.append(kind="evidence_admitted_v0_2", step=decision_index, payload=record.record())
                        except ValueError as exc:
                            item = {"error": str(exc), "proposal_sha256": sha256(_canonical_json(proposed).encode("utf-8")).hexdigest()}
                            rejected.append(item)
                            event_log.append(kind="evidence_rejected_v0_2", step=decision_index, payload=item)
                step_record["evidence_update"] = {"accepted_ids": sorted(set(accepted)), "rejected": rejected}

                citation_error = self._validate_citations(
                    decision=decision,
                    literals=literals,
                    evidence=evidence,
                    visible_texts=before.fingerprint.visible_texts,
                ) if self.uses_slots else None
                if citation_error:
                    previous_outcome = f"provenance_block:{citation_error}"
                    step_record["provenance_block"] = citation_error
                    steps.append(step_record)
                    decision_index += 1
                    continue

                trigger = self._trigger(decision)
                step_record["eligible_opportunity"] = trigger
                if trigger["eligible"]:
                    eligible_opportunities += 1
                plan = {
                    "eligible": bool(trigger["eligible"]),
                    "planned": False,
                    "realized": False,
                    "reason": "arm_has_no_matched_auxiliary_policy",
                }
                if self.arm == "B3_MATCH" and trigger["eligible"]:
                    if len(calls) < self.max_model_calls:
                        plan["planned"] = True
                        plan["reason"] = "eligible_under_shared_policy_and_budget"
                        planned_auxiliary_calls += 1
                        ordinary_summary, summary_record = self._summary_call(
                            image_path=before_path,
                            episode_id=episode_id,
                            label=f"matched_summary_d{decision_index:03d}",
                            goal=goal,
                            role_frame=role_frame,
                            previous_summary=ordinary_summary,
                            recent_transitions=recent_transitions,
                            candidate=decision,
                            calls=calls,
                            calls_path=calls_path,
                            attempts=call_attempts,
                        )
                        realized_auxiliary_calls += 1
                        plan["realized"] = True
                        plan["summary"] = summary_record
                    else:
                        plan["reason"] = "total_model_call_ceiling"
                        missed_auxiliary_calls.append({"decision_index": decision_index, "reason": plan["reason"]})
                step_record["matched_auxiliary_plan"] = plan

                if decision["status"] in {"done", "fail"}:
                    termination_reason = f"model_{decision['status']}"
                    predicted_completion = decision["status"] == "done"
                    if predicted_completion:
                        goals.close_root()
                        completion_reason = "model_terminal_done"
                    steps.append(step_record)
                    break

                action = decision["action"]
                if self.uses_slots:
                    block_reason = recoveries.block_reason(
                        state_signature=before.fingerprint.state_signature,
                        canonical_action=action,
                    )
                    if block_reason:
                        repeated_action_blocks += 1
                        previous_outcome = f"recovery_block:{block_reason};choose_different_action_class"
                        step_record["recovery_block"] = block_reason
                        event_log.append(kind="recovery_action_block_v0_2", step=decision_index, payload={"reason": block_reason, "canonical_action": action})
                        steps.append(step_record)
                        decision_index += 1
                        continue
                    if recoveries.for_state(before.fingerprint.state_signature):
                        different_class_after_recovery += 1

                mapped = self.adapter.map_action(action, screen_width=width, screen_height=height)
                self.adapter.execute(env, mapped)
                action_count += 1
                step_record["executed"] = True
                step_record["mapped_action"] = mapped.audit_record()
                stabilized = self.stabilizer.observe_after(env=env, before=before)
                post_paths = []
                for sample_index, sample in enumerate(stabilized.post_observations, start=1):
                    path = screenshots_dir / f"d{decision_index:03d}_after{sample_index}.png"
                    self._save_observation(sample, path)
                    post_paths.append(path.name)
                transition_payload = {
                    "action_executed": True,
                    "canonical_action": action,
                    "before": before.fingerprint.record(),
                    "stability": stabilized.audit_record(),
                    "final": stabilized.final_observation.fingerprint.record(),
                }
                transition_event = event_log.append(kind="transition_v0_2", step=decision_index, payload=transition_payload)
                recovery_id = None
                if self.uses_slots and stabilized.no_effect_confirmed:
                    recovery = recoveries.register(
                        state_signature=before.fingerprint.state_signature,
                        canonical_action=action,
                        failed_event_id=transition_event.event_id,
                        observed_step=decision_index,
                        stability_audit=stabilized.audit_record(),
                    )
                    recovery_id = recovery.recovery_id
                    event_log.append(kind="recovery_registered_v0_2", step=decision_index, payload=recovery.record())
                step_record.update(
                    {
                        "action_index_after": action_count,
                        "after_screenshots": post_paths,
                        "after_state_signature": stabilized.final_observation.fingerprint.state_signature,
                        "transition": stabilized.audit_record(),
                        "recovery_id": recovery_id,
                    }
                )
                transition_summary = {
                    "action_index": action_count,
                    "intent": decision["intent"],
                    "action": action,
                    "outcome": stabilized.outcome,
                }
                recent_transitions.append(transition_summary)
                previous_outcome = f"executed:{_canonical_json(action)};outcome:{stabilized.outcome}"

                completion = self.completion_policy.after_action_satisfies(
                    frame=role_frame,
                    action=action,
                    observation=stabilized.final_observation.fingerprint,
                )
                step_record["completion_check"] = asdict(completion)
                if completion.satisfied:
                    predicted_completion = True
                    completion_reason = completion.reason
                    termination_reason = "deterministic_requirement_satisfied"
                    goals.close_root()
                    steps.append(step_record)
                    event_log.append(kind="deterministic_completion_v0_2", step=decision_index, payload=asdict(completion))
                    break

                if action.get("type") == "answer":
                    predicted_completion = True
                    completion_reason = "terminal_answer_executed"
                    termination_reason = "model_answer"
                    goals.close_root()
                    steps.append(step_record)
                    break

                if (
                    self.arm in {"B3", "B3_MATCH"}
                    and action_count % self.periodic_summary_actions == 0
                    and len(calls) < self.max_model_calls
                ):
                    final_path = screenshots_dir / post_paths[-1]
                    ordinary_summary, summary_record = self._summary_call(
                        image_path=final_path,
                        episode_id=episode_id,
                        label=f"periodic_summary_a{action_count:03d}",
                        goal=goal,
                        role_frame=role_frame,
                        previous_summary=ordinary_summary,
                        recent_transitions=recent_transitions,
                        candidate=None,
                        calls=calls,
                        calls_path=calls_path,
                        attempts=call_attempts,
                    )
                    step_record["periodic_summary"] = summary_record
                steps.append(step_record)
                decision_index += 1
            if len(calls) >= self.max_model_calls and termination_reason == "environment_action_budget_exhausted":
                termination_reason = "model_call_budget_exhausted"
        except Exception as exc:
            failure_class = _failure_class(exc)
            termination_reason = failure_class
            error_record = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            event_log.append(kind="episode_error_v0_2", step=decision_index, payload={"failure_class": failure_class, **error_record})
        finally:
            if task_initialized:
                try:
                    evaluator_reward = float(task.is_successful(env))
                    evaluator_status = "ran_after_controller_error" if error_record else "ran_normal"
                    event_log.append(kind="evaluator_result_v0_2", step=decision_index, payload={"reward": evaluator_reward, "status": evaluator_status, "visible_to_agent": False})
                except Exception as exc:
                    evaluator_status = "evaluator_error"
                    evaluator_error = {"type": type(exc).__name__, "message": str(exc)}
                    event_log.append(kind="evaluator_error_v0_2", step=decision_index, payload=evaluator_error)
                try:
                    task.tear_down(env)
                except Exception as exc:
                    event_log.append(kind="teardown_error", step=decision_index, payload={"type": type(exc).__name__, "message": str(exc)})
            try:
                env.reset(go_home=True)
            except Exception as exc:
                event_log.append(kind="reset_error", step=decision_index, payload={"type": type(exc).__name__, "message": str(exc)})

        prompt_tokens = sum(int(item.get("usage", {}).get("prompt_tokens", 0)) for item in calls)
        completion_tokens = sum(int(item.get("usage", {}).get("completion_tokens", 0)) for item in calls)
        executor_calls = sum(item["role"] in {"executor", "executor_repair"} for item in calls)
        auxiliary_calls = len(calls) - executor_calls
        schema_truncation_count = int(
            bool(error_record)
            and error_record.get("type") == "EestDecisionValidationError"
            and any(
                item["role"] in {"executor", "executor_repair"}
                and int(item.get("usage", {}).get("completion_tokens", 0)) >= self.max_new_tokens
                for item in calls[-2:]
            )
        )
        raw_call_record_count = (
            sum(1 for line in calls_path.read_text(encoding="utf-8").splitlines() if line.strip())
            if calls_path.is_file()
            else 0
        )
        summary = {
            "schema_version": "eest_ac_episode.v0_2",
            "study_id": study_id,
            "episode_id": episode_id,
            "arm": self.arm,
            "seed": seed,
            "task_name": str(task.name),
            "task_goal_sha256": literals.goal_sha256,
            "task_params_sha256": sha256(_canonical_json(_json_safe(task.params)).encode("utf-8")).hexdigest(),
            "task_role_frame": role_frame.record(),
            "started_at_utc": started_utc,
            "finished_at_utc": _utc_now(),
            "wall_time_seconds": time.monotonic() - started_wall,
            "termination_reason": termination_reason,
            "failure_class": failure_class,
            "error": error_record,
            "evaluator_reward": evaluator_reward,
            "evaluator_status": evaluator_status,
            "evaluator_error": evaluator_error,
            "task_success": evaluator_reward == 1.0,
            "predicted_completion": predicted_completion,
            "completion_reason": completion_reason,
            "completion_tp": bool(predicted_completion and evaluator_reward == 1.0),
            "completion_fp": bool(predicted_completion and evaluator_reward is not None and evaluator_reward != 1.0),
            "completion_fn": bool(not predicted_completion and evaluator_reward == 1.0),
            "environment_actions": action_count,
            "model_calls": len(calls),
            "model_call_record_count": raw_call_record_count,
            "model_call_accounting_valid": len(calls) == raw_call_record_count,
            "model_call_attempts": len(call_attempts),
            "executor_calls": executor_calls,
            "auxiliary_calls": auxiliary_calls,
            "eligible_opportunities": eligible_opportunities,
            "planned_auxiliary_calls": planned_auxiliary_calls,
            "realized_auxiliary_calls": realized_auxiliary_calls,
            "missed_auxiliary_calls": missed_auxiliary_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "max_prompt_tokens": max((int(item.get("usage", {}).get("prompt_tokens", 0)) for item in calls), default=0),
            "context_cap_respected": all(int(item.get("usage", {}).get("prompt_tokens", 0)) + self.max_new_tokens <= self.context_cap_tokens for item in calls),
            "schema_truncation_count": schema_truncation_count,
            "repeated_action_blocks": repeated_action_blocks,
            "different_class_after_recovery": different_class_after_recovery,
            "task_literals": literals.record(),
            "goal_ledger": [item.record() for item in goals.requirements],
            "invented_requirement_count": 0,
            "evidence_ledger": [item.record() for item in sorted(evidence.records, key=lambda value: value.evidence_id)],
            "recovery_registry": [item.record() for item in recoveries.records],
            "ordinary_summary": ordinary_summary,
            "event_log_verified": event_log.verify(),
            "event_count": len(event_log.events),
            "steps": steps,
            "model_call_records": calls,
            "model_call_attempt_records": call_attempts,
        }
        _write_json(episode_dir / "episode_summary.json", summary)
        return summary
