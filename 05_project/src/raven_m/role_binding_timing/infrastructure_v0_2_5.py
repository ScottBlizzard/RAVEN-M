"""Task-agnostic collector infrastructure primitives for B2.5 DEV qualification."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import io
import re
from typing import Any, Callable, Iterable
import xml.etree.ElementTree as ET

from PIL import Image


COMPONENT_RE = re.compile(r"(?<![\w.])([A-Za-z][\w.]*)/([A-Za-z0-9_.$]+)")
BOUNDS_RE = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")
ACTIVITY_MARKERS = ("topResumedActivity", "mResumedActivity", "ResumedActivity")
WINDOW_MARKERS = ("mCurrentFocus", "mFocusedApp", "FocusedWindow")


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def parse_bounds(value: str) -> tuple[int, int, int, int]:
    match = BOUNDS_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"INVALID_BOUNDS:{value}")
    bounds = tuple(int(item) for item in match.groups())
    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise ValueError(f"DEGENERATE_BOUNDS:{value}")
    return bounds


def _marked_components(output: str, markers: Iterable[str]) -> list[str]:
    components: list[str] = []
    for line in output.splitlines():
        if not any(marker in line for marker in markers):
            continue
        for match in COMPONENT_RE.finditer(line):
            component = f"{match.group(1)}/{match.group(2)}"
            if component not in components:
                components.append(component)
    return components


def parse_foreground_witnesses(activity_output: str, window_output: str) -> dict[str, Any]:
    activity_components = _marked_components(activity_output, ACTIVITY_MARKERS)
    window_components = _marked_components(window_output, WINDOW_MARKERS)
    return {
        "activity_components": activity_components,
        "activity_packages": sorted({item.split("/", 1)[0] for item in activity_components}),
        "window_components": window_components,
        "window_packages": sorted({item.split("/", 1)[0] for item in window_components}),
        "activity_raw_sha256": sha256_bytes(activity_output.encode("utf-8")),
        "window_raw_sha256": sha256_bytes(window_output.encode("utf-8")),
    }


def validate_launch_result(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("timed_out"):
        issues.append("LAUNCH_TIMEOUT")
    if result.get("returncode") != 0:
        issues.append("LAUNCH_NONZERO")
    stdout = str(result.get("stdout", ""))
    if "Error:" in stdout or "Exception" in stdout:
        issues.append("LAUNCH_ERROR_OUTPUT")
    status = next(
        (line.split(":", 1)[1].strip().casefold() for line in stdout.splitlines() if line.strip().startswith("Status:")),
        None,
    )
    if status is not None and status != "ok":
        issues.append("LAUNCH_STATUS_NOT_OK")
    if not any(line.strip().startswith(("Status:", "Starting:", "Warning:")) for line in stdout.splitlines()):
        issues.append("LAUNCH_RESULT_UNPARSEABLE")
    return issues


@dataclass(frozen=True)
class UiNode:
    xpath: str
    parent_xpath: str
    package: str
    resource_id: str
    text: str
    content_desc: str
    class_name: str
    clickable: bool
    enabled: bool
    bounds: tuple[int, int, int, int]


@dataclass(frozen=True)
class UiTree:
    nodes: tuple[UiNode, ...]
    raw_sha256: str
    semantic_sha256: str


def parse_ui_tree(raw_xml: bytes) -> UiTree:
    root = ET.fromstring(raw_xml.decode("utf-8"))
    parent = {child: node for node in root.iter() for child in node}

    def xpath(node: ET.Element) -> str:
        segments: list[str] = []
        current = node
        while current is not root:
            owner = parent[current]
            siblings = list(owner)
            segments.append(f"node[{siblings.index(current)}]")
            current = owner
        return "/hierarchy/" + "/".join(reversed(segments))

    nodes: list[UiNode] = []
    for node in root.iter("node"):
        try:
            bounds = parse_bounds(node.attrib.get("bounds", ""))
        except ValueError:
            continue
        owner = parent.get(node)
        nodes.append(
            UiNode(
                xpath=xpath(node),
                parent_xpath=xpath(owner) if owner is not None and owner is not root else "/hierarchy",
                package=node.attrib.get("package", ""),
                resource_id=node.attrib.get("resource-id", ""),
                text=node.attrib.get("text", ""),
                content_desc=node.attrib.get("content-desc", ""),
                class_name=node.attrib.get("class", ""),
                clickable=node.attrib.get("clickable") == "true",
                enabled=node.attrib.get("enabled") == "true",
                bounds=bounds,
            )
        )
    if not nodes:
        raise ValueError("UI_TREE_EMPTY")
    semantic = "\n".join(
        "|".join(
            (
                item.xpath,
                item.package,
                item.resource_id,
                item.text,
                item.content_desc,
                item.class_name,
                str(item.clickable),
                str(item.enabled),
                ",".join(str(value) for value in item.bounds),
            )
        )
        for item in nodes
    ).encode("utf-8")
    return UiTree(
        nodes=tuple(nodes),
        raw_sha256=sha256_bytes(raw_xml),
        semantic_sha256=sha256_bytes(semantic),
    )


def _clickable_authority(node: UiNode, by_xpath: dict[str, UiNode]) -> UiNode | None:
    current = node
    while True:
        if current.clickable and current.enabled:
            return current
        if current.parent_xpath not in by_xpath:
            return None
        current = by_xpath[current.parent_xpath]


def _field_matches(tree: UiTree, *, field: str, value: str, package: str) -> list[UiNode]:
    normalized = normalize_text(value)
    matches: list[UiNode] = []
    for node in tree.nodes:
        if node.package != package:
            continue
        candidate = node.resource_id if field == "resource_id" else (
            node.content_desc if field == "content_desc" else node.text
        )
        if field == "resource_id":
            equal = candidate == value
        else:
            equal = normalize_text(candidate) == normalized and bool(normalized)
        if equal:
            matches.append(node)
    return matches


def resolve_locator(
    tree: UiTree,
    *,
    package: str,
    locator: dict[str, str],
    hierarchy: tuple[str, ...] = ("resource_id", "content_desc", "text"),
) -> dict[str, Any]:
    by_xpath = {node.xpath: node for node in tree.nodes}
    attempts: list[dict[str, Any]] = []
    for field in hierarchy:
        value = locator.get(field, "")
        if not value:
            attempts.append({"field": field, "status": "not_supplied", "candidate_count": 0})
            continue
        anchors = _field_matches(tree, field=field, value=value, package=package)
        authorities = []
        for anchor in anchors:
            authority = _clickable_authority(anchor, by_xpath)
            if authority is not None and authority not in authorities:
                authorities.append(authority)
        attempts.append(
            {
                "field": field,
                "status": "unique" if len(authorities) == 1 else "ambiguous_or_missing",
                "anchor_count": len(anchors),
                "candidate_count": len(authorities),
            }
        )
        if len(authorities) == 1:
            chosen = authorities[0]
            return {
                "strategy": field,
                "xpath": chosen.xpath,
                "bounds": list(chosen.bounds),
                "package": chosen.package,
                "resource_id": chosen.resource_id,
                "class": chosen.class_name,
                "text": chosen.text,
                "content_desc": chosen.content_desc,
                "attempts": attempts,
            }
    raise ValueError(f"LOCATOR_NOT_UNIQUE:{attempts}")


def derive_dev_locator(tree: UiTree, *, package: str) -> dict[str, str]:
    """Choose a deterministic unique DEV witness; never used as a task oracle."""
    by_xpath = {node.xpath: node for node in tree.nodes}
    for field in ("resource_id", "content_desc", "text"):
        values: dict[str, list[UiNode]] = {}
        for node in tree.nodes:
            if node.package != package:
                continue
            value = node.resource_id if field == "resource_id" else (
                node.content_desc if field == "content_desc" else node.text
            )
            if not value:
                continue
            authority = _clickable_authority(node, by_xpath)
            if authority is not None:
                values.setdefault(value, []).append(authority)
        for value in sorted(values):
            if len({item.xpath for item in values[value]}) == 1:
                return {field: value}
    raise ValueError("NO_UNIQUE_DEV_LOCATOR")


def validate_foreground(
    *,
    expected_package: str,
    witnesses: dict[str, Any],
    ui_tree: UiTree,
) -> list[str]:
    issues: list[str] = []
    if expected_package not in witnesses["activity_packages"]:
        issues.append("ACTIVITY_WITNESS_MISSING")
    if expected_package not in witnesses["window_packages"]:
        issues.append("WINDOW_WITNESS_MISSING")
    ui_packages = sorted({node.package for node in ui_tree.nodes if node.package})
    if expected_package not in ui_packages:
        issues.append("UI_PACKAGE_WITNESS_MISSING")
    if any(
        package != expected_package
        for package in witnesses["activity_packages"] + witnesses["window_packages"]
    ):
        issues.append("CONTRADICTORY_FOREGROUND_WITNESS")
    return issues


def validate_png(raw_png: bytes, expected_size: tuple[int, int]) -> dict[str, Any]:
    if not raw_png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("SCREENSHOT_NOT_PNG")
    with Image.open(io.BytesIO(raw_png)) as image:
        image.load()
        size = tuple(image.size)
    if size != expected_size:
        raise ValueError(f"SCREENSHOT_SIZE:{size}:{expected_size}")
    return {"sha256": sha256_bytes(raw_png), "bytes": len(raw_png), "size": list(size)}


def direct_find_args(root: str) -> list[str]:
    if not root.startswith("/storage/emulated/0/") or any(item in root for item in ("\n", "\r", "|", ";")):
        raise ValueError("UNSAFE_FIND_ROOT")
    return ["shell", "find", root, "-maxdepth", "1", "-type", "f", "-print"]


def parse_direct_find_output(output: str, root: str) -> list[str]:
    prefix = root.rstrip("/") + "/"
    paths = [line.strip() for line in output.splitlines() if line.strip()]
    if any(not path.startswith(prefix) or "/../" in path or path.startswith("./") for path in paths):
        raise ValueError("FIND_OUTPUT_ESCAPED_ROOT")
    if len(paths) != len(set(paths)):
        raise ValueError("FIND_OUTPUT_DUPLICATE")
    return paths


def guarded_call(
    *,
    expected_pid: int,
    witness: Callable[[], int | None],
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    before = witness()
    if before != expected_pid:
        raise RuntimeError(f"ADB_SERVER_IDENTITY_BEFORE:{before}:{expected_pid}")
    result = operation()
    after = witness()
    if after != expected_pid:
        raise RuntimeError(f"ADB_SERVER_IDENTITY_AFTER:{after}:{expected_pid}")
    return {**result, "adb_server_pid_before": before, "adb_server_pid_after": after}
