from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.androidenv_sidecar_v0_2_8 import (
    ROUTE_LABEL,
    UI_ELEMENT_FIELDS,
    canonical_json_bytes,
    derive_stable_oracle_candidates,
    deterministic_forest_bytes,
    encode_typed,
    protobuf_field_manifest,
    qualify_observation,
    serialize_ui_elements,
    validate_pixels,
)
from raven_m.role_binding_timing.androidenv_sidecar_runtime_v0_2_8 import (
    FailClosedA11yController,
)


ROOT = Path(__file__).resolve().parents[2]


@dataclasses.dataclass
class Box:
    x_min: int
    x_max: int
    y_min: int
    y_max: int


@dataclasses.dataclass
class Element:
    text: str | None = None
    content_description: str | None = None
    class_name: str | None = None
    bbox: Box | None = None
    bbox_pixels: Box | None = None
    hint_text: str | None = None
    is_checked: bool | None = None
    is_checkable: bool | None = None
    is_clickable: bool | None = None
    is_editable: bool | None = None
    is_enabled: bool | None = None
    is_focused: bool | None = None
    is_focusable: bool | None = None
    is_long_clickable: bool | None = None
    is_scrollable: bool | None = None
    is_selected: bool | None = None
    is_visible: bool | None = None
    package_name: str | None = None
    resource_name: str | None = None
    tooltip: str | None = None
    resource_id: str | None = None
    metadata: dict | None = None


def element(**values) -> Element:
    defaults = {
        "class_name": "android.widget.TextView",
        "bbox_pixels": Box(10, 110, 20, 80),
        "package_name": "com.example",
        "resource_name": "com.example:id/title",
        "is_visible": True,
        "metadata": {"unicode": "值", "count": 3, "ratio": 0.5},
    }
    defaults.update(values)
    return Element(**defaults)


def identity(**values) -> dict:
    result = {
        "qualified": True,
        "adb_pid": 10,
        "emulator_grpc_pid": 20,
        "a11y_component": "component",
        "a11y_apk_sha256": "a" * 64,
        "sidecar_host_port": 12345,
        "sidecar_wrapper_id": 999,
        "fallback_5037_listener_pids": [],
    }
    result.update(values)
    return result


def test_typed_encoding_is_deterministic_and_precision_preserving() -> None:
    value = {"z": 7, "a": [True, None, 0.1, b"raw", "值"]}
    first = canonical_json_bytes(encode_typed(value))
    second = canonical_json_bytes(encode_typed(value))
    assert first == second
    parsed = json.loads(first)
    float_item = parsed["items"][0]["value"]["items"][2] if parsed["items"][0]["key"]["value"] == "a" else parsed["items"][1]["value"]["items"][2]
    assert float.fromhex(float_item["hex"]) == 0.1


def test_rejects_unknown_and_nonfinite_types() -> None:
    with pytest.raises(TypeError, match="UNSUPPORTED_SERIALIZATION_TYPE"):
        encode_typed(object())
    with pytest.raises(TypeError, match="NONFINITE"):
        encode_typed(float("nan"))


def test_all_fields_are_serialized_with_type_manifest() -> None:
    raw, manifest = serialize_ui_elements([element(text="Settings")])
    payload = json.loads(raw)
    assert tuple(payload["field_order"]) == UI_ELEMENT_FIELDS
    assert len(payload["elements"][0]["fields"]) == len(UI_ELEMENT_FIELDS) == 22
    assert manifest["field_count"] == 22
    assert manifest["actual_types"]["metadata"] == ["builtins.dict"]
    assert manifest["canonical_sha256"]
    assert payload["route_label"] == ROUTE_LABEL


def test_field_drift_and_serialization_corruption_fail() -> None:
    @dataclasses.dataclass
    class BadElement:
        text: str = "only"

    with pytest.raises(ValueError, match="UI_ELEMENT_FIELD_DRIFT"):
        serialize_ui_elements([BadElement()])
    raw, _ = serialize_ui_elements([element()])
    corrupted = raw[:-1] + b"x"
    with pytest.raises(json.JSONDecodeError):
        json.loads(corrupted)


