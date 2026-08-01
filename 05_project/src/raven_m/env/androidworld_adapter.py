"""Deterministic mapping from canonical actions to AndroidWorld actions."""

from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Any
from xml.etree import ElementTree


_ATOMIC_CLEAR_AND_TYPE_TIMEOUT_SECONDS = 10.0
_ATOMIC_CLEAR_AND_TYPE_MAX_TIMEOUT_SECONDS = 120.0
_NATIVE_BOUNDS_RE = re.compile(
    r"^\[(?P<x_min>\d+),(?P<y_min>\d+)\]"
    r"\[(?P<x_max>\d+),(?P<y_max>\d+)\]$"
)
_NATIVE_INSPECTION_LABEL_RE = re.compile(
    r"\b(more\s+options|overflow|information|info|details?|edit)\b",
    flags=re.IGNORECASE,
)
_NATIVE_MUTATION_LABEL_RE = re.compile(
    r"\b(save|submit|apply|confirm|delete|send|record)\b",
    flags=re.IGNORECASE,
)


def _native_bounds(node: Any) -> dict[str, int] | None:
    match = _NATIVE_BOUNDS_RE.fullmatch(str(node.get("bounds") or ""))
    if match is None:
        return None
    bounds = {key: int(value) for key, value in match.groupdict().items()}
    if (
        bounds["x_min"] >= bounds["x_max"]
        or bounds["y_min"] >= bounds["y_max"]
    ):
        return None
    return bounds


def _native_row_label(
    row: Any,
    row_bounds: dict[str, int],
) -> tuple[str, str] | None:
    """Return one bounded visible row label and its resource id."""
    labels: dict[str, str] = {}
    resource_ids: set[str] = set()
    for descendant in row.iter("node"):
        resource_id = " ".join(
            str(descendant.get("resource-id") or "").split()
        )
        if resource_id:
            resource_ids.add(resource_id)
        for field in ("text", "content-desc"):
            label = " ".join(str(descendant.get(field) or "").split())
            if not label or len(label) > 80 or "\n" in label:
                continue
            label_bounds = _native_bounds(descendant)
            if (
                label_bounds is None
                or label_bounds["x_min"] < row_bounds["x_min"]
                or label_bounds["x_max"] > row_bounds["x_max"]
                or label_bounds["y_min"] < row_bounds["y_min"]
                or label_bounds["y_max"] > row_bounds["y_max"]
            ):
                return None
            labels.setdefault(label.casefold(), label)
    if len(labels) != 1:
        return None
    label = next(iter(labels.values()))
    resource_id = sorted(resource_ids)[0] if len(resource_ids) == 1 else ""
    return label, resource_id


