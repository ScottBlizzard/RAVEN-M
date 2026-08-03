"""Independent minimal controller for the EEST-AC paired experiment."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import re
import time
import traceback
from typing import Any

from PIL import Image

from raven_m.eest_ac.compiler import ActionNeed, ContextCompiler
from raven_m.eest_ac.models import EvidenceScope, EvidenceSource
from raven_m.eest_ac.risk import RiskDetector
from raven_m.eest_ac.schema import (
    EestDecisionValidationError,
    parse_eest_decision,
)
from raven_m.eest_ac.state import (
    EvidenceLedger,
    EventLog,
    GoalLedger,
    RecoveryRegistry,
    TaskLiteralStore,
)
from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.models.transformers_client import ModelCall, TransformersClient


ARMS = frozenset({"B3", "B3_MATCH", "M_SLOTS", "M_RISK"})
_IGNORED_PACKAGES = frozenset({"com.android.systemui"})
_SEMANTIC_FIELDS = (
    "text",
    "content_description",
    "hint_text",
    "tooltip",
    "class_name",
    "package_name",
    "resource_name",
    "resource_id",
    "is_clickable",
    "is_editable",
    "is_checkable",
    "is_checked",
    "is_selected",
    "is_scrollable",
    "is_enabled",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _json_safe(value: Any) -> Any:
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


def _element_value(element: Any, field: str) -> Any:
    if isinstance(element, dict):
        return element.get(field)
    return getattr(element, field, None)


def _normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def semantic_observation(
    ui_elements: Any,
    *,
    screenshot_sha256: str,
) -> dict[str, Any]:
    """Return stable visible UI text and a benchmark-neutral semantic hash."""
    records: list[dict[str, Any]] = []
    texts: set[str] = set()
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        package = _normalized_text(_element_value(element, "package_name"))
        if package in _IGNORED_PACKAGES:
            continue
        record: dict[str, Any] = {}
        for field in _SEMANTIC_FIELDS:
            value = _element_value(element, field)
            if value is None:
                continue
            if field in {
                "text",
                "content_description",
                "hint_text",
                "tooltip",
                "class_name",
                "package_name",
                "resource_name",
                "resource_id",
            }:
                value = _normalized_text(value)
                if not value:
                    continue
            record[field] = value
        for field in ("text", "content_description", "hint_text", "tooltip"):
            value = _normalized_text(_element_value(element, field))
            if value:
                texts.add(value)
        if record:
            records.append(record)
    if records:
        encoded = sorted(_canonical_json(item) for item in records)
        semantic_sha = sha256(_canonical_json(encoded).encode("utf-8")).hexdigest()
        source = "accessibility"
    else:
        semantic_sha = screenshot_sha256
        source = "screenshot_fallback"
    return {
        "schema_version": "eest_ac_semantic_observation.v0_1",
        "source": source,
        "sha256": semantic_sha,
        "element_count": len(records),
        "visible_texts": sorted(texts),
    }


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical_json(value) + "\n")


def _parse_summary(raw: str) -> str:
    value = json.loads(raw.strip())
    if set(value) != {"summary"} or not isinstance(value["summary"], str):
        raise ValueError("Summary must contain exactly one string field.")
    summary = value["summary"].strip()
    if not summary or len(summary) > 2000:
        raise ValueError("Summary is empty or too long.")
    return summary


def _parse_gate(raw: str) -> dict[str, Any]:
    value = json.loads(raw.strip())
    if set(value) != {"decision", "reason", "required_evidence_ids"}:
        raise ValueError("Risk gate returned an unexpected object shape.")
    if value["decision"] not in {"allow", "block"}:
        raise ValueError("Risk gate decision must be allow or block.")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("Risk gate reason is required.")
    identifiers = value["required_evidence_ids"]
    if (
        not isinstance(identifiers, list)
        or len(identifiers) > 8
        or not all(isinstance(item, str) for item in identifiers)
    ):
        raise ValueError("Risk gate evidence IDs are invalid.")
    return value


class EestAcController:
    """Observe, select evidence, act, and audit without legacy route guards."""

    def __init__(
        self,
        *,
        client: TransformersClient,
        executor_prompt: str,
        summary_prompt: str,
        risk_gate_prompt: str,
        arm: str,
        max_environment_actions: int,
        max_model_calls: int,
        max_new_tokens: int = 256,
        context_cap_tokens: int = 8192,
        adapter: AndroidWorldAdapter | None = None,
        compiler: ContextCompiler | None = None,
    ) -> None:
        if arm not in ARMS:
            raise ValueError(f"Unknown EEST-AC arm: {arm}")
        if max_environment_actions < 1 or max_model_calls < 1:
            raise ValueError("Episode budgets must be positive.")
        self.client = client
        self.executor_prompt = executor_prompt
        self.summary_prompt = summary_prompt
        self.risk_gate_prompt = risk_gate_prompt
        self.arm = arm
        self.max_environment_actions = max_environment_actions
        self.max_model_calls = max_model_calls
        self.max_new_tokens = max_new_tokens
        self.context_cap_tokens = context_cap_tokens
        self.adapter = adapter or AndroidWorldAdapter()
        self.compiler = compiler or ContextCompiler()
        self.risk_detector = RiskDetector()

    @property
    def uses_slots(self) -> bool:
        return self.arm in {"M_SLOTS", "M_RISK"}

    def _record_call(
        self,
        *,
        call: ModelCall,
        calls: list[dict[str, Any]],
        calls_path: Path,
        role: str,
    ) -> None:
        record = {"role": role, **call.audit_record()}
        calls.append(record)
        _append_jsonl(calls_path, record)
        prompt_tokens = int(call.usage.get("prompt_tokens", 0))
        if prompt_tokens + self.max_new_tokens > self.context_cap_tokens:
            raise RuntimeError(
                "CONTEXT_CAP_EXCEEDED: "
                f"{prompt_tokens}+{self.max_new_tokens}>{self.context_cap_tokens}"
            )

    def _generate_decision(
        self,
        *,
        image_path: Path,
        user_prompt: str,
        episode_id: str,
        decision_index: int,
        remaining_calls: int,
        calls: list[dict[str, Any]],
        calls_path: Path,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        initial = self.client.generate(
            image_path=image_path,
            system_prompt=self.executor_prompt,
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"executor_d{decision_index:03d}_initial",
            max_tokens=self.max_new_tokens,
        )
        self._record_call(
            call=initial,
            calls=calls,
            calls_path=calls_path,
            role="executor",
        )
        used = 1
        try:
            parsed = parse_eest_decision(initial.content)
            return (
                parsed.decision,
                {
                    "first_pass": parsed.first_pass,
                    "extraction_used": parsed.extraction_used,
                    "schema_sha256": parsed.schema_sha256,
                    "repaired": False,
                },
                used,
            )
        except EestDecisionValidationError as initial_error:
            if remaining_calls < 2:
                raise
            repair_prompt = "\n".join(
                [
                    user_prompt,
                    "PREVIOUS_OUTPUT_INVALID:",
                    initial.content[:4000],
                    "VALIDATION_ERROR:",
                    str(initial_error)[:1000],
                    "Return only a corrected eest_ac_decision.v0_1 JSON object.",
                ]
            )
            repaired = self.client.generate(
                image_path=image_path,
                system_prompt=self.executor_prompt,
                user_prompt=repair_prompt,
                episode_id=episode_id,
                call_label=f"executor_d{decision_index:03d}_repair",
                max_tokens=self.max_new_tokens,
            )
            self._record_call(
                call=repaired,
                calls=calls,
                calls_path=calls_path,
                role="executor_repair",
            )
            used += 1
            parsed = parse_eest_decision(repaired.content)
            return (
                parsed.decision,
                {
                    "first_pass": False,
                    "extraction_used": parsed.extraction_used,
                    "schema_sha256": parsed.schema_sha256,
                    "repaired": True,
                    "initial_error": str(initial_error),
                },
                used,
            )

    def _auxiliary_summary(
        self,
        *,
        image_path: Path,
        episode_id: str,
        label: str,
        task: str,
        previous_summary: str | None,
        recent_transitions: list[dict[str, Any]],
        candidate: dict[str, Any] | None,
        calls: list[dict[str, Any]],
        calls_path: Path,
    ) -> tuple[str | None, dict[str, Any]]:
        prompt = _canonical_json(
            {
                "task": task,
                "previous_summary": previous_summary,
                "recent_transitions": recent_transitions[-5:],
                "current_candidate": candidate,
            }
        )
        call = self.client.generate(
            image_path=image_path,
            system_prompt=self.summary_prompt,
            user_prompt=prompt,
            episode_id=episode_id,
            call_label=label,
            max_tokens=self.max_new_tokens,
        )
        self._record_call(
            call=call,
            calls=calls,
            calls_path=calls_path,
            role="ordinary_summary",
        )
        try:
            return _parse_summary(call.content), {"valid": True}
        except (json.JSONDecodeError, ValueError) as exc:
            return previous_summary, {"valid": False, "error": str(exc)}

    def _risk_gate(
        self,
        *,
        image_path: Path,
        episode_id: str,
        decision_index: int,
        task: str,
        compiled_context: dict[str, Any],
        candidate: dict[str, Any],
        trigger: dict[str, Any],
        calls: list[dict[str, Any]],
        calls_path: Path,
    ) -> dict[str, Any]:
        prompt = _canonical_json(
            {
                "task": task,
                "context": compiled_context,
                "candidate": candidate,
                "trigger": trigger,
            }
        )
        call = self.client.generate(
            image_path=image_path,
            system_prompt=self.risk_gate_prompt,
            user_prompt=prompt,
            episode_id=episode_id,
            call_label=f"risk_gate_d{decision_index:03d}",
            max_tokens=self.max_new_tokens,
        )
        self._record_call(
            call=call,
            calls=calls,
            calls_path=calls_path,
            role="risk_gate",
        )
        try:
            return {"valid": True, **_parse_gate(call.content)}
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "valid": False,
                "decision": "block",
                "reason": f"invalid_gate_output:{exc}",
                "required_evidence_ids": [],
            }

    @staticmethod
    def _prompt(
        *,
        goal: str,
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
            [
                f"IMMUTABLE_TASK: {goal}",
                f"ARM: {arm}",
                f"DECISION_INDEX: {decision_index}",
                f"ENVIRONMENT_ACTION_BUDGET: {action_count}/{max_actions}",
                f"MODEL_CALL_BUDGET: {call_count}/{max_calls}",
                f"PREVIOUS_OBSERVED_OUTCOME: {previous_outcome}",
                "EPISODE_CONTEXT: " + _canonical_json(context),
                f"CURRENT_SCREEN_SIZE: {width}x{height}",
                "The attached image is the authoritative current screenshot.",
                "Return one schema-valid JSON decision now.",
            ]
        )

    @staticmethod
    def _next_need(decision: dict[str, Any]) -> ActionNeed:
        text = " ".join(
            str(decision.get(key, ""))
            for key in ("decision_summary", "expected_outcome")
        )
        entities = tuple(
            item.get("entity", "")
            for item in decision.get("observed_evidence", [])
            if isinstance(item, dict)
        )
        fields = tuple(
            item.get("field", "")
            for item in decision.get("observed_evidence", [])
            if isinstance(item, dict)
        )
        return ActionNeed(entities=entities, fields=fields, intent=text[:240])

    @staticmethod
    def _validate_citations(
        *,
        decision: dict[str, Any],
        task_literals: TaskLiteralStore,
        evidence_ledger: EvidenceLedger,
        visible_texts: list[str],
    ) -> str | None:
        citation_ids = decision.get("evidence_citations", [])
        task_ids = {item.literal_id for item in task_literals.literals}
        cited_evidence = []
        for citation in citation_ids:
            if citation.startswith("task:"):
                if citation not in task_ids:
                    return f"unknown_task_citation:{citation}"
                continue
            record = evidence_ledger.get(citation)
            if record is None:
                return f"unknown_evidence_citation:{citation}"
            cited_evidence.append(record)
        action = decision.get("action")
        if not isinstance(action, dict) or action.get("type") != "type_text":
            return None
        text = str(action.get("text", ""))
        visible = "\n".join(visible_texts).casefold()
        grounded = (
            task_literals.contains_exact(text)
            or text.casefold() in visible
            or any(
                text.casefold() == item.value.casefold()
                or text.casefold() in item.value.casefold()
                for item in cited_evidence
            )
        )
        return None if grounded else "typed_text_has_no_allowed_provenance"

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
        task_initialized = False
        goal = str(task.goal)
        literals = TaskLiteralStore(goal)
        goals = GoalLedger(literals)
        evidence = EvidenceLedger()
        recoveries = RecoveryRegistry()
        ordinary_summary: str | None = None
        recent_transitions: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []
        call_count = 0
        action_count = 0
        decision_index = 0
        gate_count = 0
        gate_block_count = 0
        unnecessary_verification_count = 0
        previous_outcome = "none; first observation"
        termination_reason = "environment_action_budget_exhausted"
        evaluator_reward: float | None = None
        error_record: dict[str, Any] | None = None
        predicted_completion = False
        next_need = ActionNeed()

        event_log.append(
            kind="episode_start",
            step=0,
            payload={
                "episode_id": episode_id,
                "study_id": study_id,
                "arm": self.arm,
                "seed": seed,
                "task_name": str(task.name),
                "task_goal_sha256": literals.goal_sha256,
                "task_params_sha256": sha256(
                    _canonical_json(_json_safe(task.params)).encode("utf-8")
                ).hexdigest(),
                "max_environment_actions": self.max_environment_actions,
                "max_model_calls": self.max_model_calls,
            },
        )
        try:
            env.reset(go_home=True)
            env.hide_automation_ui()
            task.initialize_task(env)
            task_initialized = True
            if str(task.goal) != goal:
                event_log.append(
                    kind="task_goal_changed_after_initialization",
                    step=0,
                    payload={
                        "before_sha256": literals.goal_sha256,
                        "after_sha256": sha256(str(task.goal).encode("utf-8")).hexdigest(),
                        "policy": "retain_immutable_preinitialization_goal",
                    },
                )
            while (
                action_count < self.max_environment_actions
                and call_count < self.max_model_calls
            ):
                state_before = env.get_state(wait_to_stabilize=True)
                height, width = state_before.pixels.shape[:2]
                before_path = screenshots_dir / f"d{decision_index:03d}_before.png"
                Image.fromarray(state_before.pixels).save(before_path)
                before_pixel_sha = sha256(before_path.read_bytes()).hexdigest()
                before_semantic = semantic_observation(
                    getattr(state_before, "ui_elements", ()),
                    screenshot_sha256=before_pixel_sha,
                )
                event_log.append(
                    kind="observation",
                    step=decision_index,
                    payload={
                        "screenshot": before_path.name,
                        "screenshot_sha256": before_pixel_sha,
                        "semantic_sha256": before_semantic["sha256"],
                        "semantic_source": before_semantic["source"],
                        "visible_text_count": len(before_semantic["visible_texts"]),
                    },
                )
                if self.uses_slots:
                    context = self.compiler.compile(
                        task_literals=literals,
                        goal_ledger=goals,
                        evidence_ledger=evidence,
                        recovery_registry=recoveries,
                        current_screen_sha256=before_semantic["sha256"],
                        need=next_need,
                    )
                else:
                    context = {
                        "schema_version": "ordinary_summary_context.v0_1",
                        "authority": {
                            "current_screenshot": "highest_for_current_page",
                            "history": "ordinary_summary_and_last_two_transitions",
                        },
                        "summary": ordinary_summary,
                        "recent_transitions": recent_transitions[-2:],
                    }
                user_prompt = self._prompt(
                    goal=goal,
                    arm=self.arm,
                    decision_index=decision_index,
                    action_count=action_count,
                    max_actions=self.max_environment_actions,
                    call_count=call_count,
                    max_calls=self.max_model_calls,
                    previous_outcome=previous_outcome,
                    context=context,
                    width=width,
                    height=height,
                )
                decision, parse_record, used_calls = self._generate_decision(
                    image_path=before_path,
                    user_prompt=user_prompt,
                    episode_id=episode_id,
                    decision_index=decision_index,
                    remaining_calls=self.max_model_calls - call_count,
                    calls=calls,
                    calls_path=calls_path,
                )
                call_count += used_calls
                step_record: dict[str, Any] = {
                    "decision_index": decision_index,
                    "action_index_before": action_count,
                    "before_screenshot": before_path.name,
                    "before_semantic_sha256": before_semantic["sha256"],
                    "context": context,
                    "decision": decision,
                    "parse": parse_record,
                    "executed": False,
                }
                event_log.append(
                    kind="decision",
                    step=decision_index,
                    payload={
                        "status": decision["status"],
                        "action": decision["action"],
                        "decision_summary": decision["decision_summary"],
                    },
                )

                evidence_accepts: list[str] = []
                evidence_rejects: list[dict[str, str]] = []
                if self.uses_slots:
                    for proposed in decision["observed_evidence"]:
                        try:
                            record = evidence.add(
                                entity=proposed["entity"],
                                field=proposed["field"],
                                value=proposed["value"],
                                source=EvidenceSource.CURRENT_SCREEN,
                                scope=EvidenceScope(proposed["scope"]),
                                acquisition_step=decision_index,
                                source_sha256=before_semantic["sha256"],
                                expected_source_sha256=before_semantic["sha256"],
                                relevance_tags=proposed["relevance_tags"],
                                visible_texts=before_semantic["visible_texts"],
                            )
                            evidence_accepts.append(record.evidence_id)
                            event_log.append(
                                kind="evidence_admitted",
                                step=decision_index,
                                payload=record.record(),
                            )
                        except ValueError as exc:
                            rejection = {
                                "error": str(exc),
                                "proposal_sha256": sha256(
                                    _canonical_json(proposed).encode("utf-8")
                                ).hexdigest(),
                            }
                            evidence_rejects.append(rejection)
                            event_log.append(
                                kind="evidence_rejected",
                                step=decision_index,
                                payload=rejection,
                            )
                step_record["evidence_update"] = {
                    "accepted_ids": evidence_accepts,
                    "rejected": evidence_rejects,
                }
                citation_error = (
                    self._validate_citations(
                        decision=decision,
                        task_literals=literals,
                        evidence_ledger=evidence,
                        visible_texts=before_semantic["visible_texts"],
                    )
                    if self.uses_slots
                    else None
                )
                if citation_error:
                    previous_outcome = (
                        "The candidate was not executed because provenance "
                        f"validation failed: {citation_error}."
                    )
                    step_record["provenance_block"] = citation_error
                    event_log.append(
                        kind="provenance_block",
                        step=decision_index,
                        payload={"reason": citation_error},
                    )
                    steps.append(step_record)
                    decision_index += 1
                    next_need = self._next_need(decision)
                    continue

                trigger = self.risk_detector.detect(decision)
                trigger_record = asdict(trigger)
                step_record["risk_trigger"] = trigger_record
                if self.arm == "B3_MATCH" and trigger.eligible:
                    if call_count >= self.max_model_calls:
                        termination_reason = "model_call_budget_exhausted_before_matched_aux"
                        steps.append(step_record)
                        break
                    ordinary_summary, summary_record = self._auxiliary_summary(
                        image_path=before_path,
                        episode_id=episode_id,
                        label=f"matched_summary_d{decision_index:03d}",
                        task=goal,
                        previous_summary=ordinary_summary,
                        recent_transitions=recent_transitions,
                        candidate=decision,
                        calls=calls,
                        calls_path=calls_path,
                    )
                    call_count += 1
                    step_record["matched_auxiliary_summary"] = summary_record
                    event_log.append(
                        kind="matched_summary_call",
                        step=decision_index,
                        payload={"trigger": trigger_record, **summary_record},
                    )
                if self.arm == "M_RISK" and trigger.eligible:
                    if call_count >= self.max_model_calls:
                        termination_reason = "model_call_budget_exhausted_before_risk_gate"
                        steps.append(step_record)
                        break
                    gate = self._risk_gate(
                        image_path=before_path,
                        episode_id=episode_id,
                        decision_index=decision_index,
                        task=goal,
                        compiled_context=context,
                        candidate=decision,
                        trigger=trigger_record,
                        calls=calls,
                        calls_path=calls_path,
                    )
                    call_count += 1
                    gate_count += 1
                    step_record["risk_gate"] = gate
                    event_log.append(
                        kind="risk_gate",
                        step=decision_index,
                        payload={"trigger": trigger_record, **gate},
                    )
                    if gate["decision"] == "block":
                        gate_block_count += 1
                        previous_outcome = (
                            "The consequential candidate was blocked: "
                            + str(gate["reason"])
                        )
                        steps.append(step_record)
                        decision_index += 1
                        next_need = self._next_need(decision)
                        continue

                if decision["status"] in {"done", "fail"}:
                    termination_reason = f"model_{decision['status']}"
                    predicted_completion = decision["status"] == "done"
                    if predicted_completion:
                        goals.close_root()
                    steps.append(step_record)
                    event_log.append(
                        kind="terminal_decision",
                        step=decision_index,
                        payload={"status": decision["status"]},
                    )
                    break

                action = decision["action"]
                mapped = self.adapter.map_action(
                    action,
                    screen_width=width,
                    screen_height=height,
                )
                self.adapter.execute(env, mapped)
                action_count += 1
                step_record["executed"] = True
                step_record["mapped_action"] = mapped.audit_record()
                state_after = env.get_state(wait_to_stabilize=True)
                after_path = screenshots_dir / f"d{decision_index:03d}_after.png"
                Image.fromarray(state_after.pixels).save(after_path)
                after_pixel_sha = sha256(after_path.read_bytes()).hexdigest()
                after_semantic = semantic_observation(
                    getattr(state_after, "ui_elements", ()),
                    screenshot_sha256=after_pixel_sha,
                )
                no_effect = before_semantic["sha256"] == after_semantic["sha256"]
                outcome = "no_effect_confirmed" if no_effect else "semantic_changed"
                transition_payload = {
                    "outcome": outcome,
                    "action_executed": True,
                    "canonical_action": action,
                    "before_semantic_sha256": before_semantic["sha256"],
                    "after_semantic_sha256": after_semantic["sha256"],
                    "before_screenshot_sha256": before_pixel_sha,
                    "after_screenshot_sha256": after_pixel_sha,
                }
                transition_event = event_log.append(
                    kind="transition",
                    step=decision_index,
                    payload=transition_payload,
                )
                recovery_id = None
                if self.uses_slots and no_effect:
                    recovery = recoveries.register_confirmed_no_effect(
                        transition_event
                    )
                    recovery_id = recovery.recovery_id
                    event_log.append(
                        kind="recovery_registered",
                        step=decision_index,
                        payload=recovery.record(),
                    )
                step_record.update(
                    {
                        "action_index_after": action_count,
                        "after_screenshot": after_path.name,
                        "after_semantic_sha256": after_semantic["sha256"],
                        "transition_outcome": outcome,
                        "recovery_id": recovery_id,
                    }
                )
                transition_summary = {
                    "action_index": action_count,
                    "decision_summary": decision["decision_summary"],
                    "action": action,
                    "observed_outcome": outcome,
                }
                recent_transitions.append(transition_summary)
                previous_outcome = (
                    f"Executed {_canonical_json(action)}; "
                    + (
                        "the semantic UI did not change."
                        if no_effect
                        else "the semantic UI changed."
                    )
                )
                if self.arm == "B3" and action_count % 5 == 0:
                    if call_count >= self.max_model_calls:
                        termination_reason = "model_call_budget_exhausted_before_periodic_summary"
                        steps.append(step_record)
                        break
                    ordinary_summary, summary_record = self._auxiliary_summary(
                        image_path=after_path,
                        episode_id=episode_id,
                        label=f"periodic_summary_a{action_count:03d}",
                        task=goal,
                        previous_summary=ordinary_summary,
                        recent_transitions=recent_transitions,
                        candidate=None,
                        calls=calls,
                        calls_path=calls_path,
                    )
                    call_count += 1
                    step_record["periodic_summary"] = summary_record
                    event_log.append(
                        kind="periodic_summary_call",
                        step=decision_index,
                        payload=summary_record,
                    )
                steps.append(step_record)
                if action.get("type") == "answer":
                    termination_reason = "model_answer"
                    predicted_completion = True
                    goals.close_root()
                    break
                decision_index += 1
                next_need = self._next_need(decision)
            if call_count >= self.max_model_calls and termination_reason == "environment_action_budget_exhausted":
                termination_reason = "model_call_budget_exhausted"
            evaluator_reward = float(task.is_successful(env))
            event_log.append(
                kind="evaluator_result",
                step=decision_index,
                payload={"reward": evaluator_reward, "visible_to_agent": False},
            )
        except Exception as exc:  # runtime and controller failures are audited
            termination_reason = "infrastructure_or_controller_error"
            error_record = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            event_log.append(
                kind="episode_error",
                step=decision_index,
                payload=error_record,
            )
        finally:
            if task_initialized:
                try:
                    task.tear_down(env)
                except Exception as exc:  # preserve primary result
                    event_log.append(
                        kind="teardown_error",
                        step=decision_index,
                        payload={"type": type(exc).__name__, "message": str(exc)},
                    )
            try:
                env.reset(go_home=True)
            except Exception as exc:
                event_log.append(
                    kind="reset_error",
                    step=decision_index,
                    payload={"type": type(exc).__name__, "message": str(exc)},
                )

        total_prompt_tokens = sum(
            int(item.get("usage", {}).get("prompt_tokens", 0)) for item in calls
        )
        total_completion_tokens = sum(
            int(item.get("usage", {}).get("completion_tokens", 0)) for item in calls
        )
        executor_calls = sum(
            item["role"] in {"executor", "executor_repair"} for item in calls
        )
        auxiliary_calls = len(calls) - executor_calls
        summary = {
            "schema_version": "eest_ac_episode.v0_1",
            "study_id": study_id,
            "episode_id": episode_id,
            "arm": self.arm,
            "seed": seed,
            "task_name": str(task.name),
            "task_goal_sha256": literals.goal_sha256,
            "task_params_sha256": sha256(
                _canonical_json(_json_safe(task.params)).encode("utf-8")
            ).hexdigest(),
            "started_at_utc": started_utc,
            "finished_at_utc": _utc_now(),
            "wall_time_seconds": time.monotonic() - started_wall,
            "termination_reason": termination_reason,
            "evaluator_reward": evaluator_reward,
            "task_success": evaluator_reward == 1.0,
            "predicted_completion": predicted_completion,
            "completion_tp": bool(predicted_completion and evaluator_reward == 1.0),
            "completion_fp": bool(predicted_completion and evaluator_reward != 1.0),
            "completion_fn": bool(not predicted_completion and evaluator_reward == 1.0),
            "environment_actions": action_count,
            "model_calls": call_count,
            "executor_calls": executor_calls,
            "auxiliary_calls": auxiliary_calls,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "max_prompt_tokens": max(
                (
                    int(item.get("usage", {}).get("prompt_tokens", 0))
                    for item in calls
                ),
                default=0,
            ),
            "context_cap_respected": all(
                int(item.get("usage", {}).get("prompt_tokens", 0))
                + self.max_new_tokens
                <= self.context_cap_tokens
                for item in calls
            ),
            "risk_gate_count": gate_count,
            "risk_gate_block_count": gate_block_count,
            "unnecessary_verification_count": unnecessary_verification_count,
            "blocked_action_recovery": None,
            "task_literals": literals.record(),
            "goal_ledger": [item.record() for item in goals.requirements],
            "invented_requirement_count": 0,
            "evidence_ledger": [item.record() for item in evidence.records],
            "recovery_registry": [item.record() for item in recoveries.records],
            "ordinary_summary": ordinary_summary,
            "event_log_verified": event_log.verify(),
            "event_count": len(event_log.events),
            "steps": steps,
            "model_call_records": calls,
            "error": error_record,
        }
        # A block is recovered only when a later action executes and evaluation
        # succeeds; the analysis also reports partial progress separately.
        if gate_block_count:
            summary["blocked_action_recovery"] = bool(
                evaluator_reward == 1.0
                and any(
                    item.get("executed")
                    and item.get("decision_index", -1)
                    > next(
                        (
                            prior.get("decision_index", -1)
                            for prior in steps
                            if prior.get("risk_gate", {}).get("decision") == "block"
                        ),
                        -1,
                    )
                    for item in steps
                )
            )
        _write_json(episode_dir / "episode_summary.json", summary)
        return summary
