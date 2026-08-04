"""Fresh screenshot/UI-tree and oracle qualification."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.contract import SNAPSHOT_SCHEMA_PATH


@dataclass(frozen=True)
class SnapshotQualification:
    total_variants: int
    qualified_variants: int
    rate: float
    retained_base_families: int
    issues: tuple[dict[str, str], ...]


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_snapshot_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SNAPSHOT_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:5]))
    return value


def _variant_issues(
    *,
    family: dict[str, Any],
    ambiguity: str,
    repository_root: Path,
) -> list[str]:
    variant = family["variants"][ambiguity]
    issues: list[str] = []
    if variant["role_ambiguity"] != ambiguity:
        issues.append("ambiguity_label_mismatch")
    for key in ("screenshot", "ui_tree"):
        path = repository_root / variant[f"{key}_path"]
        if not path.is_file():
            issues.append(f"missing_{key}")
        elif _digest(path) != variant[f"{key}_sha256"]:
            issues.append(f"{key}_hash_mismatch")
    targets = variant["candidate_targets"]
    target_ids = [item["target_id"] for item in targets]
    selectors = [item["selector"] for item in targets]
    if len(target_ids) != len(set(target_ids)):
        issues.append("duplicate_target_id")
    if len(selectors) != len(set(selectors)):
        issues.append("nonunique_ui_tree_selector")
    destination = next(
        (
            item
            for item in targets
            if item["target_id"] == variant["destination_target_id"]
        ),
        None,
    )
    if destination is None:
        issues.append("destination_target_missing")
    else:
        if destination["entity_id"] != variant["destination_entity_id"]:
            issues.append("destination_entity_oracle_mismatch")
        if destination["widget_role"] != variant["destination_widget_role"]:
            issues.append("destination_widget_oracle_mismatch")
    source_target = variant.get("source_target_id")
    if source_target is not None and source_target not in target_ids:
        issues.append("source_target_missing")
    if variant["source_entity_id"] == variant["destination_entity_id"]:
        issues.append("source_destination_entity_not_distinct")
    if ambiguity == "high":
        groups: dict[str, int] = {}
        for item in targets:
            groups[item["ambiguity_group"]] = groups.get(item["ambiguity_group"], 0) + 1
        if max(groups.values(), default=0) < 2:
            issues.append("high_ambiguity_has_no_competing_group")
    return issues


def qualify_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    repository_root: Path,
) -> SnapshotQualification:
    issue_records: list[dict[str, str]] = []
    qualified = 0
    retained = 0
    for family in manifest["base_families"]:
        family_ok = True
        for ambiguity in ("low", "high"):
            issues = _variant_issues(
                family=family,
                ambiguity=ambiguity,
                repository_root=repository_root,
            )
            if issues:
                family_ok = False
                issue_records.extend(
                    {
                        "base_family_id": family["base_family_id"],
                        "role_ambiguity": ambiguity,
                        "issue": issue,
                    }
                    for issue in issues
                )
            else:
                qualified += 1
        if family_ok:
            retained += 1
    total = len(manifest["base_families"]) * 2
    return SnapshotQualification(
        total_variants=total,
        qualified_variants=qualified,
        rate=(qualified / total) if total else 0.0,
        retained_base_families=retained,
        issues=tuple(issue_records),
    )
