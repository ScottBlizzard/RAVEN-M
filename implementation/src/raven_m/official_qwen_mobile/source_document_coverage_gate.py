"""Executable source-document coverage gate for bounded development pilots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MARKOR_DOCUMENT_ACTIVITY = (
    "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"
)
FORCED_FORWARD_SWIPE = {
    "type": "swipe",
    "x": 0.5,
    "y": 0.82,
    "x2": 0.5,
    "y2": 0.24,
    "duration_ms": 400,
}


def is_forward_vertical_swipe(action: dict[str, Any] | None) -> bool:
    if not action or action.get("type") != "swipe":
        return False
    dx = float(action.get("x2", 0.0)) - float(action.get("x", 0.0))
    dy = float(action.get("y2", 0.0)) - float(action.get("y", 0.0))
    return abs(dy) >= abs(dx) and dy < 0.0


def no_observable_transition(transition: dict[str, Any]) -> bool:
    changed_fraction = transition.get("changed_pixel_fraction_gt_5")
    return (
        isinstance(changed_fraction, (int, float))
        and float(changed_fraction) < 0.001
        and not bool(transition.get("activity_changed"))
        and not bool(transition.get("ui_sha_changed"))
    )


@dataclass
class SourceDocumentCoverageGate:
    """Force forward scanning until the source document reaches an attested end."""

    document_seen: bool = False
    forward_swipe_count: int = 0
    bottom_attested: bool = False
    override_count: int = 0

    def filter_action(
        self,
        *,
        before_activity: str | None,
        proposed_action: dict[str, Any] | None,
        terminal_status: str | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        in_document = before_activity == MARKOR_DOCUMENT_ACTIVITY
        if not in_document:
            return proposed_action, {
                "active": False,
                "overridden": False,
                "reason": None,
                "terminal_status_blocked": None,
            }
        self.document_seen = True
        if self.bottom_attested or is_forward_vertical_swipe(proposed_action):
            return proposed_action, {
                "active": not self.bottom_attested,
                "overridden": False,
                "reason": "bottom_attested" if self.bottom_attested else "proposed_forward_scan",
                "terminal_status_blocked": None,
            }
        self.override_count += 1
        return dict(FORCED_FORWARD_SWIPE), {
            "active": True,
            "overridden": True,
            "reason": "coverage_open_requires_forward_scan",
            "terminal_status_blocked": terminal_status,
            "proposed_action": proposed_action,
            "forced_action": dict(FORCED_FORWARD_SWIPE),
        }

    def observe(
        self,
        *,
        before_activity: str | None,
        executed_action: dict[str, Any],
        transition: dict[str, Any],
    ) -> dict[str, Any]:
        counted = (
            before_activity == MARKOR_DOCUMENT_ACTIVITY
            and is_forward_vertical_swipe(executed_action)
        )
        reached_bottom = False
        if counted:
            self.forward_swipe_count += 1
            reached_bottom = no_observable_transition(transition)
            if reached_bottom:
                self.bottom_attested = True
        return {
            "forward_swipe_counted": counted,
            "forward_swipe_count": self.forward_swipe_count,
            "bottom_attested_this_step": reached_bottom,
            "bottom_attested": self.bottom_attested,
            "override_count": self.override_count,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "document_seen": self.document_seen,
            "forward_swipe_count": self.forward_swipe_count,
            "bottom_attested": self.bottom_attested,
            "override_count": self.override_count,
        }
