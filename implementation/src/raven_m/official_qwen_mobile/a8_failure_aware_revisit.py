"""Failure-aware exact-screen revisit memory proposed for A8-v2.

This module is deliberately isolated from the frozen A8-v1 implementation.
It consumes only model-visible RGB pixels and the policy's own executed action
and visible-pixel transition.  It is advisory memory: it never blocks,
repairs, or replaces an action.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any

import numpy as np


def _compact(value: Any, limit: int) -> str:
    rendered = " ".join(str(value).split()).strip()
    if len(rendered) > limit:
        return rendered[: max(0, limit - 3)].rstrip() + "..."
    return rendered


def _json_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def exact_visible_fingerprint(snapshot: dict[str, Any]) -> str:
    """Hash exact stable model-visible pixels, excluding thin system bars."""
    pixels = np.asarray(snapshot.get("pixels"))
    if (
        pixels.ndim != 3
        or pixels.shape[0] < 25
        or pixels.shape[1] < 8
        or pixels.shape[2] < 3
    ):
        raise RuntimeError("A8-v2 requires model-visible RGB screenshot pixels")
    top = int(round(pixels.shape[0] * 0.04))
    bottom = int(round(pixels.shape[0] * 0.96))
    crop = np.ascontiguousarray(pixels[top:bottom, :, :3])
    descriptor = f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    return sha256(descriptor).hexdigest()


def _visible_outcome(transition: dict[str, Any]) -> str:
    if transition.get("exactly_unchanged") is True:
        return "no_visible_change"
    fraction = transition.get("changed_pixel_fraction_gt_5")
    if isinstance(fraction, (int, float)) and float(fraction) <= 0.001:
        return "negligible_visible_change"
    return "visible_change"


def _rounded_coordinate(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value), 2)


def _action_family(action: dict[str, Any]) -> tuple[str, str]:
    """Group tiny coordinate jitter without using UI semantics or hidden state."""
    action_type = _compact(action.get("type") or "unknown", 24)
    family: dict[str, Any] = {"type": action_type}
    for name in ("x", "y", "x2", "y2"):
        coordinate = _rounded_coordinate(action.get(name))
        if coordinate is not None:
            family[name] = coordinate
    if "text" in action:
        family["text_sha256"] = sha256(str(action.get("text") or "").encode()).hexdigest()
    if "key" in action:
        family["key"] = _compact(action.get("key"), 32)
    family_id = f"a8f_{_json_sha(family)[:12]}"

    if all(name in family for name in ("x", "y", "x2", "y2")):
        label = (
            f"{action_type}@({family['x']:.2f},{family['y']:.2f})->"
            f"({family['x2']:.2f},{family['y2']:.2f})"
        )
    elif all(name in family for name in ("x", "y")):
        label = f"{action_type}@({family['x']:.2f},{family['y']:.2f})"
    elif "key" in family:
        label = f"{action_type}:{family['key']}"
    else:
        label = action_type
    return family_id, label


@dataclass
class ActionEvidence:
    family_id: str
    label: str
    latest_intent: str
    attempt_count: int = 0
    no_visible_change_count: int = 0
    negligible_visible_change_count: int = 0
    visible_change_count: int = 0
    last_source_step: int = -1
    canonical_action_sha256s: list[str] = field(default_factory=list)

    @property
    def no_progress_count(self) -> int:
        return self.no_visible_change_count + self.negligible_visible_change_count


@dataclass
class ScreenEvidence:
    fingerprint: str
    first_source_step: int
    last_source_step: int
    write_visit_count: int = 0
    read_hit_count: int = 0
    actions: dict[str, ActionEvidence] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitionReceipt:
    source_step: int
    source_fingerprint: str
    destination_fingerprint: str
    action_family_id: str
    action_label: str
    action_intent: str
    visible_outcome: str
    canonical_action_sha256: str
    source_response_sha256: str


class FailureAwareExactRevisitMemory:
    """A8-v2 prototype: aggregate failed action families on exact revisits."""

    mechanism_id = "a8_failure_aware_exact_revisit_memory_v2"
    max_canonical_hashes_per_action_family = 4

    def __init__(
        self,
        *,
        max_states: int = 12,
        max_actions_per_state: int = 4,
        max_transitions: int = 24,
        max_rendered_actions: int = 3,
        max_chars: int = 360,
    ) -> None:
        self.max_states = max(1, int(max_states))
        self.max_actions_per_state = max(1, int(max_actions_per_state))
        self.max_transitions = max(2, int(max_transitions))
        self.max_rendered_actions = max(1, int(max_rendered_actions))
        # Keep room for the evidence boundary even when a caller requests an
        # unrealistically small prompt budget.
        self.max_chars = max(256, int(max_chars))
        self._states: OrderedDict[str, ScreenEvidence] = OrderedDict()
        self._transitions: list[TransitionReceipt] = []
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0
        self.exact_revisit_count = 0
        self.closed_route_count = 0

    def _finish_read(
        self,
        rendered: str,
        *,
        retrieved_ids: list[str],
        details: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        rendered = rendered[: self.max_chars]
        self.read_count += 1
        if rendered:
            self.nonempty_read_count += 1
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "nonempty": bool(rendered),
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": retrieved_ids,
            "retrieved_count": len(retrieved_ids),
            **details,
        }

    def _latest_closed_route(self, fingerprint: str) -> dict[str, Any] | None:
        if not self._transitions or self._transitions[-1].destination_fingerprint != fingerprint:
            return None
        end = len(self._transitions) - 1
        for start in range(end, -1, -1):
            if self._transitions[start].source_fingerprint != fingerprint:
                continue
            chain = self._transitions[start : end + 1]
            if all(
                chain[index].destination_fingerprint == chain[index + 1].source_fingerprint
                for index in range(len(chain) - 1)
            ):
                first = chain[0]
                return {
                    "action_count": len(chain),
                    "first_action_family_id": first.action_family_id,
                    "first_action_label": first.action_label,
                    "first_action_intent": first.action_intent,
                    "source_step": first.source_step,
                }
        return None

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        fingerprint = exact_visible_fingerprint(dict(context.get("before") or {}))
        bucket = self._states.get(fingerprint)
        if bucket is None:
            return self._finish_read(
                "",
                retrieved_ids=[],
                details={
                    "query_fingerprint": fingerprint,
                    "exact_match": False,
                    "closed_route": None,
                },
            )

        bucket.read_hit_count += 1
        self.exact_revisit_count += 1
        ranked = sorted(
            bucket.actions.values(),
            key=lambda item: (item.no_progress_count, item.attempt_count, item.last_source_step),
            reverse=True,
        )[: self.max_rendered_actions]
        fragments = []
        for item in ranked:
            counts = []
            if item.no_progress_count:
                counts.append(f"no/negligible visible change {item.no_progress_count}x")
            if item.visible_change_count:
                counts.append(f"visible change {item.visible_change_count}x")
            result = ", ".join(counts) if counts else "outcome unavailable"
            fragments.append(
                f"{item.label} tried {item.attempt_count}x -> {result}; "
                f"latest intent: {_compact(item.latest_intent, 52)}"
            )

        closed_route = self._latest_closed_route(fingerprint)
        if closed_route is not None:
            self.closed_route_count += 1
            fragments.append(
                "a prior route returned to this exact screen after "
                f"{closed_route['action_count']} action(s), beginning with "
                f"{closed_route['first_action_label']}"
            )
        prefix = "Exact-screen revisit evidence (observations only; current pixels authoritative): "
        suffix = " | Visible change is not task-completion evidence; no action is blocked or replaced."
        body_budget = max(0, self.max_chars - len(prefix) - len(suffix))
        body = " | ".join(fragments)[:body_budget].rstrip()
        rendered = prefix + body + suffix
        return self._finish_read(
            rendered,
            retrieved_ids=[item.family_id for item in ranked],
            details={
                "query_fingerprint": fingerprint,
                "exact_match": True,
                "state_write_visit_count": bucket.write_visit_count,
                "state_action_family_count": len(bucket.actions),
                "closed_route": closed_route,
            },
        )

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        source_step = int(kwargs["source_step"])
        source = exact_visible_fingerprint(dict(kwargs.get("before") or {}))
        destination = exact_visible_fingerprint(dict(kwargs.get("after") or {}))
        action = dict(kwargs.get("canonical_action") or {})
        action_sha = _json_sha(action)
        family_id, label = _action_family(action)
        intent = _compact(kwargs.get("action_summary") or label, 72)
        outcome = _visible_outcome(dict(kwargs.get("transition") or {}))

        bucket = self._states.get(source)
        if bucket is None:
            bucket = ScreenEvidence(
                fingerprint=source,
                first_source_step=source_step,
                last_source_step=source_step,
            )
            self._states[source] = bucket
        else:
            bucket.last_source_step = source_step
            self._states.move_to_end(source)
        bucket.write_visit_count += 1

        evidence = bucket.actions.get(family_id)
        if evidence is None:
            evidence = ActionEvidence(
                family_id=family_id,
                label=label,
                latest_intent=intent,
            )
            bucket.actions[family_id] = evidence
        evidence.latest_intent = intent
        evidence.attempt_count += 1
        evidence.last_source_step = source_step
        counter_name = f"{outcome}_count"
        setattr(evidence, counter_name, int(getattr(evidence, counter_name)) + 1)
        if action_sha not in evidence.canonical_action_sha256s:
            evidence.canonical_action_sha256s.append(action_sha)
            evidence.canonical_action_sha256s = evidence.canonical_action_sha256s[
                -self.max_canonical_hashes_per_action_family :
            ]

        if len(bucket.actions) > self.max_actions_per_state:
            victim = min(
                bucket.actions.values(),
                key=lambda item: (
                    item.no_progress_count,
                    item.attempt_count,
                    item.last_source_step,
                    item.family_id,
                ),
            )
            del bucket.actions[victim.family_id]
        while len(self._states) > self.max_states:
            self._states.popitem(last=False)

        receipt = TransitionReceipt(
            source_step=source_step,
            source_fingerprint=source,
            destination_fingerprint=destination,
            action_family_id=family_id,
            action_label=label,
            action_intent=intent,
            visible_outcome=outcome,
            canonical_action_sha256=action_sha,
            source_response_sha256=str(kwargs.get("source_response_sha256") or ""),
        )
        self._transitions.append(receipt)
        self._transitions = self._transitions[-self.max_transitions :]
        self.write_success_count += 1
        return {
            "written": True,
            "source_fingerprint": source,
            "destination_fingerprint": destination,
            "action_family_id": family_id,
            "action_evidence": asdict(evidence),
            "state_count": len(self._states),
        }

    def audit_record(self) -> dict[str, Any]:
        states = []
        for bucket in self._states.values():
            states.append(
                {
                    "fingerprint": bucket.fingerprint,
                    "first_source_step": bucket.first_source_step,
                    "last_source_step": bucket.last_source_step,
                    "write_visit_count": bucket.write_visit_count,
                    "read_hit_count": bucket.read_hit_count,
                    "actions": [asdict(item) for item in bucket.actions.values()],
                }
            )
        return {
            "mechanism_id": self.mechanism_id,
            "max_states": self.max_states,
            "max_actions_per_state": self.max_actions_per_state,
            "max_transitions": self.max_transitions,
            "max_rendered_actions": self.max_rendered_actions,
            "max_canonical_hashes_per_action_family": (
                self.max_canonical_hashes_per_action_family
            ),
            "max_chars": self.max_chars,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "exact_revisit_count": self.exact_revisit_count,
            "closed_route_count": self.closed_route_count,
            "states": states,
            "transitions": [asdict(item) for item in self._transitions],
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "fingerprint": "sha256_exact_middle_92_percent_model_visible_rgb_pixels",
            "action_family": "canonical_action_type_plus_coordinates_rounded_to_0.01",
            "near_match_enabled": False,
            "model_calls_added": 0,
            "evaluator_used_for_decision": False,
            "hidden_ui_used_for_decision": False,
            "guard_enabled": False,
            "action_override_count": 0,
            "evidence_boundary": "policy_action_plus_model_visible_pixel_transition_only",
            "claim_boundary": "visible_outcome_and_exact_route_return_never_task_completion",
        }
