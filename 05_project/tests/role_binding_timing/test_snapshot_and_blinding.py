from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.design import build_blinded_cells
from raven_m.role_binding_timing.snapshots import (
    load_snapshot_manifest,
    qualify_snapshot_manifest,
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_manifest(tmp_path: Path, *, corrupt_hash: bool = False) -> Path:
    image = tmp_path / "screen.png"
    tree = tmp_path / "tree.json"
    image.write_bytes(b"fresh-png-placeholder")
    tree.write_text('{"nodes":[]}', encoding="utf-8")

    def variant(level: str) -> dict[str, object]:
        return {
            "role_ambiguity": level,
            "screenshot_path": "screen.png",
            "screenshot_sha256": "0" * 64 if corrupt_hash else digest(image),
            "ui_tree_path": "tree.json",
            "ui_tree_sha256": digest(tree),
            "source_entity_id": "E1",
            "destination_entity_id": "E2",
            "source_target_id": "A",
            "destination_target_id": "B",
            "destination_widget_role": "input",
            "candidate_targets": [
                {"target_id": "A", "selector": "node/source", "entity_id": "E1", "widget_role": "input", "bounds": [0, 0, 10, 10], "ambiguity_group": "fields"},
                {"target_id": "B", "selector": "node/destination", "entity_id": "E2", "widget_role": "input", "bounds": [10, 0, 20, 10], "ambiguity_group": "fields"}
            ]
        }

    payload = {
        "schema_version": "role_binding_timing.snapshot_manifest.v0_1",
        "study_id": "role_binding_timing_stage1_v0_1",
        "frozen_before_condition_assignment": True,
        "base_families": [
            {
                "base_family_id": "BF-001",
                "collection_batch": "fresh-test-batch",
                "development_contaminated": False,
                "held_out_eligible": True,
                "task_without_value": "Enter the requested field at the destination.",
                "fact": {"source_entity_id": "E1", "field": "code", "value": "PX-4917"},
                "variants": {"low": variant("low"), "high": variant("high")}
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_fresh_paired_snapshot_and_oracle_qualify(tmp_path: Path) -> None:
    manifest = load_snapshot_manifest(write_manifest(tmp_path))
    result = qualify_snapshot_manifest(manifest, repository_root=tmp_path)
    assert result.total_variants == 2
    assert result.qualified_variants == 2
    assert result.rate == 1.0
    assert result.retained_base_families == 1


def test_hash_corruption_is_detected(tmp_path: Path) -> None:
    manifest = load_snapshot_manifest(write_manifest(tmp_path, corrupt_hash=True))
    result = qualify_snapshot_manifest(manifest, repository_root=tmp_path)
    assert result.rate == 0
    assert {item["issue"] for item in result.issues} == {"screenshot_hash_mismatch"}


def test_contaminated_snapshot_cannot_pass_schema(tmp_path: Path) -> None:
    path = write_manifest(tmp_path)
    payload = json.loads(path.read_text())
    payload["base_families"][0]["development_contaminated"] = True
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="False was expected"):
        load_snapshot_manifest(path)


def test_blinding_has_four_unique_cells_per_base_and_private_mapping() -> None:
    public, private = build_blinded_cells(
        ["BF-002", "BF-001"],
        secret=b"offline-test-secret",
    )
    assert len(public) == 8
    assert len(private) == 8
    assert all(set(item) == {"cell_id", "base_family_id"} for item in public)
    assert {value["fact_timing"] for value in private.values()} == {"early", "late"}
    assert {value["role_ambiguity"] for value in private.values()} == {"low", "high"}
