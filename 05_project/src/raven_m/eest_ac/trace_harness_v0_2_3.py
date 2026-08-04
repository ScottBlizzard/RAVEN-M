"""Generic zero-model trace capture harness for EEST-AC v0.2.3."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from PIL import Image

from raven_m.eest_ac.outcome_oracle_v0_2_3 import (
    canonical_json,
    context_route_signature,
    value_sha256,
)


_IGNORED_PACKAGES = frozenset({"com.android.systemui"})
_SEMANTIC_FIELDS = (
    "text", "content_description", "hint_text", "tooltip", "class_name",
    "package_name", "resource_name", "resource_id", "is_clickable", "is_editable",
    "is_checkable", "is_checked", "is_selected", "is_scrollable", "is_enabled",
)


def _value(element: Any, field: str) -> Any:
    return element.get(field) if isinstance(element, dict) else getattr(element, field, None)


def _text(value: Any) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def semantic_a11y_records(state: Any) -> list[dict[str, Any]]:
    records = []
    for element in getattr(state, "ui_elements", ()) or ():
        if _value(element, "is_visible") is False:
            continue
        package = _text(_value(element, "package_name"))
        if package in _IGNORED_PACKAGES:
            continue
        record = {}
        for field in _SEMANTIC_FIELDS:
            item = _value(element, field)
            if item is None:
                continue
            if field in _SEMANTIC_FIELDS[:7]:
                item = _text(item)
                if not item:
                    continue
            record[field] = item
        if record:
            records.append(record)
    return sorted(records, key=canonical_json)


def current_activity(*, adb_path: str, adb_server_port: int, serial: str) -> str | None:
    result = subprocess.run(
        [adb_path, "-P", str(adb_server_port), "-s", serial, "shell", "dumpsys", "activity", "activities"],
        capture_output=True, text=True, check=False, timeout=20,
    )
    if result.returncode:
        return None
    match = re.search(r"(?:topResumedActivity|mResumedActivity)=ActivityRecord\{[^\n]*?\su\d+\s+([^\s}]+)", result.stdout)
    return match.group(1) if match else None


@dataclass(frozen=True)
class TraceSnapshotV023:
    oracle_observation: dict[str, Any]
    raw_record: dict[str, Any]


def capture_snapshot(
    *,
    env: Any,
    output_dir: Path,
    sample_id: str,
    adb_path: str,
    adb_server_port: int,
    serial: str,
) -> TraceSnapshotV023:
    state = env.get_state(wait_to_stabilize=True)
    pixels = state.pixels
    pixel_sha = sha256(pixels.tobytes()).hexdigest()
    screenshot = output_dir / f"{sample_id}.png"
    output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(screenshot)
    records = semantic_a11y_records(state)
    a11y_available = bool(records)
    a11y_sha = value_sha256(records) if a11y_available else None
    packages = sorted({str(item["package_name"]) for item in records if item.get("package_name")})
    activity = current_activity(
        adb_path=adb_path,
        adb_server_port=adb_server_port,
        serial=serial,
    )
    route = context_route_signature(packages, activity) if packages else None
    a11y_path = output_dir / f"{sample_id}.a11y.json"
    a11y_payload = {
        "sample_id": sample_id,
        "records": records,
        "package_names": packages,
        "activity": activity,
    }
    a11y_path.write_text(json.dumps(a11y_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    observation = {
        "pixel_sha256": pixel_sha,
        "a11y_available": a11y_available,
        "a11y_sha256": a11y_sha,
        "page_content_sha256": a11y_sha,
        "package_names": packages,
        "activity": activity,
        "route_signature": route,
    }
    raw = {
        "sample_id": sample_id,
        "captured_at_unix_seconds": time.time(),
        "pixel_bytes_sha256": pixel_sha,
        "screenshot_path": screenshot.name,
        "screenshot_file_sha256": sha256(screenshot.read_bytes()).hexdigest(),
        "a11y_path": a11y_path.name,
        "a11y_file_sha256": sha256(a11y_path.read_bytes()).hexdigest(),
        "semantic_a11y_sha256": a11y_sha,
        "semantic_element_count": len(records),
        "package_names": packages,
        "activity": activity,
        "route_signature": route,
    }
    return TraceSnapshotV023(observation, raw)


def capture_post_sequence(
    *,
    env: Any,
    output_dir: Path,
    count: int,
    delay_seconds: float,
    adb_path: str,
    adb_server_port: int,
    serial: str,
) -> list[TraceSnapshotV023]:
    snapshots = []
    for index in range(count):
        if index:
            time.sleep(delay_seconds)
        snapshots.append(capture_snapshot(
            env=env,
            output_dir=output_dir,
            sample_id=f"post_{index + 1:02d}",
            adb_path=adb_path,
            adb_server_port=adb_server_port,
            serial=serial,
        ))
    return snapshots
