from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.collection_v0_2 import (
    build_oracle,
    load_manifest,
    parse_bounds,
    parse_ui_tree,
    qualify_manifest,
    resolve_exact_item,
    sha256_bytes,
    validate_collection_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "role_binding_timing" / "phase_b2_collection_v0_2.json"
SCHEMA_PATH = ROOT / "schemas" / "role_binding_timing_snapshot_pool.v0_2.schema.json"


def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def xml_for(family: dict, ambiguity: str) -> bytes:
    source = ""
    if ambiguity == "high":
        source = (
            f'<node text="{family["source_label"]}" resource-id="row_source" '
            'class="android.view.View" package="pkg" clickable="true" enabled="true" '
            'bounds="[10,300][900,430]" />'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hierarchy rotation="0">'
        '<node text="" resource-id="root" class="android.widget.FrameLayout" package="pkg" '
        'clickable="false" enabled="true" bounds="[0,0][1080,2400]">'
        '<node text="Menu" resource-id="toolbar" class="android.widget.ImageButton" package="pkg" '
        'clickable="true" enabled="true" bounds="[10,100][110,200]" />'
        f'{source}'
        f'<node text="{family["destination_label"]}" resource-id="row_destination" '
        'class="android.view.View" package="pkg" clickable="true" enabled="true" '
        'bounds="[10,500][900,630]" />'
        '</node></hierarchy>'
    ).encode("utf-8")


def test_config_has_structural_diversity_and_zero_generation() -> None:
    value = config()
    assert validate_collection_config(value) == []
    assert len({item["app_id"] for item in value["families"]}) == 8
    assert len({item["destination_widget_family"] for item in value["families"]}) == 8
    assert len({item["task_semantics_id"] for item in value["families"]}) == 8
    assert value["generation_calls_authorized"] == 0
    assert value["generation_eligible"] is False


def test_contacts_replication_is_rejected_as_pseudoreplication() -> None:
    value = config()
    for family in value["families"]:
        family["app_id"] = "contacts"
        family["destination_widget_family"] = "contacts_person_row"
    issues = validate_collection_config(value)
    assert "APP_DIVERSITY" in issues
    assert "APP_DOMINANCE" in issues
    assert "WIDGET_DIVERSITY" in issues


def test_bounds_reject_degenerate_or_malformed() -> None:
    assert parse_bounds("[1,2][3,4]") == [1, 2, 3, 4]
    with pytest.raises(ValueError):
        parse_bounds("[1,2][1,4]")
    with pytest.raises(ValueError):
        parse_bounds("1,2,3,4")


def test_high_oracle_resolves_distinct_source_destination_and_neutral() -> None:
    family = config()["families"][0]
    targets, rationale = build_oracle(
        raw_xml=xml_for(family, "high"), family=family, ambiguity="high"
    )
    assert {item["target_id"] for item in targets} == {
        family["destination_target_id"],
        family["source_target_id"],
        family["neutral_target_id"],
    }
    assert rationale["source_anchor_count"] == 1
    assert rationale["independently_checkable"] is True


def test_low_oracle_requires_source_absent() -> None:
    family = config()["families"][0]
    targets, rationale = build_oracle(
        raw_xml=xml_for(family, "low"), family=family, ambiguity="low"
    )
    assert len(targets) == 2
    assert rationale["source_anchor_count"] == 0
    with pytest.raises(ValueError, match="LOW_SOURCE_PRESENT"):
        build_oracle(
            raw_xml=xml_for(family, "high"), family=family, ambiguity="low"
        )


def test_exact_anchor_corruption_fails_closed() -> None:
    family = config()["families"][0]
    raw = xml_for(family, "low").replace(
        b"</node></hierarchy>",
        f'<node text="{family["destination_label"]}" resource-id="duplicate" class="android.view.View" package="pkg" clickable="true" enabled="true" bounds="[10,700][900,830]" /></node></hierarchy>'.encode(),
    )
    tree = parse_ui_tree(raw)
    with pytest.raises(ValueError, match="ITEM_ANCHOR_COUNT"):
        resolve_exact_item(tree, family["destination_label"])


def synthetic_manifest(tmp_path: Path) -> tuple[dict, dict]:
    value = config()
    value["capture"]["output_root"] = "pool"
    families = []
    for index, family in enumerate(value["families"]):
        variants = {}
        for ambiguity_index, ambiguity in enumerate(("low", "high")):
            variant_root = tmp_path / "pool" / "families" / family["base_family_id"] / ambiguity
            variant_root.mkdir(parents=True)
            png = f"png-{index}-{ambiguity_index}".encode()
            xml = xml_for(family, ambiguity)
            screenshot = variant_root / "selected_frame.png"
            ui_tree = variant_root / "selected_ui.xml"
            trace = variant_root / "setup_trace.json"
            screenshot.write_bytes(png)
            ui_tree.write_bytes(xml)
            trace.write_text("{}\n", encoding="utf-8")
            targets, rationale = build_oracle(raw_xml=xml, family=family, ambiguity=ambiguity)
            variants[ambiguity] = {
                "role_ambiguity": ambiguity,
                "capture_status": "captured",
                "error": None,
                "development_contaminated": False,
                "held_out_eligible": False,
                "artifact_root": variant_root.relative_to(tmp_path).as_posix(),
                "screenshot_path": screenshot.relative_to(tmp_path).as_posix(),
                "screenshot_sha256": sha256_bytes(png),
                "raw_ui_tree_path": ui_tree.relative_to(tmp_path).as_posix(),
                "raw_ui_tree_sha256": sha256_bytes(xml),
                "setup_trace_path": trace.relative_to(tmp_path).as_posix(),
                "setup_trace_sha256": sha256_bytes(trace.read_bytes()),
                "sample_records": [{}, {}, {}],
                "stability": {
                    "three_samples_present": True,
                    "all_brackets_pixel_equal": True,
                    "cross_sample_pixel_equal": True,
                    "cross_sample_semantic_equal": True,
                    "package_activity_stable": True,
                    "geometry_orientation_stable": True,
                },
                "provenance": {"foreground_package": family["expected_package"]},
                "reset_before": {"passed": True},
                "reset_after": {"passed": True},
                "source_target_id": family["source_target_id"] if ambiguity == "high" else None,
                "destination_target_id": family["destination_target_id"],
                "destination_widget_id": family["destination_target_id"],
                "candidate_targets": targets,
                "oracle_rationale": rationale,
            }
        families.append(
            {
                "base_family_id": family["base_family_id"],
                "app_id": family["app_id"],
                "app_name": family["app_name"],
                "expected_package": family["expected_package"],
                "driver": family["driver"],
                "task_semantics_id": family["task_semantics_id"],
                "destination_widget_family": family["destination_widget_family"],
                "task_without_value": family["task_without_value"],
                "fact": {
                    "field": family["field"],
                    "value": family["fact_value"],
                    "source_entity_id": family["source_entity_id"],
                    "destination_entity_id": family["destination_entity_id"],
                    "source_label": family["source_label"],
                    "destination_label": family["destination_label"],
                },
                "collection_order": family["variant_order"],
                "variants": variants,
            }
        )
    manifest = {
        "schema_version": "role_binding_timing.snapshot_pool.v0_2",
        "study_id": "role_binding_timing_phase_b2_v0_2",
        "generation_calls": 0,
        "frozen_before_qualification": True,
        "protocol_freeze_commit": "a" * 40,
        "collection": {
            "started_at": "start",
            "finished_at": "finish",
            "wall_time_seconds": 1.0,
            "capture_attempts": 16,
            "model_endpoint_called": False,
            "candidate_replacements": 0,
        },
        "runtime": {str(index): index for index in range(8)},
        "families": families,
    }
    return manifest, value


def test_synthetic_structurally_diverse_pool_qualifies(tmp_path: Path) -> None:
    manifest, value = synthetic_manifest(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_manifest(path, SCHEMA_PATH)
    result = qualify_manifest(loaded, repository_root=tmp_path, config=value)
    assert result["verdict"] == "ELIGIBLE_FOR_PHASE_C_PREREGISTRATION"
    assert result["qualified_families"] == 8
    assert result["diversity"]["apps"] == 8


def test_duplicate_artifact_hash_fails_entire_pool(tmp_path: Path) -> None:
    manifest, value = synthetic_manifest(tmp_path)
    first = manifest["families"][0]["variants"]["low"]
    second = manifest["families"][0]["variants"]["high"]
    second_path = tmp_path / second["screenshot_path"]
    first_bytes = (tmp_path / first["screenshot_path"]).read_bytes()
    second_path.write_bytes(first_bytes)
    second["screenshot_sha256"] = first["screenshot_sha256"]
    result = qualify_manifest(manifest, repository_root=tmp_path, config=value)
    assert result["verdict"] == "NOT_ELIGIBLE"
    assert result["duplicate_screenshot_hashes"] == [first["screenshot_sha256"]]


def test_dev_denylist_hash_is_excluded(tmp_path: Path) -> None:
    manifest, value = synthetic_manifest(tmp_path)
    variant = manifest["families"][0]["variants"]["low"]
    denylisted_bytes = b"dev-contaminated"
    denylisted_hash = sha256_bytes(denylisted_bytes)
    (tmp_path / variant["screenshot_path"]).write_bytes(denylisted_bytes)
    variant["screenshot_sha256"] = denylisted_hash
    value["contamination"]["phase_a_dev_screenshot_sha256"].append(denylisted_hash)
    result = qualify_manifest(manifest, repository_root=tmp_path, config=value)
    issues = result["family_results"][0]["variants"][0]["issues"]
    assert "PHASE_A_DEV_SCREENSHOT_REUSED" in issues
    assert result["verdict"] == "NOT_ELIGIBLE"


def test_generation_or_port_drift_fails_config() -> None:
    value = config()
    value["generation_calls_authorized"] = 1
    value["runtime"]["adb_server_port"] = 5037
    issues = validate_collection_config(value)
    assert "GENERATION_BOUNDARY" in issues
    assert "ADB_PORT_BOUNDARY" in issues
