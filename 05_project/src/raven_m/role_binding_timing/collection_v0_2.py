"""Deterministic Phase-B2 snapshot/oracle parsing and qualification."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator


BOUNDS_RE = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")
TARGET_IDS = tuple("ABCDEFGH")
ENTITY_IDS = tuple(f"E{i}" for i in range(1, 9))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_bounds(value: str) -> list[int]:
    match = BOUNDS_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid bounds: {value!r}")
    bounds = [int(item) for item in match.groups()]
    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise ValueError(f"Degenerate bounds: {value!r}")
    return bounds


@dataclass(frozen=True)
class ParsedTree:
    root: ET.Element
    nodes: tuple[dict[str, Any], ...]
    semantic_sha256: str


def parse_ui_tree(raw_xml: bytes) -> ParsedTree:
    root = ET.fromstring(raw_xml.decode("utf-8"))
    parent = {child: node for node in root.iter() for child in node}
    nodes: list[dict[str, Any]] = []

    def xpath(node: ET.Element) -> str:
        segments: list[str] = []
        current = node
        while current is not root:
            owner = parent[current]
            siblings = list(owner)
            segments.append(f"node[{siblings.index(current)}]")
            current = owner
        return "/hierarchy/" + "/".join(reversed(segments))

    for node in root.iter("node"):
        attrs = node.attrib
        try:
            bounds = parse_bounds(attrs.get("bounds", ""))
        except ValueError:
            continue
        nodes.append(
            {
                "xpath": xpath(node),
                "text": attrs.get("text", ""),
                "content_desc": attrs.get("content-desc", ""),
                "resource_id": attrs.get("resource-id", ""),
                "class": attrs.get("class", ""),
                "package": attrs.get("package", ""),
                "clickable": attrs.get("clickable") == "true",
                "enabled": attrs.get("enabled") == "true",
                "bounds": bounds,
                "parent_xpath": xpath(parent[node]) if parent.get(node) is not None and parent[node] is not root else "/hierarchy",
            }
        )
    semantic = [
        {
            key: item[key]
            for key in (
                "xpath",
                "text",
                "content_desc",
                "resource_id",
                "class",
                "package",
                "clickable",
                "enabled",
                "bounds",
            )
        }
        for item in nodes
    ]
    return ParsedTree(
        root=root,
        nodes=tuple(nodes),
        semantic_sha256=sha256_bytes(canonical_json(semantic).encode("utf-8")),
    )


def _ancestor_chain(node: dict[str, Any], by_xpath: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    chain = [node]
    current = node
    while current["parent_xpath"] in by_xpath:
        current = by_xpath[current["parent_xpath"]]
        chain.append(current)
    return chain


def resolve_exact_item(tree: ParsedTree, label: str) -> dict[str, Any]:
    anchors = [
        item
        for item in tree.nodes
        if item["text"] == label or item["content_desc"] == label
    ]
    if len(anchors) != 1:
        raise ValueError(f"ITEM_ANCHOR_COUNT:{label}:{len(anchors)}")
    by_xpath = {item["xpath"]: item for item in tree.nodes}
    clickable = [
        item
        for item in _ancestor_chain(anchors[0], by_xpath)
        if item["clickable"] and item["enabled"]
    ]
    if not clickable:
        raise ValueError(f"CLICKABLE_ANCESTOR_COUNT:{label}:0")
    chosen = clickable[0]
    return {
        "anchor_text": label,
        "anchor_xpath": anchors[0]["xpath"],
        "xpath": chosen["xpath"],
        "resource_id": chosen["resource_id"],
        "class": chosen["class"],
        "content_desc": chosen["content_desc"],
        "bounds": chosen["bounds"],
    }


def count_exact_item(tree: ParsedTree, label: str) -> int:
    return sum(
        item["text"] == label or item["content_desc"] == label
        for item in tree.nodes
    )


def select_neutral_control(
    tree: ParsedTree,
    *,
    excluded_xpaths: set[str],
) -> dict[str, Any]:
    candidates = []
    for item in tree.nodes:
        if not item["clickable"] or not item["enabled"] or item["xpath"] in excluded_xpaths:
            continue
        if any(
            item["xpath"].startswith(path + "/") or path.startswith(item["xpath"] + "/")
            for path in excluded_xpaths
        ):
            continue
        if not (item["text"] or item["content_desc"] or item["resource_id"]):
            continue
        candidates.append(item)
    if not candidates:
        raise ValueError("NO_NEUTRAL_CONTROL")
    candidates.sort(key=lambda item: (item["bounds"][1], item["bounds"][0], item["xpath"]))
    chosen = candidates[0]
    return {
        "anchor_text": chosen["text"],
        "anchor_xpath": chosen["xpath"],
        "xpath": chosen["xpath"],
        "resource_id": chosen["resource_id"],
        "class": chosen["class"],
        "content_desc": chosen["content_desc"],
        "bounds": chosen["bounds"],
    }


def build_oracle(
    *,
    raw_xml: bytes,
    family: dict[str, Any],
    ambiguity: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tree = parse_ui_tree(raw_xml)
    destination = resolve_exact_item(tree, family["destination_label"])
    source_count = count_exact_item(tree, family["source_label"])
    if ambiguity == "high":
        source = resolve_exact_item(tree, family["source_label"])
        if source["xpath"] == destination["xpath"]:
            raise ValueError("SOURCE_DESTINATION_WIDGET_NOT_DISTINCT")
        source_target_id: str | None = family["source_target_id"]
    elif ambiguity == "low":
        if source_count != 0:
            raise ValueError(f"LOW_SOURCE_PRESENT:{source_count}")
        source = None
        source_target_id = None
    else:
        raise ValueError(f"UNKNOWN_AMBIGUITY:{ambiguity}")
    excluded = {destination["xpath"]}
    if source is not None:
        excluded.add(source["xpath"])
    neutral = select_neutral_control(tree, excluded_xpaths=excluded)
    targets = [
        {
            "target_id": family["destination_target_id"],
            "entity_id": family["destination_entity_id"],
            "widget_role": "destination_entity_control",
            "widget_family": family["destination_widget_family"],
            "selector": destination,
            "bounds": destination["bounds"],
            "ambiguity_group": family["destination_widget_family"],
        }
    ]
    if source is not None:
        targets.append(
            {
                "target_id": family["source_target_id"],
                "entity_id": family["source_entity_id"],
                "widget_role": "source_entity_control",
                "widget_family": family["destination_widget_family"],
                "selector": source,
                "bounds": source["bounds"],
                "ambiguity_group": family["destination_widget_family"],
            }
        )
    targets.append(
        {
            "target_id": family["neutral_target_id"],
            "entity_id": None,
            "widget_role": "non_entity_control",
            "widget_family": "structural_control",
            "selector": neutral,
            "bounds": neutral["bounds"],
            "ambiguity_group": "non_entity_control",
        }
    )
    if len({item["target_id"] for item in targets}) != len(targets):
        raise ValueError("DUPLICATE_TARGET_ALIAS")
    rationale = {
        "method": "exact_text_anchor_to_nearest_enabled_clickable_ancestor",
        "destination_anchor": family["destination_label"],
        "destination_selector": destination,
        "source_anchor": family["source_label"],
        "source_anchor_count": source_count,
        "source_selector": source,
        "neutral_selector_policy": "first_bounds_then_xpath_non_entity_clickable",
        "neutral_selector": neutral,
        "destination_widget_family": family["destination_widget_family"],
        "source_target_id": source_target_id,
        "independently_checkable": True,
    }
    return targets, rationale


def validate_collection_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    families = config.get("families", [])
    qualification = config.get("qualification", {})
    if len(families) != qualification.get("required_families"):
        issues.append("FAMILY_COUNT")
    ids = [item.get("base_family_id") for item in families]
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_FAMILY_ID")
    apps = [item.get("app_id") for item in families]
    widgets = [item.get("destination_widget_family") for item in families]
    semantics = [item.get("task_semantics_id") for item in families]
    if len(set(apps)) < qualification.get("minimum_apps", 0):
        issues.append("APP_DIVERSITY")
    if max(Counter(apps).values(), default=0) > qualification.get("maximum_families_per_app", 0):
        issues.append("APP_DOMINANCE")
    if len(set(widgets)) < qualification.get("minimum_widget_families", 0):
        issues.append("WIDGET_DIVERSITY")
    if len(semantics) != len(set(semantics)):
        issues.append("TASK_SEMANTICS_NOT_DISTINCT")
    for family in families:
        if family.get("source_entity_id") == family.get("destination_entity_id"):
            issues.append(f"{family.get('base_family_id')}:ENTITY_ALIAS_COLLISION")
        aliases = [
            family.get("destination_target_id"),
            family.get("source_target_id"),
            family.get("neutral_target_id"),
        ]
        if len(set(aliases)) != 3 or any(item not in TARGET_IDS for item in aliases):
            issues.append(f"{family.get('base_family_id')}:TARGET_ALIAS_INVALID")
        if family.get("source_entity_id") not in ENTITY_IDS or family.get("destination_entity_id") not in ENTITY_IDS:
            issues.append(f"{family.get('base_family_id')}:ENTITY_ALIAS_INVALID")
        if sorted(family.get("variant_order", [])) != ["high", "low"]:
            issues.append(f"{family.get('base_family_id')}:VARIANT_ORDER_INVALID")
    if config.get("generation_calls_authorized") != 0 or config.get("generation_eligible") is not False:
        issues.append("GENERATION_BOUNDARY")
    if config.get("runtime", {}).get("adb_server_port") != 5038 or config.get("runtime", {}).get("fallback_to_5037") is not False:
        issues.append("ADB_PORT_BOUNDARY")
    return issues


def load_manifest(path: Path, schema_path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        raise ValueError("; ".join(item.message for item in errors[:8]))
    return value


def _variant_issues(
    variant: dict[str, Any],
    *,
    family: dict[str, Any],
    ambiguity: str,
    repository_root: Path,
    config: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if variant["capture_status"] != "captured":
        return ["CAPTURE_FAILED"]
    if variant["role_ambiguity"] != ambiguity:
        issues.append("AMBIGUITY_LABEL_MISMATCH")
    root = Path(config["capture"]["output_root"]).as_posix().casefold()
    for key in ("screenshot", "raw_ui_tree", "setup_trace"):
        relative = variant[f"{key}_path"]
        if relative is None:
            issues.append(f"MISSING_{key.upper()}_PATH")
            continue
        normalized = Path(relative).as_posix().casefold()
        if not normalized.startswith(root + "/"):
            issues.append("ARTIFACT_OUTSIDE_B2_ROOT")
        path = repository_root / relative
        if not path.is_file():
            issues.append(f"MISSING_{key.upper()}")
        elif sha256_path(path) != variant[f"{key}_sha256"]:
            issues.append(f"{key.upper()}_HASH_MISMATCH")
    screenshot_hash = variant["screenshot_sha256"]
    if screenshot_hash in set(config["contamination"]["phase_a_dev_screenshot_sha256"]):
        issues.append("PHASE_A_DEV_SCREENSHOT_REUSED")
    stability = variant["stability"]
    for key in (
        "three_samples_present",
        "all_brackets_pixel_equal",
        "cross_sample_pixel_equal",
        "cross_sample_semantic_equal",
        "package_activity_stable",
        "geometry_orientation_stable",
    ):
        if stability.get(key) is not True:
            issues.append(f"STABILITY_{key.upper()}")
    if variant["reset_before"].get("passed") is not True:
        issues.append("RESET_BEFORE")
    if variant["reset_after"].get("passed") is not True:
        issues.append("RESET_AFTER")
    if variant["provenance"].get("foreground_package") != family["expected_package"]:
        issues.append("PACKAGE_MISMATCH")
    if variant["destination_widget_id"] != family["destination_target_id"]:
        issues.append("DESTINATION_WIDGET_ID_MISMATCH")
    target_ids = [item["target_id"] for item in variant["candidate_targets"]]
    if len(target_ids) != len(set(target_ids)):
        issues.append("DUPLICATE_TARGET_ID")
    destination = [item for item in variant["candidate_targets"] if item["target_id"] == family["destination_target_id"]]
    if len(destination) != 1 or destination[0]["entity_id"] != family["destination_entity_id"]:
        issues.append("DESTINATION_ORACLE_MISMATCH")
    if ambiguity == "high":
        source = [item for item in variant["candidate_targets"] if item["target_id"] == family["source_target_id"]]
        if len(source) != 1 or source[0]["entity_id"] != family["source_entity_id"]:
            issues.append("SOURCE_ORACLE_MISMATCH")
        if variant["source_target_id"] != family["source_target_id"]:
            issues.append("SOURCE_TARGET_ID_MISMATCH")
    elif variant["source_target_id"] is not None or variant["oracle_rationale"].get("source_anchor_count") != 0:
        issues.append("LOW_SOURCE_NOT_ABSENT")
    xml_path = variant.get("raw_ui_tree_path")
    if xml_path and (repository_root / xml_path).is_file():
        try:
            expected_targets, expected_rationale = build_oracle(
                raw_xml=(repository_root / xml_path).read_bytes(),
                family=family,
                ambiguity=ambiguity,
            )
            if expected_targets != variant["candidate_targets"]:
                issues.append("ORACLE_NOT_REPRODUCIBLE")
            if expected_rationale != variant["oracle_rationale"]:
                issues.append("RATIONALE_NOT_REPRODUCIBLE")
        except (ValueError, ET.ParseError):
            issues.append("ORACLE_REPLAY_FAILED")
    return issues


def qualify_manifest(
    manifest: dict[str, Any],
    *,
    repository_root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    family_results: list[dict[str, Any]] = []
    screenshot_hashes: list[str] = []
    tree_hashes: list[str] = []
    spec_by_id = {item["base_family_id"]: item for item in config["families"]}
    for family in manifest["families"]:
        spec = spec_by_id.get(family["base_family_id"])
        variant_results = []
        family_issues: list[str] = []
        if spec is None:
            family_issues.append("UNKNOWN_FAMILY")
        else:
            for key in ("app_id", "app_name", "expected_package", "driver", "task_semantics_id", "destination_widget_family", "task_without_value"):
                if family[key] != spec[key]:
                    family_issues.append(f"PAIRING_{key.upper()}")
            for ambiguity in ("low", "high"):
                variant = family["variants"][ambiguity]
                issues = _variant_issues(
                    variant,
                    family=spec,
                    ambiguity=ambiguity,
                    repository_root=repository_root,
                    config=config,
                )
                variant_results.append({"role_ambiguity": ambiguity, "passed": not issues, "issues": issues})
                if variant.get("screenshot_sha256"):
                    screenshot_hashes.append(variant["screenshot_sha256"])
                if variant.get("raw_ui_tree_sha256"):
                    tree_hashes.append(variant["raw_ui_tree_sha256"])
        passed = not family_issues and all(item["passed"] for item in variant_results)
        family_results.append(
            {
                "base_family_id": family["base_family_id"],
                "passed": passed,
                "family_issues": family_issues,
                "variants": variant_results,
            }
        )
    duplicate_screens = sorted(key for key, count in Counter(screenshot_hashes).items() if count > 1)
    duplicate_trees = sorted(key for key, count in Counter(tree_hashes).items() if count > 1)
    if duplicate_screens or duplicate_trees:
        for family_result in family_results:
            family_result["passed"] = False
            family_result["family_issues"].append("CORPUS_ARTIFACT_HASH_NOT_UNIQUE")
    qualified = sum(item["passed"] for item in family_results)
    total = len(family_results)
    rate = qualified / total if total else 0.0
    app_counts = Counter(item["app_id"] for item in manifest["families"])
    widget_families = {item["destination_widget_family"] for item in manifest["families"]}
    diversity = {
        "apps": len(app_counts),
        "app_family_counts": dict(sorted(app_counts.items())),
        "widget_families": len(widget_families),
        "maximum_families_in_one_app": max(app_counts.values(), default=0),
    }
    q = config["qualification"]
    diversity_pass = (
        diversity["apps"] >= q["minimum_apps"]
        and diversity["widget_families"] >= q["minimum_widget_families"]
        and diversity["maximum_families_in_one_app"] <= q["maximum_families_per_app"]
    )
    overall = (
        total == q["required_families"]
        and qualified >= q["minimum_complete_families"]
        and rate >= q["minimum_family_rate"]
        and diversity_pass
        and manifest["generation_calls"] == 0
        and manifest["collection"]["model_endpoint_called"] is False
    )
    first_broken_edge = None
    for result in family_results:
        if not result["passed"]:
            first_broken_edge = {
                "base_family_id": result["base_family_id"],
                "family_issues": result["family_issues"],
                "variants": result["variants"],
            }
            break
    if first_broken_edge is None and not diversity_pass:
        first_broken_edge = {"layer": "structural_diversity", "diversity": diversity}
    return {
        "verdict": "ELIGIBLE_FOR_PHASE_C_PREREGISTRATION" if overall else "NOT_ELIGIBLE",
        "generation_eligible": False,
        "generation_calls": 0,
        "total_families": total,
        "qualified_families": qualified,
        "family_qualification_rate": rate,
        "diversity": diversity,
        "duplicate_screenshot_hashes": duplicate_screens,
        "duplicate_ui_tree_hashes": duplicate_trees,
        "family_results": family_results,
        "first_broken_edge": first_broken_edge,
    }
