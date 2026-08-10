"""Controller-authored A6/A7/A8 memories with no extra model call.

These mechanisms consume only the task goal, model-visible pixels, the
policy's own action prose/canonical action, and visible-pixel transitions.
They never read an evaluator, UI tree, foreground package, guard, or hidden
state, and they never block, repair, or replace an action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

import numpy as np


def _compact(value: Any, limit: int | None = None) -> str:
    rendered = " ".join(str(value).split()).strip()
    if limit is not None and len(rendered) > limit:
        rendered = rendered[: max(0, limit - 3)].rstrip() + "..."
    return rendered


def _json_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _visible_outcome(transition: dict[str, Any]) -> str:
    if transition.get("exactly_unchanged") is True:
        return "no visible change"
    fraction = transition.get("changed_pixel_fraction_gt_5")
    if isinstance(fraction, (int, float)) and float(fraction) <= 0.001:
        return "negligible visible change"
    return "visible change"


def _visible_fingerprint(snapshot: dict[str, Any]) -> str:
    """Exact SHA256 of stable model-visible pixels, excluding thin system bars."""
    pixels = np.asarray(snapshot.get("pixels"))
    if pixels.ndim != 3 or pixels.shape[0] < 25 or pixels.shape[1] < 8:
        raise RuntimeError("A8 requires model-visible RGB screenshot pixels")
    top = int(round(pixels.shape[0] * 0.04))
    bottom = int(round(pixels.shape[0] * 0.96))
    crop = np.ascontiguousarray(pixels[top:bottom, :, :3])
    descriptor = f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    return sha256(descriptor).hexdigest()


class _AuditBase:
    mechanism_id: str

    def __init__(self, *, max_chars: int) -> None:
        self.max_chars = max(64, int(max_chars))
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0

    def _finish_read(
        self, rendered: str, *, retrieved_ids: list[str], details: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        rendered = rendered[: self.max_chars]
        self.read_count += 1
        if rendered:
            self.nonempty_read_count += 1
        audit = {
            "mechanism_id": self.mechanism_id,
            "nonempty": bool(rendered),
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": list(retrieved_ids),
            "retrieved_count": len(retrieved_ids),
        }
        audit.update(details or {})
        return rendered, audit

    def _base_audit(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_chars": self.max_chars,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "model_calls_added": 0,
            "evaluator_used_for_decision": False,
            "hidden_ui_used_for_decision": False,
            "guard_enabled": False,
            "action_override_count": 0,
        }


@dataclass(frozen=True)
class RecentEpisode:
    memory_id: str
    source_step: int
    action_type: str
    action_intent: str
    visible_outcome: str
    source_screenshot_sha256: str
    source_response_sha256: str
    canonical_action_sha256: str


class ShortTransitionEpisodicBuffer(_AuditBase):
    """A6: last-N action/outcome receipts, attested only by visible transitions."""

    mechanism_id = "a6_short_transition_attested_episodic_buffer_v1"

    def __init__(self, *, capacity: int = 2, max_chars: int = 240) -> None:
        super().__init__(max_chars=max_chars)
        self.capacity = max(1, int(capacity))
        self._entries: list[RecentEpisode] = []

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if not self._entries:
            return self._finish_read("", retrieved_ids=[])
        fragments = [
            f"step {entry.source_step + 1} {entry.action_type} ({entry.action_intent}) -> "
            f"{entry.visible_outcome}"
            for entry in self._entries
        ]
        rendered = "Recent transition-attested episodic memory: " + " | ".join(fragments)
        return self._finish_read(
            rendered, retrieved_ids=[entry.memory_id for entry in self._entries]
        )

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        action = dict(kwargs.get("canonical_action") or {})
        transition = dict(kwargs.get("transition") or {})
        step = int(kwargs["source_step"])
        action_type = _compact(action.get("type") or "unknown", 24)
        intent = _compact(kwargs.get("action_summary") or action_type, 72)
        action_sha = _json_sha(action)
        entry = RecentEpisode(
            memory_id=f"a6s_{step:03d}_{action_sha[:8]}",
            source_step=step,
            action_type=action_type,
            action_intent=intent,
            visible_outcome=_visible_outcome(transition),
            source_screenshot_sha256=str(kwargs.get("source_screenshot_sha256") or ""),
            source_response_sha256=str(kwargs.get("source_response_sha256") or ""),
            canonical_action_sha256=action_sha,
        )
        self._entries.append(entry)
        self._entries = self._entries[-self.capacity :]
        self.write_success_count += 1
        return {"written": True, "entry": asdict(entry), "buffer_size": len(self._entries)}

    def audit_record(self) -> dict[str, Any]:
        return {
            **self._base_audit(),
            "capacity": self.capacity,
            "entries": [asdict(entry) for entry in self._entries],
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "evidence_boundary": "policy_action_plus_model_visible_pixel_transition_only",
        }


@dataclass
class GoalItem:
    item_id: str
    text: str
    normalized: str
    status: str = "pending"
    source_step: int | None = None
    evidence_sha256: str | None = None


_QUOTED_ITEM = re.compile(
    r"[\"'\u201c\u201d\u2018\u2019]"
    r"([^\"'\u201c\u201d\u2018\u2019]{2,80})"
    r"[\"'\u201c\u201d\u2018\u2019]"
)


def extract_goal_items(goal: str, *, max_items: int = 6, max_item_chars: int = 48) -> list[str]:
    """Deterministically extract explicit values; never invent semantic completion."""
    goal = _compact(goal)
    quoted = [_compact(item, max_item_chars) for item in _QUOTED_ITEM.findall(goal)]
    candidates = quoted
    if not candidates and ":" in goal:
        tail = goal.rsplit(":", 1)[1].strip().rstrip(".")
        candidates = [_compact(item.strip(" ."), max_item_chars) for item in re.split(r"[,;]", tail)]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = re.sub(r"\W+", " ", item.casefold()).strip()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(item)
        if len(cleaned) >= max_items:
            break
    return cleaned


class GoalItemStatusLedger(_AuditBase):
    """A7: explicit goal-item attempt ledger; it never labels an item completed."""

    mechanism_id = "a7_deterministic_active_goal_item_status_ledger_v1"

    def __init__(self, *, max_items: int = 6, max_item_chars: int = 48, max_chars: int = 320) -> None:
        super().__init__(max_chars=max_chars)
        self.max_items = max(1, int(max_items))
        self.max_item_chars = max(8, int(max_item_chars))
        self._goal_sha256: str | None = None
        self._items: list[GoalItem] = []

    def _initialize(self, goal: str) -> None:
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if self._goal_sha256 is not None and goal_sha != self._goal_sha256:
            raise RuntimeError("A7 memory is episode-local and cannot accept a second task goal")
        if self._goal_sha256 is not None:
            return
        self._goal_sha256 = goal_sha
        self._items = [
            GoalItem(
                item_id=f"a7i_{index:02d}_{sha256(text.casefold().encode()).hexdigest()[:8]}",
                text=text,
                normalized=re.sub(r"\W+", " ", text.casefold()).strip(),
            )
            for index, text in enumerate(
                extract_goal_items(
                    goal, max_items=self.max_items, max_item_chars=self.max_item_chars
                ),
                start=1,
            )
        ]

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        self._initialize(str(context.get("goal") or ""))
        if not self._items:
            return self._finish_read(
                "", retrieved_ids=[], details={"goal_item_count": 0, "parse_inactive": True}
            )
        if self.write_attempt_count == 0:
            return self._finish_read(
                "",
                retrieved_ids=[],
                details={
                    "goal_item_count": len(self._items),
                    "parse_inactive": False,
                    "withheld_until_observed_action": True,
                },
            )
        rendered = "Goal-item attempt ledger (not completion evidence): " + " | ".join(
            f"{item.text}={item.status}" for item in self._items
        )
        return self._finish_read(
            rendered,
            retrieved_ids=[item.item_id for item in self._items],
            details={
                "goal_item_count": len(self._items),
                "parse_inactive": False,
                "withheld_until_observed_action": False,
            },
        )

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        summary = _compact(kwargs.get("action_summary") or "")
        normalized_summary = re.sub(r"\W+", " ", summary.casefold()).strip()
        outcome = _visible_outcome(dict(kwargs.get("transition") or {}))
        updates: list[dict[str, Any]] = []
        for item in self._items:
            if item.normalized and item.normalized in normalized_summary:
                item.status = f"attempted; {outcome}"
                item.source_step = int(kwargs["source_step"])
                item.evidence_sha256 = sha256(
                    f"{summary}|{outcome}|{kwargs.get('source_response_sha256') or ''}".encode("utf-8")
                ).hexdigest()
                updates.append(asdict(item))
        if updates:
            self.write_success_count += 1
        return {
            "written": bool(updates),
            "reason": "explicit_goal_item_mentioned" if updates else "no_explicit_goal_item_mention",
            "updates": updates,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            **self._base_audit(),
            "goal_sha256": self._goal_sha256,
            "max_items": self.max_items,
            "max_item_chars": self.max_item_chars,
            "items": [asdict(item) for item in self._items],
            "active": bool(self._items) and self.nonempty_read_count > 0,
            "claim_boundary": "attempt_status_only_never_completion",
        }


@dataclass(frozen=True)
class RevisitEntry:
    cache_id: str
    source_step: int
    source_fingerprint: str
    destination_fingerprint: str
    action_type: str
    action_intent: str
    visible_outcome: str
    canonical_action_sha256: str
    source_response_sha256: str


class ExactVisualRevisitActionOutcomeCache(_AuditBase):
    """A8: exact-screen cache of prior action/outcome receipts."""

    mechanism_id = "a8_exact_visual_revisit_action_outcome_cache_v1"

    def __init__(self, *, max_entries: int = 12, max_matches: int = 2, max_chars: int = 260) -> None:
        super().__init__(max_chars=max_chars)
        self.max_entries = max(1, int(max_entries))
        self.max_matches = max(1, int(max_matches))
        self._entries: list[RevisitEntry] = []
        self.exact_revisit_count = 0

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        fingerprint = _visible_fingerprint(dict(context.get("before") or {}))
        matches = [entry for entry in reversed(self._entries) if entry.source_fingerprint == fingerprint]
        matches = matches[: self.max_matches]
        if not matches:
            return self._finish_read(
                "", retrieved_ids=[], details={"query_fingerprint": fingerprint, "exact_match": False}
            )
        self.exact_revisit_count += 1
        rendered = "Exact-screen action/outcome memory: " + " | ".join(
            f"prior {entry.action_type} ({entry.action_intent}) -> {entry.visible_outcome}"
            for entry in matches
        )
        return self._finish_read(
            rendered,
            retrieved_ids=[entry.cache_id for entry in matches],
            details={"query_fingerprint": fingerprint, "exact_match": True},
        )

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        before = dict(kwargs.get("before") or {})
        after = dict(kwargs.get("after") or {})
        source = _visible_fingerprint(before)
        destination = _visible_fingerprint(after)
        action = dict(kwargs.get("canonical_action") or {})
        action_sha = _json_sha(action)
        step = int(kwargs["source_step"])
        entry = RevisitEntry(
            cache_id=f"a8c_{step:03d}_{source[:8]}_{action_sha[:8]}",
            source_step=step,
            source_fingerprint=source,
            destination_fingerprint=destination,
            action_type=_compact(action.get("type") or "unknown", 24),
            action_intent=_compact(kwargs.get("action_summary") or action.get("type") or "action", 72),
            visible_outcome=_visible_outcome(dict(kwargs.get("transition") or {})),
            canonical_action_sha256=action_sha,
            source_response_sha256=str(kwargs.get("source_response_sha256") or ""),
        )
        self._entries.append(entry)
        self._entries = self._entries[-self.max_entries :]
        self.write_success_count += 1
        return {"written": True, "entry": asdict(entry), "cache_size": len(self._entries)}

    def audit_record(self) -> dict[str, Any]:
        return {
            **self._base_audit(),
            "max_entries": self.max_entries,
            "max_matches": self.max_matches,
            "exact_revisit_count": self.exact_revisit_count,
            "entries": [asdict(entry) for entry in self._entries],
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "fingerprint": "sha256_exact_middle_92_percent_model_visible_rgb_pixels",
            "near_match_enabled": False,
        }

