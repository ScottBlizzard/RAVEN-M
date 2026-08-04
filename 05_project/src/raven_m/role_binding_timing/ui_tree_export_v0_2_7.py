"""Pure evidence parsing and classification for B2.7 DEV UI-tree export diagnosis."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
import xml.etree.ElementTree as ET


XML_END = b"</hierarchy>"


@dataclass(frozen=True)
class XmlValidation:
    valid: bool
    payload: bytes
    sha256: str | None
    root_tag: str | None
    package_names: tuple[str, ...]
    node_count: int
    semantic_node_count: int
    error: str | None
    envelope_found: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "payload_sha256": self.sha256,
            "payload_bytes": len(self.payload),
            "root_tag": self.root_tag,
            "package_names": list(self.package_names),
            "node_count": self.node_count,
            "semantic_node_count": self.semantic_node_count,
            "error": self.error,
            "envelope_found": self.envelope_found,
        }


def extract_xml_payload(raw: bytes) -> bytes:
    """Extract exactly one complete hierarchy envelope from command/file bytes."""
    if raw.count(b"<?xml") > 1 or raw.count(b"<hierarchy") > 1:
        raise ValueError("MULTIPLE_XML_ENVELOPES")
    start = raw.find(b"<?xml")
    end = raw.rfind(XML_END)
    if start < 0 or end < 0 or end < start:
        raise ValueError("XML_ENVELOPE_MISSING")
    end += len(XML_END)
    trailing = raw[end:]
    return raw[start:end]


def validate_xml_bytes(raw: bytes, *, expected_package: str | None) -> XmlValidation:
    try:
        payload = extract_xml_payload(raw)
    except Exception as exc:
        return XmlValidation(
            valid=False,
            payload=b"",
            sha256=None,
            root_tag=None,
            package_names=(),
            node_count=0,
            semantic_node_count=0,
            error=f"{type(exc).__name__}:{exc}",
            envelope_found=False,
        )
    try:
        root = ET.fromstring(payload)
        if root.tag != "hierarchy":
            raise ValueError(f"ROOT_NOT_HIERARCHY:{root.tag}")
        nodes = list(root.iter("node"))
        if not nodes:
            raise ValueError("NO_NODES")
        packages = tuple(sorted({node.attrib.get("package", "").strip() for node in nodes if node.attrib.get("package", "").strip()}))
        semantic = sum(
            bool(
                node.attrib.get("text", "").strip()
                or node.attrib.get("content-desc", "").strip()
                or node.attrib.get("resource-id", "").strip()
            )
            for node in nodes
        )
        if not packages:
            raise ValueError("NO_PACKAGE_NAMES")
        if semantic == 0:
            raise ValueError("NO_SEMANTIC_NODES")
        if expected_package and expected_package not in packages:
            raise ValueError(f"EXPECTED_PACKAGE_MISSING:{expected_package}")
        return XmlValidation(
            valid=True,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            root_tag=root.tag,
            package_names=packages,
            node_count=len(nodes),
            semantic_node_count=semantic,
            error=None,
            envelope_found=True,
        )
    except Exception as exc:
        return XmlValidation(
            valid=False,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            root_tag=None,
            package_names=(),
            node_count=0,
            semantic_node_count=0,
            error=f"{type(exc).__name__}:{exc}",
            envelope_found=True,
        )


def parse_state_markers(*, power: str, display: str, window_policy: str, device_idle: str) -> dict[str, Any]:
    folded_policy = window_policy.casefold()
    display_interactive = "minteractive=true" in display.casefold()
    power_interactive = "minteractive=true" in power.casefold()
    awake = "mwakefulness=awake" in power.casefold() or "wakefulness: awake" in power.casefold()
    display_on = "state=on" in display.casefold() or "mscreenstate=on" in display.casefold()
    keyguard_showing = "showing=true" in folded_policy or "mshowing=true" in folded_policy
    idle = "mdeepidlemode=true" in device_idle.casefold() or "mlightidlemode=true" in device_idle.casefold()
    interactive = (display_interactive or power_interactive) and awake and display_on and not keyguard_showing
    return {
        "interactive_verified": interactive,
        "display_interactive": display_interactive,
        "power_interactive": power_interactive,
        "wakefulness_awake": awake,
        "display_on": display_on,
        "keyguard_showing": keyguard_showing,
        "device_idle": idle,
    }


def qualify_paths(attempts: list[dict[str, Any]], repeats: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for attempt in attempts:
        grouped.setdefault((attempt["precondition"], attempt["form_id"]), []).append(attempt)
    qualified: list[dict[str, Any]] = []
    for (precondition, form_id), items in sorted(grouped.items()):
        items = sorted(items, key=lambda item: item["repeat"])
        expected_repeats = list(range(1, repeats + 1))
        observed_repeats = [item["repeat"] for item in items]
        all_valid = (
            observed_repeats == expected_repeats
            and all(item.get("xml_validation", {}).get("valid") is True for item in items)
            and all(item.get("adb_identity_continuous") is True for item in items)
            and all(item.get("state_markers_before", {}).get("interactive_verified") is True for item in items)
        )
        if all_valid:
            qualified.append(
                {
                    "precondition": precondition,
                    "form_id": form_id,
                    "transport": items[0]["transport"],
                    "compressed": items[0]["compressed"],
                    "repeats": repeats,
                }
            )
    return qualified


def classify_root_cause(
    *,
    attempts: list[dict[str, Any]],
    qualified_paths: list[dict[str, Any]],
    baseline_interactive: bool,
    wake_interactive: bool,
) -> dict[str, Any]:
    baseline_valid = any(
        item.get("xml_validation", {}).get("valid") is True and item["precondition"] == "observed"
        for item in attempts
    )
    wake_valid = any(
        item.get("xml_validation", {}).get("valid") is True and item["precondition"] == "wake_dismiss_verified"
        for item in attempts
    )
    qualified_file = any(item["transport"] == "remote_file" for item in qualified_paths)
    qualified_stdout = any(item["transport"] == "direct_stdout" for item in qualified_paths)
    raw_envelope_parse_failure = any(
        item.get("xml_validation", {}).get("envelope_found") is True
        and item.get("xml_validation", {}).get("valid") is not True
        for item in attempts
    )
    if not baseline_interactive and wake_interactive and wake_valid and not baseline_valid:
        cause = "DEVICE_NON_INTERACTIVE_OR_IDLE_STATE_FAILURE"
    elif qualified_stdout and not qualified_file:
        cause = "REMOTE_PATH_OR_FILE_CREATION_FAILURE"
    elif raw_envelope_parse_failure:
        cause = "PARSER_OR_CAPTURE_BUG"
    elif wake_interactive and not qualified_paths and not any(
        item.get("xml_validation", {}).get("envelope_found") is True for item in attempts
    ):
        cause = "UIAUTOMATOR_TOOL_FAILURE"
    else:
        cause = "UNRESOLVED"
    return {
        "root_cause": cause,
        "task_agnostic_acquisition_authorized": bool(qualified_paths),
        "qualified_paths": qualified_paths,
        "baseline_interactive_verified": baseline_interactive,
        "wake_interactive_verified": wake_interactive,
    }