def native_popup_menu_ui_elements_from_xml(
    xml: str,
    *,
    screen_width: int,
    screen_height: int,
) -> list[dict[str, Any]]:
    """Derive only structurally verified popup rows from native UI XML.

    Android UIAutomator can preserve popup labels and row bounds while
    incorrectly reporting every menu row as non-clickable.  This parser does
    not generally upgrade such nodes.  It accepts only a compact ListView
    whose direct children are two to ten equally sized, contiguous, singly
    labelled rows and which contains both an inspection route and a distinct
    mutating route.  The latter requirement makes the safety distinction that
    motivates this supplement explicit.  Any malformed or ambiguous tree
    returns no elements.
    """
    if (
        not isinstance(xml, str)
        or not xml.strip()
        or len(xml) > 2_000_000
        or screen_width <= 0
        or screen_height <= 0
    ):
        return []
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    candidates: list[list[dict[str, Any]]] = []
    for list_view in root.iter("node"):
        if list_view.get("class") != "android.widget.ListView":
            continue
        if (
            list_view.get("enabled") == "false"
            or list_view.get("scrollable") == "true"
        ):
            continue
        list_bounds = _native_bounds(list_view)
        if list_bounds is None:
            continue
        list_width = list_bounds["x_max"] - list_bounds["x_min"]
        list_height = list_bounds["y_max"] - list_bounds["y_min"]
        if (
            list_width > 0.75 * screen_width
            or list_height > 0.75 * screen_height
        ):
            continue
        rows = [child for child in list(list_view) if child.tag == "node"]
        if not 2 <= len(rows) <= 10:
            continue

        parsed_rows: list[dict[str, Any]] = []
        valid = True
        package_names: set[str] = set()
        for row in rows:
            if (
                row.get("class") != "android.widget.LinearLayout"
                or row.get("enabled") == "false"
            ):
                valid = False
                break
            bounds = _native_bounds(row)
            package_name = " ".join(
                str(row.get("package") or "").split()
            )
            if bounds is None or not package_name:
                valid = False
                break
            labelled = _native_row_label(row, bounds)
            if labelled is None:
                valid = False
                break
            if (
                abs(bounds["x_min"] - list_bounds["x_min"]) > 2
                or abs(bounds["x_max"] - list_bounds["x_max"]) > 2
                or bounds["y_min"] < list_bounds["y_min"] - 2
                or bounds["y_max"] > list_bounds["y_max"] + 2
            ):
                valid = False
                break
            label, resource_id = labelled
            package_names.add(package_name)
            parsed_rows.append(
                {
                    "text": label,
                    "content_description": "",
                    "resource_id": resource_id,
                    "class_name": row.get("class"),
                    "package_name": package_name,
                    "bbox_pixels": bounds,
                    "is_visible": True,
                    "is_enabled": True,
                    # The row is actionable by its verified ListView-row
                    # structure even when UIAutomator's raw flag is false.
                    "is_clickable": True,
                    "source": "native_uiautomator_popup_row",
                }
            )
        if not valid or len(package_names) != 1:
            continue
        if (
            abs(
                parsed_rows[0]["bbox_pixels"]["y_min"]
                - list_bounds["y_min"]
            )
            > 2
            or abs(
                parsed_rows[-1]["bbox_pixels"]["y_max"]
                - list_bounds["y_max"]
            )
            > 2
        ):
            continue

        heights = [
            item["bbox_pixels"]["y_max"]
            - item["bbox_pixels"]["y_min"]
            for item in parsed_rows
        ]
        if (
            min(heights) < max(24, 0.01 * screen_height)
            or max(heights) > 1.15 * min(heights)
        ):
            continue
        if any(
            abs(
                parsed_rows[index]["bbox_pixels"]["y_max"]
                - parsed_rows[index + 1]["bbox_pixels"]["y_min"]
            )
            > 2
            for index in range(len(parsed_rows) - 1)
        ):
            continue
        labels = [item["text"] for item in parsed_rows]
        if len({label.casefold() for label in labels}) != len(labels):
            continue
        if not any(_NATIVE_INSPECTION_LABEL_RE.search(label) for label in labels):
            continue
        if not any(_NATIVE_MUTATION_LABEL_RE.search(label) for label in labels):
            continue
        candidates.append(parsed_rows)

    # Multiple independently valid popup lists are ambiguous; fail closed.
    return candidates[0] if len(candidates) == 1 else []


def current_native_popup_menu_ui_elements(
    env: Any,
    *,
    screen_width: int,
    screen_height: int,
    timeout_seconds: float = 10.0,
) -> list[dict[str, Any]]:
    """Capture and parse one current-screen native popup hierarchy."""
    from android_world.env import adb_utils

    xml = adb_utils.uiautomator_dump(
        env.controller,
        timeout_sec=timeout_seconds,
    )
    return native_popup_menu_ui_elements_from_xml(
        xml,
        screen_width=screen_width,
        screen_height=screen_height,
    )


@dataclass(frozen=True)
class MappedAction:
    canonical: dict[str, Any]
    screen_size: tuple[int, int]
    actual_pixels: dict[str, int]
    upstream_action: dict[str, Any] | None

    def audit_record(self) -> dict[str, Any]:
        return {
            "canonical": self.canonical,
            "screen_size": list(self.screen_size),
            "actual_pixels": self.actual_pixels,
            "upstream_action": self.upstream_action,
        }