def test_pixels_require_exact_uint8_c_order_and_shape() -> None:
    pixels = np.zeros((4, 3, 3), dtype=np.uint8)
    assert validate_pixels(pixels, (4, 3, 3))["raw_bytes"] == 36
    with pytest.raises(ValueError, match="PIXEL_DTYPE"):
        validate_pixels(pixels.astype(np.float32), (4, 3, 3))
    with pytest.raises(ValueError, match="PIXEL_SHAPE"):
        validate_pixels(pixels, (3, 4, 3))


def test_forest_must_be_nonempty_and_deterministic() -> None:
    class Forest:
        def SerializeToString(self, deterministic: bool = False) -> bytes:
            assert deterministic
            return b"forest"

    assert deterministic_forest_bytes(Forest()) == b"forest"
    with pytest.raises(ValueError, match="FOREST_EMPTY"):
        deterministic_forest_bytes(type("Empty", (), {"SerializeToString": lambda self, deterministic: b""})())


def test_protobuf_manifest_covers_nested_field_types() -> None:
    from android_env.proto.a11y import android_accessibility_forest_pb2

    forest = android_accessibility_forest_pb2.AndroidAccessibilityForest()
    manifest = protobuf_field_manifest(forest)
    assert manifest["root_message"].endswith("AndroidAccessibilityForest")
    assert any(item["full_name"].endswith("AndroidAccessibilityNodeInfo") for item in manifest["messages"])
    assert all("type" in field and "label" in field for item in manifest["messages"] for field in item["fields"])
    assert len(manifest["canonical_sha256"]) == 64


def test_stable_oracle_requires_unique_strong_resource_identity() -> None:
    unique = derive_stable_oracle_candidates(
        [element(text="one")], expected_package="com.example", screen_width=1080, screen_height=2400
    )
    assert len(unique) == 1
    duplicates = derive_stable_oracle_candidates(
        [element(text="one"), element(text="two")],
        expected_package="com.example",
        screen_width=1080,
        screen_height=2400,
    )
    assert duplicates == []
    assert derive_stable_oracle_candidates(
        [element(resource_name=None, text="weak")],
        expected_package="com.example",
        screen_width=1080,
        screen_height=2400,
    ) == []


def test_qualification_fails_empty_mismatch_and_identity_drift() -> None:
    pixels = validate_pixels(np.zeros((4, 3, 3), dtype=np.uint8), (4, 3, 3))
    good = identity()
    issues = qualify_observation(
        elements=[],
        expected_package="com.example",
        foreground_packages={"activity_packages": [], "window_packages": [], "env_packages": []},
        oracle_candidates=[],
        pixel_validation=pixels,
        forest_bytes=b"forest",
        identity_before=good,
        identity_after=identity(sidecar_host_port=54321),
    )
    assert "EMPTY_ACCESSIBILITY_ELEMENTS" in issues
    assert "A11Y_EXPECTED_PACKAGE_MISSING" in issues
    assert "STABLE_ORACLE_FIELDS_MISSING" in issues
    assert "IDENTITY_DRIFT:sidecar_host_port" in issues


def test_fail_closed_controller_does_not_refresh() -> None:
    assert "IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN" in FailClosedA11yController.refresh_env.__code__.co_consts
    source = (ROOT / "src/raven_m/role_binding_timing/androidenv_sidecar_runtime_v0_2_8.py").read_text(encoding="utf-8")
    assert "install_a11y_forwarding_app=False" in source
    assert "adb_server_port != 5038" in source
    assert "refresh_env()" not in source


def test_protocol_config_and_schema_boundaries() -> None:
    config = json.loads(
        (ROOT / "configs/role_binding_timing/phase_b2_8_androidenv_sidecar_diagnosis.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "schemas/role_binding_timing_androidenv_sidecar_observation.v0_2_8.schema.json").read_text(encoding="utf-8")
    )
    assert config["generation_calls_authorized"] == 0
    assert config["generation_eligible"] is False
    assert config["held_out_eligible"] is False
    assert config["route_label"] == ROUTE_LABEL
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["emulator_grpc_port"] == 8554
    assert config["runtime"]["fallback_to_5037"] is False
    assert config["diagnostic"]["explicit_get_state_calls"] == 1
    Draft202012Validator.check_schema(schema)
