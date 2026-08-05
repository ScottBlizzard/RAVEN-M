"""Lossless action normalization for cross-controller audits."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable


ACTION_NAMES = {"tap", "swipe", "type", "back", "home", "enter", "launch", "wait", "answer", "finish"}


@dataclass(frozen=True)
class ScreenTransform:
    source_width: int
    source_height: int
    target_width: int
    target_height: int

    def point(self, x: float, y: float) -> tuple[int, int]:
        if min(self.source_width, self.source_height, self.target_width, self.target_height) <= 0:
            raise ValueError("Screen dimensions must be positive")
        if not 0 <= x <= self.source_width or not 0 <= y <= self.source_height:
            raise ValueError("Source coordinate is out of bounds")
        tx = min(self.target_width - 1, round(x * self.target_width / self.source_width))
        ty = min(self.target_height - 1, round(y * self.target_height / self.source_height))
        return tx, ty


def normalize_action(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize syntax only; never change the controller-selected target."""
    if not isinstance(raw, dict):
        raise ValueError("Action must be an object")
    name = str(raw.get("action", raw.get("type", ""))).strip().lower()
    aliases = {"click": "tap", "press_back": "back", "terminate": "finish", "input_text": "type"}
    name = aliases.get(name, name)
    if name not in ACTION_NAMES:
        raise ValueError(f"Unsupported action: {name!r}")
    out: dict[str, Any] = {"action": name}
    if name == "tap":
        out.update(x=int(raw["x"]), y=int(raw["y"]))
    elif name == "swipe":
        out.update(x1=int(raw["x1"]), y1=int(raw["y1"]), x2=int(raw["x2"]), y2=int(raw["y2"]), duration_ms=int(raw.get("duration_ms", 400)))
    elif name in {"type", "answer"}:
        out["text"] = str(raw.get("text", raw.get("answer", "")))
    elif name == "launch":
        out["package"] = str(raw["package"])
    elif name == "wait":
        out["seconds"] = float(raw.get("seconds", 1.0))
    return out


def exact_fingerprint(action: dict[str, Any]) -> str:
    return json.dumps(normalize_action(action), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_fingerprint(action: dict[str, Any], coordinate_bin: int = 40) -> str:
    value = normalize_action(action)
    name = value["action"]
    if name == "tap":
        return f"tap:{value['x']//coordinate_bin}:{value['y']//coordinate_bin}"
    if name == "swipe":
        dx, dy = value["x2"] - value["x1"], value["y2"] - value["y1"]
        direction = "right" if abs(dx) >= abs(dy) and dx > 0 else "left" if abs(dx) >= abs(dy) else "down" if dy > 0 else "up"
        return f"swipe:{direction}"
    if name in {"type", "answer"}:
        text = re.sub(r"\s+", " ", value["text"].strip().casefold())
        return f"{name}:{text}"
    return name


def maximum_run(actions: Iterable[dict[str, Any]], *, semantic: bool = False) -> int:
    fingerprint = semantic_fingerprint if semantic else exact_fingerprint
    best = current = 0
    previous: str | None = None
    for action in actions:
        value = fingerprint(action)
        current = current + 1 if value == previous else 1
        best = max(best, current)
        previous = value
    return best
