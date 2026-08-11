"""A9: sparse, controller-authored recurrence canaries for GUI loops.

The mechanism is deliberately narrower than a planner or a guard.  It records
only the policy's executed canonical actions and exact fingerprints of pixels
that were visible to the policy.  It emits a one-shot memory note only after a
frozen recurrence canary fires; it never changes or rejects an action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any

import numpy as np


def _compact(value: Any, limit: int) -> str:
    rendered = " ".join(str(value).split()).strip()
    if len(rendered) <= limit:
        return rendered
    return rendered[: max(0, limit - 3)].rstrip() + "..."


def _normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def _visible_fingerprint(snapshot: dict[str, Any]) -> str:
    """Hash model-visible RGB pixels while excluding thin system bars."""
    pixels = np.asarray(snapshot.get("pixels"))
    if (
        pixels.ndim != 3
        or pixels.shape[0] < 25
        or pixels.shape[1] < 8
        or pixels.shape[2] < 3
    ):
        raise RuntimeError("A9 requires model-visible RGB screenshot pixels")
    top = int(round(pixels.shape[0] * 0.04))
    bottom = int(round(pixels.shape[0] * 0.96))
    crop = np.ascontiguousarray(pixels[top:bottom, :, :3])
    descriptor = f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    return sha256(descriptor).hexdigest()


_CLEAR_INTENT = re.compile(
    r"\b(clear|erase|remove|delete)\b.{0,32}\b(text|field|query|search|input)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class QueryOccurrence:
    source_step: int
    text: str
    normalized_sha256: str
    source_fingerprint: str
    destination_fingerprint: str
    clear_evidence: bool
    source_response_sha256: str


@dataclass(frozen=True)
class CanaryEvent:
    event_id: str
    kind: str
    source_step: int
    evidence_steps: tuple[int, ...]
    evidence_sha256: str
    rendered: str


class SparseRecurrenceCanaryMemory:
    """One-shot query-reentry and exact visual-cycle memory.

    A normal step produces no prompt text.  A canary is raised after either:
    (1) the exact same non-trivial text is typed twice inside a short window;
    (2) one exact screen persists for three observations; or
    (3) an exact screen sequence of period two or three occurs twice.

    These are recurrence facts, not evaluator-derived failure or completion
    claims.  Each recurrence signature is surfaced at most once per episode.
    """

    mechanism_id = "a9_sparse_query_and_navigation_recurrence_canary_v1"

    def __init__(
        self,
        *,
        max_chars: int = 280,
        query_window_steps: int = 12,
        max_query_keys: int = 8,
        max_occurrences_per_query: int = 4,
        max_trace_screens: int = 13,
        max_cycle_period: int = 3,
        pending_capacity: int = 2,
        event_log_capacity: int = 16,
    ) -> None:
        self.max_chars = max(96, int(max_chars))
        self.query_window_steps = max(2, int(query_window_steps))
        self.max_query_keys = max(1, int(max_query_keys))
        self.max_occurrences_per_query = max(2, int(max_occurrences_per_query))
        self.max_trace_screens = max(7, int(max_trace_screens))
        self.max_cycle_period = min(3, max(1, int(max_cycle_period)))
        self.pending_capacity = max(1, int(pending_capacity))
        self.event_log_capacity = max(1, int(event_log_capacity))

        self._screen_trace: list[str] = []
        self._query_occurrences: dict[str, list[QueryOccurrence]] = {}
        self._query_key_order: list[str] = []
        self._pending: list[CanaryEvent] = []
        self._event_log: list[CanaryEvent] = []
        self._seen_signatures: list[str] = []
        self._last_clear_step: int | None = None

        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0
        self.activation_count = 0
        self.delivered_count = 0
        self.query_reentry_activation_count = 0
        self.navigation_cycle_activation_count = 0
        self.trace_discontinuity_count = 0

    def _enqueue(
        self,
        *,
        kind: str,
        source_step: int,
        evidence_steps: tuple[int, ...],
        signature: str,
        rendered: str,
    ) -> bool:
        signature_sha = sha256(signature.encode("utf-8")).hexdigest()
        if signature_sha in self._seen_signatures:
            return False
        self._seen_signatures.append(signature_sha)
        self._seen_signatures = self._seen_signatures[-self.event_log_capacity :]
        evidence_sha = sha256(
            f"{kind}|{source_step}|{evidence_steps}|{signature_sha}".encode("utf-8")
        ).hexdigest()
        event = CanaryEvent(
            event_id=f"a9e_{source_step:03d}_{kind.lower()}_{evidence_sha[:8]}",
            kind=kind,
            source_step=source_step,
            evidence_steps=evidence_steps,
            evidence_sha256=evidence_sha,
            rendered=_compact(rendered, self.max_chars),
        )
        self._pending.append(event)
        self._pending = self._pending[-self.pending_capacity :]
        self._event_log.append(event)
        self._event_log = self._event_log[-self.event_log_capacity :]
        self.activation_count += 1
        if kind.startswith("QUERY"):
            self.query_reentry_activation_count += 1
        else:
            self.navigation_cycle_activation_count += 1
        return True

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        # Pending events were derived during observe_step.  Ignoring context here
        # is intentional: hidden snapshot metadata cannot affect retrieval.
        del context
        self.read_count += 1
        if not self._pending:
            return "", {
                "mechanism_id": self.mechanism_id,
                "nonempty": False,
                "rendered_chars": 0,
                "rendered_sha256": sha256(b"").hexdigest(),
                "retrieved_ids": [],
                "retrieved_count": 0,
                "activation_canary": False,
            }
        event = self._pending.pop(0)
        rendered = event.rendered[: self.max_chars]
        self.nonempty_read_count += 1
        self.delivered_count += 1
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "nonempty": True,
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": [event.event_id],
            "retrieved_count": 1,
            "activation_canary": True,
            "canary_kind": event.kind,
            "evidence_steps": list(event.evidence_steps),
            "evidence_sha256": event.evidence_sha256,
            "one_shot": True,
        }

    def _record_query(
        self,
        *,
        source_step: int,
        action: dict[str, Any],
        action_summary: str,
        source: str,
        destination: str,
        source_response_sha256: str,
    ) -> bool:
        if str(action.get("type") or "") != "type_text":
            if bool(action.get("clear_text")) or _CLEAR_INTENT.search(action_summary):
                self._last_clear_step = source_step
            return False
        text = _compact(action.get("text") or "", 48)
        normalized = _normalized_text(text)
        if len(normalized) < 2:
            return False
        clear_evidence = bool(action.get("clear_text")) or (
            self._last_clear_step is not None and source_step - self._last_clear_step <= 2
        )
        occurrence = QueryOccurrence(
            source_step=source_step,
            text=text,
            normalized_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
            source_fingerprint=source,
            destination_fingerprint=destination,
            clear_evidence=clear_evidence,
            source_response_sha256=source_response_sha256,
        )
        if normalized not in self._query_occurrences:
            self._query_key_order.append(normalized)
        records = self._query_occurrences.setdefault(normalized, [])
        records.append(occurrence)
        records[:] = [
            item
            for item in records[-self.max_occurrences_per_query :]
            if source_step - item.source_step <= self.query_window_steps
        ]
        while len(self._query_key_order) > self.max_query_keys:
            oldest = self._query_key_order.pop(0)
            self._query_occurrences.pop(oldest, None)
        if len(records) != 2:
            return False
        first, second = records
        kind = "QUERY_CLEAR_REENTRY" if first.clear_evidence or second.clear_evidence else "QUERY_REENTRY"
        qualifier = " after clearing/re-entry" if kind == "QUERY_CLEAR_REENTRY" else ""
        return self._enqueue(
            kind=kind,
            source_step=source_step,
            evidence_steps=(first.source_step, second.source_step),
            signature=f"query|{occurrence.normalized_sha256}",
            rendered=(
                f'Recurrence canary: the same text "{text}" was entered at steps '
                f"{first.source_step + 1} and {second.source_step + 1}{qualifier}. "
                "This records recurrence only; reassess the visible route before repeating it."
            ),
        )

    def _record_cycle(self, *, source_step: int) -> bool:
        trace = self._screen_trace
        # Stationary canary requires two executed transitions / three screens.
        if len(trace) >= 3 and len(set(trace[-3:])) == 1:
            pattern = trace[-1]
            return self._enqueue(
                kind="STATIONARY_SCREEN",
                source_step=source_step,
                evidence_steps=(max(0, source_step - 1), source_step),
                signature=f"stationary|{pattern}",
                rendered=(
                    "Recurrence canary: the exact same visible screen persisted across "
                    "two actions. This is screen-revisit evidence only; reassess the "
                    "visible route before another repetition."
                ),
            )
        for period in range(2, self.max_cycle_period + 1):
            width = period * 2
            if len(trace) < width:
                continue
            if trace[-width:-period] != trace[-period:]:
                continue
            pattern = trace[-period:]
            return self._enqueue(
                kind=f"NAVIGATION_CYCLE_P{period}",
                source_step=source_step,
                evidence_steps=tuple(range(max(0, source_step - width + 2), source_step + 1)),
                signature=f"cycle|{period}|{'|'.join(pattern)}",
                rendered=(
                    f"Recurrence canary: an exact visible-screen route of period {period} "
                    "has repeated twice. This is route-revisit evidence only; reassess "
                    "the visible route before replaying the cycle."
                ),
            )
        return False

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        source_step = int(kwargs["source_step"])
        before = dict(kwargs.get("before") or {})
        after = dict(kwargs.get("after") or {})
        source = _visible_fingerprint(before)
        destination = _visible_fingerprint(after)
        if not self._screen_trace:
            self._screen_trace.append(source)
        elif self._screen_trace[-1] != source:
            self.trace_discontinuity_count += 1
            self._screen_trace.append(source)
        self._screen_trace.append(destination)
        self._screen_trace = self._screen_trace[-self.max_trace_screens :]

        action = dict(kwargs.get("canonical_action") or {})
        action_summary = str(kwargs.get("action_summary") or "")
        query_written = self._record_query(
            source_step=source_step,
            action=action,
            action_summary=action_summary,
            source=source,
            destination=destination,
            source_response_sha256=str(kwargs.get("source_response_sha256") or ""),
        )
        cycle_written = self._record_cycle(source_step=source_step)
        written = query_written or cycle_written
        if written:
            self.write_success_count += 1
        return {
            "written": written,
            "query_canary_written": query_written,
            "cycle_canary_written": cycle_written,
            "pending_count": len(self._pending),
            "source_fingerprint": source,
            "destination_fingerprint": destination,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_chars": self.max_chars,
            "query_window_steps": self.query_window_steps,
            "max_query_keys": self.max_query_keys,
            "max_occurrences_per_query": self.max_occurrences_per_query,
            "max_trace_screens": self.max_trace_screens,
            "max_cycle_period": self.max_cycle_period,
            "pending_capacity": self.pending_capacity,
            "event_log_capacity": self.event_log_capacity,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "activation_count": self.activation_count,
            "delivered_count": self.delivered_count,
            "query_reentry_activation_count": self.query_reentry_activation_count,
            "navigation_cycle_activation_count": self.navigation_cycle_activation_count,
            "trace_discontinuity_count": self.trace_discontinuity_count,
            "pending_count": len(self._pending),
            "screen_trace": list(self._screen_trace),
            "query_occurrences": {
                sha256(key.encode("utf-8")).hexdigest(): [asdict(item) for item in records]
                for key, records in self._query_occurrences.items()
            },
            "events": [asdict(event) for event in self._event_log],
            "active": self.activation_count > 0 and self.nonempty_read_count > 0,
            "model_calls_added": 0,
            "evaluator_used_for_decision": False,
            "hidden_ui_used_for_decision": False,
            "guard_enabled": False,
            "action_override_count": 0,
            "evidence_boundary": "policy_action_plus_exact_model_visible_rgb_pixels_only",
            "claim_boundary": "recurrence_only_never_failure_correctness_or_completion",
            "retrieval_policy": "one_shot_event_triggered_only",
        }
