"""Deterministic memory lifecycle manager used by Strict and Full RAVEN-M."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from raven_m.memory.models import (
    MemoryConfig,
    MemoryItem,
    MemorySource,
    RetrievalQuery,
    RoutedMemory,
)
from raven_m.memory.retrieval import render_bundle, retrieve_and_route
from raven_m.memory.store import EpisodeMemoryStore


@dataclass(frozen=True)
class TransitionObservation:
    step: int
    decision_summary: str
    action: dict[str, Any]
    expected_outcome: str
    observed_outcome: str
    evidence_outcome: str
    before_screenshot_path: str
    before_screenshot_sha256: str
    after_screenshot_sha256: str
    after_screenshot_path: str
    before_semantic_ui_sha256: str = ""
    after_semantic_ui_sha256: str = ""
    visible_failure_texts: tuple[str, ...] = ()
    state_delta: tuple[dict[str, Any], ...] = ()


class RavenMemoryManager:
    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or MemoryConfig()

    def reset(
        self,
        *,
        episode_id: str,
        task_id: str,
        task_goal: str,
        episode_dir: Path,
    ) -> None:
        self.episode_id = episode_id
        self.task_id = task_id
        self.task_goal = task_goal
        self.episode_dir = episode_dir
        self.store = EpisodeMemoryStore(
            episode_id=episode_id,
            event_path=episode_dir / "memory_events.jsonl",
        )
        self.working: list[dict[str, Any]] = []
        self.action_signatures: list[str] = []
        self.last_page_signature: str | None = None

    @staticmethod
    def page_signature(
        screenshot_sha256: str,
        *,
        semantic: bool = False,
    ) -> str:
        prefix = "ui" if semantic else "screen"
        return f"{prefix}:{screenshot_sha256[:16]}"

    @staticmethod
    def action_signature(action: dict[str, Any]) -> str:
        encoded = json.dumps(
            action,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(encoded.encode("utf-8")).hexdigest()[:16]

    def _source(
        self,
        *,
        step: int,
        screenshot_path: str,
        screenshot_sha256: str,
        model_call_id: str | None,
        extractor: str,
    ) -> MemorySource:
        return MemorySource(
            observation_ids=(f"obs_{step + 1:06d}",),
            action_ids=(f"act_{step:06d}",),
            screenshot_paths=(screenshot_path,),
            screenshot_sha256=(screenshot_sha256,),
            model_call_id=model_call_id,
            extractor=extractor,
        )

    def _write_delta(
        self,
        delta: dict[str, Any],
        *,
        transition: TransitionObservation,
        page_signature: str,
        model_call_id: str | None,
    ) -> str | None:
        required = {"kind", "subject", "predicate", "object", "natural_language"}
        if not required.issubset(delta):
            return None
        kind = str(delta["kind"])
        memory_type = {
            "fact": "episodic_fact",
            "progress": "episodic_fact",
            "failure": "failure",
            "page_hypothesis": "page_hint",
        }.get(kind)
        if memory_type is None:
            return None
        quotas = {
            "episodic_fact": self.config.episodic_quota,
            "failure": self.config.failure_quota,
            "page_hint": self.config.page_hint_quota,
        }
        if quotas[memory_type] <= 0:
            return None
        evidence_label = delta.get("evidence", "model_inference")
        origin = {
            "direct_screen": "direct_visual_observation",
            "action_outcome": "direct_action_outcome",
            "inference": "model_inference",
        }.get(evidence_label, "model_inference")
        status = (
            "observed"
            if origin in {"direct_visual_observation", "direct_action_outcome"}
            else "candidate"
        )
        subject = str(delta["subject"])
        predicate = str(delta["predicate"])
        page_local = (
            kind == "page_hypothesis"
            or (
                subject.strip().lower()
                in {"page", "screen", "current_page", "current_screen"}
                and predicate.strip().lower()
                in {"identity", "visible", "visibility", "state"}
            )
        )
        preconditions = list(delta.get("preconditions", ["same_task"]))
        expires_on = list(delta.get("expires_on", []))
        if page_local:
            if "same_page" not in preconditions:
                preconditions.append("same_page")
            if "semantic_page_changed" not in expires_on:
                expires_on.append("semantic_page_changed")
        current_source = self._source(
            step=transition.step,
            screenshot_path=transition.before_screenshot_path,
            screenshot_sha256=transition.before_screenshot_sha256,
            model_call_id=model_call_id,
            extractor="executor_state_delta_v2",
        )
        if origin in {"direct_visual_observation", "direct_action_outcome"}:
            for existing in self.store.active_items():
                if existing.verification_status not in {
                    "candidate",
                    "observed",
                    "verified",
                }:
                    continue
                same_claim = (
                    existing.memory_type == memory_type
                    and existing.content["subject"] == subject
                    and existing.content["predicate"] == predicate
                    and existing.content["object"] == delta["object"]
                    and existing.page_signature == page_signature
                )
                repeated_model_observation = (
                    same_claim
                    and transition.step > existing.last_confirmed_step
                    and transition.before_screenshot_sha256
                    not in existing.source.screenshot_sha256
                )
                if not repeated_model_observation:
                    continue
                repetitions = int(
                    existing.evidence.get("model_reobservations", 0)
                ) + 1
                evidence = {
                    **existing.evidence,
                    # Repeating a model-authored interpretation on a later
                    # screenshot is useful provenance, but it is not
                    # independent verification. Keep it out of FACT routing.
                    "model_reobservations": repetitions,
                }
                combined_source = MemorySource(
                    observation_ids=tuple(
                        dict.fromkeys(
                            (
                                *existing.source.observation_ids,
                                *current_source.observation_ids,
                            )
                        )
                    ),
                    action_ids=tuple(
                        dict.fromkeys(
                            (
                                *existing.source.action_ids,
                                *current_source.action_ids,
                            )
                        )
                    ),
                    screenshot_paths=(
                        *existing.source.screenshot_paths,
                        *current_source.screenshot_paths,
                    ),
                    screenshot_sha256=(
                        *existing.source.screenshot_sha256,
                        *current_source.screenshot_sha256,
                    ),
                    model_call_id=model_call_id,
                    extractor="executor_state_delta_reobservation_v3",
                )
                self.store.transition(
                    existing.memory_id,
                    status="observed",
                    step=transition.step,
                    reason="repeated_model_observation",
                    patch={
                        "evidence": evidence,
                        "source": combined_source,
                    },
                )
                return existing.memory_id
        # state_delta is emitted from the decision-time observation. Its
        # screenshot provenance is therefore always the *before* frame. An
        # action_outcome label refers to PREVIOUS_ACTION_AND_OBSERVED_OUTCOME
        # supplied to that decision, never the not-yet-executed current action.
        item = MemoryItem(
            memory_id=self.store.allocate_id(
                "f" if memory_type == "failure" else "m"
            ),
            episode_id=self.episode_id,
            memory_type=memory_type,
            content={
                "subject": subject,
                "predicate": predicate,
                "object": delta["object"],
                "natural_language": str(delta["natural_language"]),
            },
            task_id=self.task_id,
            subgoal_id=delta.get("subgoal_id"),
            app_id_observed=delta.get("app_id_observed"),
            page_signature=page_signature,
            created_step=transition.step,
            last_confirmed_step=transition.step,
            source=current_source,
            evidence={
                "origin": origin,
                "action_outcome": (
                    transition.evidence_outcome
                    if evidence_label == "action_outcome"
                    else None
                ),
                "independent_confirmations": 0,
            },
            verification_status=status,
            confidence_model=float(delta.get("confidence", 0.5)),
            validity={
                "scope": "episode",
                "preconditions": preconditions,
                "expires_on": expires_on,
            },
            relations={
                "supersedes": None,
                "superseded_by": None,
                "contradicts": [],
                "supports_completion_requirements": list(
                    delta.get("supports_completion_requirements", [])
                ),
            },
        )
        conflicts = self.store.find_conflicts(item)
        self.store.write(item)
        for existing in conflicts:
            self.store.mark_contradiction(
                existing.memory_id,
                item.memory_id,
                step=transition.step,
            )
        return item.memory_id

    def observe_transition(
        self,
        transition: TransitionObservation,
        *,
        model_call_id: str | None = None,
    ) -> dict[str, Any]:
        semantic_available = bool(
            transition.before_semantic_ui_sha256
            and transition.after_semantic_ui_sha256
        )
        before_state_sha = (
            transition.before_semantic_ui_sha256
            if semantic_available
            else transition.before_screenshot_sha256
        )
        after_state_sha = (
            transition.after_semantic_ui_sha256
            if semantic_available
            else transition.after_screenshot_sha256
        )
        before_page_signature = self.page_signature(
            before_state_sha,
            semantic=semantic_available,
        )
        after_page_signature = self.page_signature(
            after_state_sha,
            semantic=semantic_available,
        )
        action_signature = self.action_signature(transition.action)
        no_semantic_change = before_state_sha == after_state_sha
        if self.config.working_quota > 0:
            self.working.append(
                {
                    "step": transition.step,
                    "decision_summary": transition.decision_summary,
                    "action": transition.action,
                    "observed_outcome": transition.observed_outcome,
                    "page_signature": after_page_signature,
                }
            )
            self.working = self.working[-self.config.working_quota :]
        else:
            self.working = []
        self.action_signatures.append(action_signature)
        self.action_signatures = self.action_signatures[-3:]

        contradiction_events_before = sum(
            event["event"] == "contradiction" for event in self.store.events
        )
        written = []
        for delta in transition.state_delta:
            memory_id = self._write_delta(
                delta,
                transition=transition,
                page_signature=before_page_signature,
                model_call_id=model_call_id,
            )
            if memory_id:
                written.append(memory_id)

        failure_detected = bool(transition.visible_failure_texts)
        if failure_detected and self.config.failure_quota > 0:
            failure = MemoryItem(
                memory_id=self.store.allocate_id("f"),
                episode_id=self.episode_id,
                memory_type="failure",
                content={
                    "subject": after_page_signature,
                    "predicate": "visible_validation_failure",
                    "object": {
                        "action": transition.action,
                        "messages": list(
                            transition.visible_failure_texts
                        ),
                    },
                    "natural_language": (
                        "The action produced a visible validation failure: "
                        + " | ".join(transition.visible_failure_texts)
                        + ". Change the invalid input or choose a different "
                        "recovery action before retrying."
                    ),
                },
                task_id=self.task_id,
                created_step=transition.step,
                last_confirmed_step=transition.step,
                page_signature=after_page_signature,
                source=self._source(
                    step=transition.step,
                    screenshot_path=transition.after_screenshot_path,
                    screenshot_sha256=transition.after_screenshot_sha256,
                    model_call_id=model_call_id,
                    extractor="deterministic_visible_failure_v1",
                ),
                evidence={
                    "origin": "direct_visual_observation",
                    "action_outcome": "visible_validation_failure",
                    "independent_confirmations": 1,
                },
                verification_status="observed",
                confidence_model=1.0,
                validity={
                    "scope": "episode",
                    "preconditions": ["same_task", "same_page"],
                    "expires_on": [
                        "semantic_page_changed",
                        "recovery_succeeded",
                    ],
                },
            )
            self.store.write(failure)
            written.append(failure.memory_id)

        # Invalidate after decision-time deltas are written so a page-local
        # assertion cannot survive the transition that already left its page.
        invalidated = self.store.invalidate_page_local(
            current_page_signature=after_page_signature,
            step=transition.step,
        )
        loop_detected = (
            no_semantic_change
            and len(self.action_signatures) >= 2
            and self.action_signatures[-1] == self.action_signatures[-2]
        )
        if loop_detected and self.config.failure_quota > 0:
            failure = MemoryItem(
                memory_id=self.store.allocate_id("f"),
                episode_id=self.episode_id,
                memory_type="failure",
                content={
                    "subject": after_page_signature,
                    "predicate": "action_had_no_effect",
                    "object": transition.action,
                    "natural_language": (
                        (
                            "Repeated action produced no semantic UI change; "
                            "avoid the same action on this page and re-observe "
                            "or recover."
                        )
                        if semantic_available
                        else (
                            "Repeated action produced no visible change; avoid "
                            "the same action on this page and re-observe or "
                            "recover."
                        )
                    ),
                },
                task_id=self.task_id,
                created_step=transition.step,
                last_confirmed_step=transition.step,
                page_signature=after_page_signature,
                source=self._source(
                    step=transition.step,
                    screenshot_path=transition.after_screenshot_path,
                    screenshot_sha256=transition.after_screenshot_sha256,
                    model_call_id=model_call_id,
                    extractor=(
                        "deterministic_semantic_loop_detector_v2"
                        if semantic_available
                        else "deterministic_loop_detector_v1"
                    ),
                ),
                evidence={
                    "origin": "direct_action_outcome",
                    "action_outcome": (
                        "same_action_same_semantic_page_no_progress"
                        if semantic_available
                        else "same_action_same_page_no_visual_change"
                    ),
                    "independent_confirmations": 1,
                },
                verification_status="observed",
                confidence_model=1.0,
                validity={
                    "scope": "episode",
                    "preconditions": ["same_task", "same_page"],
                    "expires_on": ["page_changed", "recovery_succeeded"],
                },
            )
            self.store.write(failure)
            written.append(failure.memory_id)
        self.last_page_signature = after_page_signature
        contradiction_events_after = sum(
            event["event"] == "contradiction" for event in self.store.events
        )
        completion_evidence_ids = [
            memory_id
            for memory_id in written
            if self.store.get(memory_id)
            .relations.get("supports_completion_requirements")
        ]
        return {
            "written_memory_ids": written,
            "invalidated_memory_ids": invalidated,
            "loop_detected": loop_detected,
            "failure_detected": failure_detected,
            "visible_failure_texts": list(
                transition.visible_failure_texts
            ),
            "semantic_state_used": semantic_available,
            "contradiction_detected": (
                contradiction_events_after > contradiction_events_before
            ),
            "completion_evidence_ids": completion_evidence_ids,
            "completion_evidence_detected": bool(completion_evidence_ids),
            "page_signature": after_page_signature,
        }

    def context(
        self,
        *,
        step: int,
        current_subgoal_id: str | None = None,
        required_variables: tuple[str, ...] = (),
        page_signature: str | None = None,
        app_label_observed: str | None = None,
        open_completion_requirements: tuple[str, ...] = (),
        used_by: str = "executor",
    ) -> tuple[str, list[RoutedMemory]]:
        query = RetrievalQuery(
            step_id=step,
            task_terms=tuple(self.task_goal.lower().split()),
            current_subgoal_id=current_subgoal_id,
            required_variables=required_variables,
            page_signature=page_signature or self.last_page_signature,
            app_label_observed=app_label_observed,
            event_flags=("normal_step",),
            open_completion_requirements=open_completion_requirements,
        )
        routed = retrieve_and_route(
            query=query,
            store=self.store,
            config=self.config,
            used_by=used_by,
        )
        bundle = json.loads(render_bundle(routed))
        bundle["working_memory"] = self.working
        return (
            json.dumps(
                bundle,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            routed,
        )