class AndroidWorldAdapter:
    """Maps normalized screenshot coordinates and rejects unsafe values."""

    @staticmethod
    def _atomic_clear_and_type_command(text: str, adb_utils: Any) -> list[str]:
        """Build one retry-idempotent shell request for clear-and-type.

        AndroidEnv retries a timed-out ADB command below this adapter. Keeping
        select-all, delete, and every input token in the same shell request
        ensures that each such retry clears any prefix left by its predecessor.
        Tokenization preserves AndroidWorld's word-wise input behavior.
        """
        command = [
            "shell",
            "input",
            "keycombination",
            "113",
            "29",
            "&&",
            "input",
            "keyevent",
            "67",
            "&&",
            "sleep",
            "1",
        ]
        for token in adb_utils._split_words_and_newlines(text):
            command.append("&&")
            if token == "\n":
                command.extend(["input", "keyevent", "66"])
            else:
                command.extend(
                    ["input", "text", adb_utils._adb_text_format(token)]
                )
        return command

    @staticmethod
    def _atomic_clear_and_type_timeout(text: str, adb_utils: Any) -> float:
        """Scale one compound request without allowing an unbounded stall."""
        input_operation_count = sum(
            1 for _ in adb_utils._split_words_and_newlines(text)
        )
        return min(
            _ATOMIC_CLEAR_AND_TYPE_MAX_TIMEOUT_SECONDS,
            max(
                _ATOMIC_CLEAR_AND_TYPE_TIMEOUT_SECONDS,
                float(input_operation_count + 2),
            ),
        )

    @staticmethod
    def _pixel(value: Any, extent: int, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be a number.")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{field}={value!r} is outside [0, 1].")
        if extent <= 0:
            raise ValueError(f"Invalid screen extent for {field}: {extent}.")
        return round(float(value) * (extent - 1))

    def map_action(
        self,
        canonical: dict[str, Any],
        *,
        screen_width: int,
        screen_height: int,
    ) -> MappedAction:
        action_type = canonical["type"]
        pixels: dict[str, int] = {}
        for field, extent in (
            ("x", screen_width),
            ("x2", screen_width),
            ("y", screen_height),
            ("y2", screen_height),
        ):
            if field in canonical:
                pixels[field] = self._pixel(canonical[field], extent, field)

        upstream: dict[str, Any] | None
        if action_type == "tap":
            upstream = {
                "action_type": "click",
                "x": pixels["x"],
                "y": pixels["y"],
            }
        elif action_type == "type_text":
            upstream = {
                "action_type": "input_text",
                "text": canonical["text"],
                "clear_text": canonical.get("clear_text", False),
            }
            if "x" in pixels:
                upstream.update(x=pixels["x"], y=pixels["y"])
        elif action_type == "press_back":
            upstream = {"action_type": "navigate_back"}
        elif action_type == "press_home":
            upstream = {"action_type": "navigate_home"}
        elif action_type == "press_enter":
            upstream = {"action_type": "keyboard_enter"}
        elif action_type == "open_app":
            upstream = {
                "action_type": "open_app",
                "app_name": canonical["app_name"],
            }
        elif action_type == "answer":
            upstream = {
                "action_type": "answer",
                "text": canonical["text"],
            }
        elif action_type in {"swipe", "long_press", "wait"}:
            upstream = None
        else:
            raise ValueError(f"Unsupported canonical action: {action_type!r}")

        return MappedAction(
            canonical=dict(canonical),
            screen_size=(screen_width, screen_height),
            actual_pixels=pixels,
            upstream_action=upstream,
        )

    def execute(self, env: Any, mapped: MappedAction) -> None:
        """Execute one already-validated action against an AsyncEnv."""
        from android_env.proto import adb_pb2
        from android_world.env import adb_utils, json_action

        action_type = mapped.canonical["type"]
        if action_type == "answer":
            # AndroidWorld's evaluator reads interaction_cache. Its upstream
            # answer branch sets this value and then sends a cosmetic overlay
            # broadcast; the latter can block on an unhealthy overlay service
            # even though the terminal answer is already available. Preserve
            # the benchmark semantics without coupling evaluation to the UI.
            env.interaction_cache = mapped.canonical["text"]
            return
        if (
            action_type == "type_text"
            and mapped.canonical.get("clear_text", False)
            and mapped.canonical.get("text")
        ):
            pixels = mapped.actual_pixels
            if "x" in pixels:
                env.execute_action(
                    json_action.JSONAction(
                        action_type="click",
                        x=pixels["x"],
                        y=pixels["y"],
                    )
                )
                time.sleep(1.0)

            command = self._atomic_clear_and_type_command(
                mapped.canonical["text"],
                adb_utils,
            )
            response = adb_utils.issue_generic_request(
                command,
                env.controller,
                timeout_sec=self._atomic_clear_and_type_timeout(
                    mapped.canonical["text"],
                    adb_utils,
                ),
            )
            if response.status != adb_pb2.AdbResponse.Status.OK:
                raise RuntimeError(
                    "Atomic clear-and-type ADB request failed: "
                    f"status={response.status}, "
                    f"error={response.error_message!r}"
                )
            adb_utils.press_enter_button(env.controller)
            return
        if mapped.upstream_action is not None:
            env.execute_action(json_action.JSONAction(**mapped.upstream_action))
            return
        if action_type == "swipe":
            pixels = mapped.actual_pixels
            command = adb_utils.generate_swipe_command(
                pixels["x"],
                pixels["y"],
                pixels["x2"],
                pixels["y2"],
                mapped.canonical["duration_ms"],
            )
            adb_utils.issue_generic_request(command, env.controller)
            return
        if action_type == "long_press":
            pixels = mapped.actual_pixels
            command = adb_utils.generate_swipe_command(
                pixels["x"],
                pixels["y"],
                pixels["x"],
                pixels["y"],
                mapped.canonical["duration_ms"],
            )
            adb_utils.issue_generic_request(command, env.controller)
            return
        if action_type == "wait":
            time.sleep(mapped.canonical["duration_ms"] / 1000.0)
            return
        raise ValueError(f"Cannot execute canonical action: {action_type!r}")
