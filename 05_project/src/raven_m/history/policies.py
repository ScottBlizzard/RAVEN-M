"""Controlled history policies for the B0-B3 baseline family."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from PIL import Image

from raven_m.actions.schema import ActionValidationError
from raven_m.history.summary_schema import parse_summary_response
from raven_m.memory.manager import RavenMemoryManager, TransitionObservation
from raven_m.memory.models import MemoryConfig
from raven_m.models.transformers_client import ModelCall, TransformersClient
from raven_m.roles.orchestrator import RoleOrchestrator


@dataclass(frozen=True)
class HistoryEntry:
    step: int
    decision_summary: str
    action: dict[str, Any]
    observed_outcome: str
    screenshot_path: Path
    screenshot_sha256: str
    semantic_ui_sha256: str = ""
    before_screenshot_path: Path | None = None
    before_screenshot_sha256: str = ""
    before_semantic_ui_sha256: str = ""
    visible_failure_texts: tuple[str, ...] = ()
    evidence_outcome: str = "none; this is the first observation"
    expected_outcome: str = ""
    state_delta: tuple[dict[str, Any], ...] = ()
    model_call_id: str | None = None

    def record(self, image_label: str | None = None) -> dict[str, Any]:
        value = {
            "step": self.step,
            "decision_summary": self.decision_summary,
            "action": self.action,
            "observed_outcome": self.observed_outcome,
            "screenshot_sha256": self.screenshot_sha256,
        }
        if image_label:
            value["historical_image_label"] = image_label
        return value


@dataclass(frozen=True)
class HistoryContext:
    rendered: str
    images: list[tuple[str, Path]] = field(default_factory=list)


@dataclass(frozen=True)
class HistoryUpdate:
    calls: list[ModelCall] = field(default_factory=list)
    summary_updated: bool = False
    error: dict[str, Any] | None = None
    summary_schema_sha256: str | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class CompletionAdjudication:
    accepted: bool = True
    calls: list[ModelCall] = field(default_factory=list)
    record: dict[str, Any] | None = None
    error: str | None = None


class HistoryPolicy:
    variant = "B0"

    def reset(
        self,
        *,
        episode_dir: Path,
        goal: str,
        episode_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        self.episode_dir = episode_dir
        self.goal = goal
        self.entries: list[HistoryEntry] = []
        self.thumbnail_dir = episode_dir / "history_thumbnails"

    def validate_decision(self, decision: dict[str, Any]) -> None:
        del decision

    def adjudicate_completion(
        self,
        decision: dict[str, Any],
        *,
        image_path: Path,
        episode_id: str,
        step: int,
        remaining_model_calls: int,
    ) -> CompletionAdjudication:
        del decision, image_path, episode_id, step, remaining_model_calls
        return CompletionAdjudication()

    def context(self) -> HistoryContext:
        return HistoryContext(rendered="[]")

    def observe(
        self,
        entry: HistoryEntry,
        *,
        episode_id: str,
        remaining_model_calls: int,
    ) -> HistoryUpdate:
        self.entries.append(entry)
        return HistoryUpdate()

    def _thumbnail(self, entry: HistoryEntry, long_side: int = 384) -> Path:
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        destination = self.thumbnail_dir / f"step_{entry.step:03d}.png"
        if not destination.exists():
            image = Image.open(entry.screenshot_path).convert("RGB")
            image.thumbnail((long_side, long_side), Image.Resampling.LANCZOS)
            image.save(destination, format="PNG", optimize=True)
        return destination


class SlidingWindowPolicy(HistoryPolicy):
    variant = "B1"

    def __init__(self, k: int = 3) -> None:
        self.k = k

    def context(self) -> HistoryContext:
        selected = self.entries[-self.k :]
        images: list[tuple[str, Path]] = []
        records = []
        for entry in selected:
            label = f"b1_step_{entry.step:03d}_after"
            images.append((label, self._thumbnail(entry)))
            records.append(entry.record(label))
        return HistoryContext(
            rendered=json.dumps(
                {
                    "variant": self.variant,
                    "window_k": self.k,
                    "entries": records,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            images=images,
        )


class RawFullHistoryPolicy(HistoryPolicy):
    variant = "B2"

    def __init__(self, max_chars: int = 12000, max_images: int = 8) -> None:
        self.max_chars = max_chars
        self.max_images = max_images

    def context(self) -> HistoryContext:
        selected: list[HistoryEntry] = []
        used_chars = 0
        for entry in reversed(self.entries):
            encoded = json.dumps(
                entry.record(), ensure_ascii=False, separators=(",", ":")
            )
            if selected and (
                used_chars + len(encoded) > self.max_chars
                or len(selected) >= self.max_images
            ):
                break
            selected.append(entry)
            used_chars += len(encoded)
        selected.reverse()
        images: list[tuple[str, Path]] = []
        records = []
        for entry in selected:
            label = f"b2_step_{entry.step:03d}_after"
            images.append((label, self._thumbnail(entry)))
            records.append(entry.record(label))
        return HistoryContext(
            rendered=json.dumps(
                {
                    "variant": self.variant,
                    "retention": "fifo_under_frozen_caps",
                    "max_chars": self.max_chars,
                    "max_images": self.max_images,
                    "entries": records,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            images=images,
        )


class SimpleSummaryPolicy(HistoryPolicy):
    variant = "B3"

    def __init__(
        self,
        *,
        client: TransformersClient,
        system_prompt: str,
        trigger_every: int = 5,
        keep_recent: int = 2,
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.trigger_every = trigger_every
        self.keep_recent = keep_recent

    def reset(
        self,
        *,
        episode_dir: Path,
        goal: str,
        episode_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().reset(
            episode_dir=episode_dir,
            goal=goal,
            episode_id=episode_id,
            task_id=task_id,
        )
        self.summary: dict[str, Any] | None = None
        self.pending: list[HistoryEntry] = []

    def context(self) -> HistoryContext:
        recent = self.entries[-self.keep_recent :]
        images: list[tuple[str, Path]] = []
        records = []
        for entry in recent:
            label = f"b3_recent_step_{entry.step:03d}_after"
            images.append((label, self._thumbnail(entry)))
            records.append(entry.record(label))
        return HistoryContext(
            rendered=json.dumps(
                {
                    "variant": self.variant,
                    "summary": self.summary,
                    "recent_entries": records,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            images=images,
        )

    def observe(
        self,
        entry: HistoryEntry,
        *,
        episode_id: str,
        remaining_model_calls: int,
    ) -> HistoryUpdate:
        self.entries.append(entry)
        self.pending.append(entry)
        if len(self.pending) < self.trigger_every:
            return HistoryUpdate()
        return self._summarize_pending(
            entry=entry,
            episode_id=episode_id,
            remaining_model_calls=remaining_model_calls,
            call_prefix="b3_summary",
        )

    def _summarize_pending(
        self,
        *,
        entry: HistoryEntry,
        episode_id: str,
        remaining_model_calls: int,
        call_prefix: str,
    ) -> HistoryUpdate:
        if remaining_model_calls < 1:
            return HistoryUpdate(
                error={
                    "type": "HistoryBudgetExhausted",
                    "message": "No model-call budget remains for B3 summary.",
                }
            )
        user_prompt = json.dumps(
            {
                "task": self.goal,
                "previous_summary": self.summary,
                "new_entries": [item.record() for item in self.pending],
                "instruction": "Update the trajectory summary.",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        calls: list[ModelCall] = []
        initial = self.client.generate(
            image_path=entry.screenshot_path,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"{call_prefix}_step_{entry.step:03d}_initial",
            max_tokens=256,
        )
        calls.append(initial)
        try:
            parsed = parse_summary_response(initial.content)
        except ActionValidationError as initial_error:
            if remaining_model_calls < 2:
                return HistoryUpdate(
                    calls=calls,
                    error={
                        "type": "SummaryValidationError",
                        "message": str(initial_error),
                    },
                )
            repaired = self.client.generate(
                image_path=entry.screenshot_path,
                system_prompt=self.system_prompt,
                user_prompt=(
                    user_prompt
                    + "\nPrevious output was invalid:\n"
                    + initial.content
                    + "\nValidation error: "
                    + str(initial_error)
                    + "\nReturn only corrected summary.v1 JSON."
                ),
                episode_id=episode_id,
                call_label=f"{call_prefix}_step_{entry.step:03d}_repair",
                max_tokens=256,
            )
            calls.append(repaired)
            try:
                parsed = parse_summary_response(repaired.content)
            except ActionValidationError as repair_error:
                return HistoryUpdate(
                    calls=calls,
                    error={
                        "type": "SummaryValidationError",
                        "initial": str(initial_error),
                        "repair": str(repair_error),
                    },
                )
        self.summary = parsed.value
        self.pending.clear()
        return HistoryUpdate(
            calls=calls,
            summary_updated=True,
            summary_schema_sha256=parsed.schema_sha256,
        )


class ContextMatchedSummaryPolicy(SimpleSummaryPolicy):
    """Predeclared high-context summary control with neutral fixed padding."""

    variant = "B3_CTX"

    def __init__(self, *, target_chars: int = 10000, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.target_chars = target_chars

    def context(self) -> HistoryContext:
        base = super().context()
        if not self.entries:
            return base
        payload = json.loads(base.rendered)
        payload["control"] = "predeclared_context_budget_padding_v1"
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        remaining = max(0, self.target_chars - len(encoded) - 32)
        payload["neutral_padding"] = (
            "[unused context-budget control] " * 400
        )[:remaining]
        return HistoryContext(
            rendered=json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            images=base.images,
        )


class CallMatchedSummaryPolicy(SimpleSummaryPolicy):
    """Summary-only control using M0's shared deterministic call triggers."""

    variant = "B3_CALL"

    def observe(
        self,
        entry: HistoryEntry,
        *,
        episode_id: str,
        remaining_model_calls: int,
    ) -> HistoryUpdate:
        prior = self.entries[-1] if self.entries else None
        self.entries.append(entry)
        self.pending.append(entry)
        loop_trigger = bool(
            prior
            and prior.action == entry.action
            and entry.before_screenshot_sha256 == entry.screenshot_sha256
        )
        periodic_trigger = entry.step == 0 or (entry.step + 1) % 5 == 0
        if not (periodic_trigger or loop_trigger):
            return HistoryUpdate()
        update = self._summarize_pending(
            entry=entry,
            episode_id=episode_id,
            remaining_model_calls=remaining_model_calls,
            call_prefix="b3_call_control",
        )
        details = {
            "call_control_trigger": (
                "repeated_no_effect_loop"
                if loop_trigger
                else "first_or_periodic"
            )
        }
        return HistoryUpdate(
            calls=update.calls,
            summary_updated=update.summary_updated,
            error=update.error,
            summary_schema_sha256=update.summary_schema_sha256,
            details=details,
        )


class RavenMemoryPolicy(HistoryPolicy):
    """Strict one-call RAVEN memory policy with deterministic management."""

    variant = "S0"

    def __init__(
        self,
        *,
        config: MemoryConfig | None = None,
        variant: str = "S0",
    ) -> None:
        self.manager = RavenMemoryManager(config)
        self.variant = variant
        self.last_routed_ids: set[str] = set()
        self.last_fact_ids: set[str] = set()

    def reset(
        self,
        *,
        episode_dir: Path,
        goal: str,
        episode_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        if not episode_id or not task_id:
            raise ValueError("RAVEN memory requires episode_id and task_id.")
        super().reset(
            episode_dir=episode_dir,
            goal=goal,
            episode_id=episode_id,
            task_id=task_id,
        )
        self.manager.reset(
            episode_id=episode_id,
            task_id=task_id,
            task_goal=goal,
            episode_dir=episode_dir,
        )
        self.last_routed_ids = set()
        self.last_fact_ids = set()

    def context(self) -> HistoryContext:
        rendered, routed = self.manager.context(step=len(self.entries))
        self.last_routed_ids = {
            value.item.memory_id
            for value in routed
            if value.route != "SUPPRESS"
        }
        self.last_fact_ids = {
            value.item.memory_id for value in routed if value.route == "FACT"
        }
        return HistoryContext(rendered=rendered)

    def validate_decision(self, decision: dict[str, Any]) -> None:
        cited = set(decision.get("memory_citations", []))
        action = decision.get("action")
        if isinstance(action, dict):
            cited.update(action.get("source_memory_ids", []))
        for evidence in decision.get("completion_evidence", []):
            cited.update(evidence.get("memory_ids", []))
        unknown = cited - self.last_routed_ids
        if unknown:
            raise ActionValidationError(
                "memory_citations contains unavailable IDs: "
                + ", ".join(sorted(unknown))
            )

    def observe(
        self,
        entry: HistoryEntry,
        *,
        episode_id: str,
        remaining_model_calls: int,
    ) -> HistoryUpdate:
        del episode_id, remaining_model_calls
        self.entries.append(entry)
        details = self.manager.observe_transition(
            TransitionObservation(
                step=entry.step,
                decision_summary=entry.decision_summary,
                action=entry.action,
                expected_outcome=entry.expected_outcome,
                observed_outcome=entry.observed_outcome,
                evidence_outcome=entry.evidence_outcome,
                before_screenshot_path=(
                    entry.before_screenshot_path.name
                    if entry.before_screenshot_path
                    else entry.screenshot_path.name
                ),
                before_screenshot_sha256=(
                    entry.before_screenshot_sha256 or entry.screenshot_sha256
                ),
                before_semantic_ui_sha256=entry.before_semantic_ui_sha256,
                after_screenshot_sha256=entry.screenshot_sha256,
                after_semantic_ui_sha256=entry.semantic_ui_sha256,
                after_screenshot_path=entry.screenshot_path.name,
                visible_failure_texts=entry.visible_failure_texts,
                state_delta=entry.state_delta,
            ),
            model_call_id=entry.model_call_id,
        )
        return HistoryUpdate(details=details)


class FullRavenMemoryPolicy(RavenMemoryPolicy):
    """RAVEN-M Full with conditional Planner and Critic role calls."""

    variant = "M0"

    def __init__(
        self,
        *,
        client: TransformersClient,
        planner_prompt: str,
        critic_prompt: str,
        config: MemoryConfig | None = None,
        critic_enabled: bool = True,
        variant: str = "M0",
    ) -> None:
        super().__init__(config=config, variant=variant)
        self.critic_enabled = critic_enabled
        self.roles = RoleOrchestrator(
            client=client,
            planner_prompt=planner_prompt,
            critic_prompt=critic_prompt,
        )

    def reset(
        self,
        *,
        episode_dir: Path,
        goal: str,
        episode_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().reset(
            episode_dir=episode_dir,
            goal=goal,
            episode_id=episode_id,
            task_id=task_id,
        )
        self.plan_state: dict[str, Any] | None = None
        self.critic_alert: dict[str, Any] | None = None

    def context(self) -> HistoryContext:
        base = super().context()
        payload = json.loads(base.rendered)
        payload["planner_state"] = self.plan_state
        payload["critic_alert"] = self.critic_alert
        return HistoryContext(
            rendered=json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    def validate_decision(self, decision: dict[str, Any]) -> None:
        super().validate_decision(decision)
        if decision.get("status") != "done":
            return
        cited = set(decision.get("memory_citations", []))
        if not (cited & self.last_fact_ids):
            raise ActionValidationError(
                "Completion requires at least one currently routed FACT "
                "memory citation; continue and gather visible evidence."
            )
        if (
            self.critic_alert
            and self.critic_alert.get("verdict") == "reject_completion"
        ):
            raise ActionValidationError(
                "The latest completion Critic rejected completion; continue "
                "and satisfy its constraint."
            )

    def observe(
        self,
        entry: HistoryEntry,
        *,
        episode_id: str,
        remaining_model_calls: int,
    ) -> HistoryUpdate:
        base = super().observe(
            entry,
            episode_id=episode_id,
            remaining_model_calls=remaining_model_calls,
        )
        details = dict(base.details or {})
        planner_trigger = entry.step == 0 or (entry.step + 1) % 5 == 0
        critic_trigger = bool(
            details.get("loop_detected")
            or details.get("failure_detected")
            or details.get("contradiction_detected")
            or details.get("completion_evidence_detected")
        )
        bundle_text, routed = self.manager.context(step=entry.step + 1)
        allowed_ids = {
            value.item.memory_id
            for value in routed
            if value.route != "SUPPRESS"
        }
        role_calls: list[ModelCall] = []
        role_records: list[dict[str, Any]] = []
        common_payload = {
            "task": self.goal,
            "step": entry.step,
            "latest_transition": entry.record(),
            "memory_bundle": json.loads(bundle_text),
            "previous_plan": self.plan_state,
        }
        if planner_trigger:
            planner = self.roles.call(
                role="planner",
                image_path=entry.screenshot_path,
                payload={**common_payload, "trigger": "plan_refresh"},
                episode_id=episode_id,
                step=entry.step,
                remaining_model_calls=(
                    remaining_model_calls - len(role_calls)
                ),
                allowed_memory_ids=allowed_ids,
            )
            role_calls.extend(planner.calls)
            if planner.output is not None:
                self.plan_state = planner.output
            role_records.append(
                {
                    "role": "planner",
                    "trigger": "plan_refresh",
                    "output": planner.output,
                    "error": planner.error,
                    "model_calls": [
                        call.audit_record() for call in planner.calls
                    ],
                }
            )
        if critic_trigger and self.critic_enabled:
            trigger = (
                "contradiction"
                if details.get("contradiction_detected")
                else (
                    "visible_validation_failure"
                    if details.get("failure_detected")
                    else (
                        "semantic_no_progress_loop"
                        if details.get("loop_detected")
                        else "completion_evidence"
                    )
                )
            )
            critic = self.roles.call(
                role="critic",
                image_path=entry.screenshot_path,
                payload={**common_payload, "trigger": trigger},
                episode_id=episode_id,
                step=entry.step,
                remaining_model_calls=(
                    remaining_model_calls - len(role_calls)
                ),
                allowed_memory_ids=allowed_ids,
            )
            role_calls.extend(critic.calls)
            if critic.output is not None:
                self.critic_alert = critic.output
            role_records.append(
                {
                    "role": "critic",
                    "trigger": trigger,
                    "output": critic.output,
                    "error": critic.error,
                    "model_calls": [
                        call.audit_record() for call in critic.calls
                    ],
                }
            )
        details["role_events"] = role_records
        details["role_call_counts"] = {
            "planner": sum(
                len(record["model_calls"])
                for record in role_records
                if record["role"] == "planner"
            ),
            "critic": sum(
                len(record["model_calls"])
                for record in role_records
                if record["role"] == "critic"
            ),
        }
        return HistoryUpdate(calls=role_calls, details=details)


class FullRavenMemoryPolicyV2(FullRavenMemoryPolicy):
    """Protocol-v2 full method with same-turn completion adjudication."""

    def validate_decision(self, decision: dict[str, Any]) -> None:
        RavenMemoryPolicy.validate_decision(self, decision)
        if decision.get("status") != "done":
            return
        evidence = decision.get("completion_evidence", [])
        cited = set(decision.get("memory_citations", []))
        for item in evidence:
            cited.update(item.get("memory_ids", []))
        has_fact = bool(cited & self.last_fact_ids)
        has_direct = any(
            item.get("evidence") in {"direct_screen", "mixed"}
            for item in evidence
        )
        if not (has_fact or has_direct):
            raise ActionValidationError(
                "Protocol v2 completion requires current-screen evidence "
                "or a currently routed FACT."
            )

    def adjudicate_completion(
        self,
        decision: dict[str, Any],
        *,
        image_path: Path,
        episode_id: str,
        step: int,
        remaining_model_calls: int,
    ) -> CompletionAdjudication:
        if decision.get("status") != "done":
            return CompletionAdjudication()
        bundle_text, routed = self.manager.context(step=len(self.entries))
        allowed_ids = {
            value.item.memory_id
            for value in routed
            if value.route != "SUPPRESS"
        }
        latest_transition = (
            self.entries[-1].record() if self.entries else None
        )
        critic = self.roles.call(
            role="critic",
            image_path=image_path,
            payload={
                "task": self.goal,
                "step": step,
                "trigger": "completion_candidate",
                "completion_candidate": decision,
                "latest_transition": latest_transition,
                "memory_bundle": json.loads(bundle_text),
                "planner_state": self.plan_state,
            },
            episode_id=episode_id,
            step=step,
            remaining_model_calls=remaining_model_calls,
            allowed_memory_ids=allowed_ids,
        )
        record = {
            "schema_version": "completion_adjudication.v2",
            "trigger": "completion_candidate",
            "output": critic.output,
            "error": critic.error,
            "model_call_ids": [call.call_id for call in critic.calls],
        }
        if critic.output is not None:
            self.critic_alert = critic.output
        if critic.error is not None or critic.output is None:
            return CompletionAdjudication(
                accepted=False,
                calls=list(critic.calls),
                record=record,
                error="Completion critic did not return a valid verdict.",
            )
        if critic.output.get("verdict") != "proceed":
            constraint = critic.output.get(
                "recommended_constraint",
                "satisfy the unresolved completion requirement",
            )
            return CompletionAdjudication(
                accepted=False,
                calls=list(critic.calls),
                record=record,
                error=f"Completion critic rejected completion: {constraint}",
            )
        return CompletionAdjudication(
            accepted=True,
            calls=list(critic.calls),
            record=record,
        )


def make_history_policy(
    variant: str,
    *,
    client: TransformersClient,
    summary_system_prompt: str,
    planner_system_prompt: str = "",
    critic_system_prompt: str = "",
) -> HistoryPolicy:
    normalized = variant.upper()
    if normalized == "B0":
        return HistoryPolicy()
    if normalized == "B1":
        return SlidingWindowPolicy(k=3)
    if normalized == "B2":
        return RawFullHistoryPolicy(max_chars=12000, max_images=8)
    if normalized == "B3":
        return SimpleSummaryPolicy(
            client=client,
            system_prompt=summary_system_prompt,
            trigger_every=5,
            keep_recent=2,
        )
    if normalized in {"B3_CTX", "B3-CTX"}:
        return ContextMatchedSummaryPolicy(
            client=client,
            system_prompt=summary_system_prompt,
            trigger_every=5,
            keep_recent=2,
            target_chars=10000,
        )
    if normalized in {"B3_CALL", "B3-CALL"}:
        return CallMatchedSummaryPolicy(
            client=client,
            system_prompt=summary_system_prompt,
            trigger_every=5,
            keep_recent=2,
        )
    if normalized in {"S0", "RAVEN_STRICT"}:
        return RavenMemoryPolicy(config=MemoryConfig(), variant="S0")
    if normalized in {"M0", "RAVEN_FULL"}:
        if not planner_system_prompt or not critic_system_prompt:
            raise ValueError("M0 requires Planner and Critic system prompts.")
        return FullRavenMemoryPolicy(
            client=client,
            planner_prompt=planner_system_prompt,
            critic_prompt=critic_system_prompt,
            config=MemoryConfig(),
        )
    ablation_configs = {
        "MREL": MemoryConfig(reliability_aware=False),
        "MNO_WM": MemoryConfig(working_quota=0),
        "MNO_VEL": MemoryConfig(episodic_quota=0),
        "MNO_FRM": MemoryConfig(failure_quota=0),
        "MNO_PSI": MemoryConfig(page_hint_quota=0),
        "MNO_CRITIC": MemoryConfig(),
    }
    if normalized in ablation_configs:
        if not planner_system_prompt or not critic_system_prompt:
            raise ValueError(
                f"{normalized} requires Planner and Critic system prompts."
            )
        return FullRavenMemoryPolicy(
            client=client,
            planner_prompt=planner_system_prompt,
            critic_prompt=critic_system_prompt,
            config=ablation_configs[normalized],
            critic_enabled=normalized != "MNO_CRITIC",
            variant=normalized,
        )
    raise ValueError(f"Unknown baseline history variant: {variant}")


def make_history_policy_v2(
    variant: str,
    *,
    client: TransformersClient,
    summary_system_prompt: str,
    planner_system_prompt: str = "",
    critic_system_prompt: str = "",
) -> HistoryPolicy:
    """Build protocol-v2 policies without changing protocol-v1 factories."""
    normalized = variant.upper()
    if normalized not in {"M0", "RAVEN_FULL", "MREL"}:
        return make_history_policy(
            normalized,
            client=client,
            summary_system_prompt=summary_system_prompt,
            planner_system_prompt=planner_system_prompt,
            critic_system_prompt=critic_system_prompt,
        )
    if not planner_system_prompt or not critic_system_prompt:
        raise ValueError(
            f"{normalized} requires Planner and Critic system prompts."
        )
    config = (
        MemoryConfig(reliability_aware=False)
        if normalized == "MREL"
        else MemoryConfig()
    )
    return FullRavenMemoryPolicyV2(
        client=client,
        planner_prompt=planner_system_prompt,
        critic_prompt=critic_system_prompt,
        config=config,
        variant=("MREL" if normalized == "MREL" else "M0"),
    )
