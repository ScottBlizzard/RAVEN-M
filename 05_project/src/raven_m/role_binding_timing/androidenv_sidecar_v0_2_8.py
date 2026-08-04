"""Lossless, fail-closed serialization for the B2.8 AndroidEnv a11y sidecar."""

from __future__ import annotations

import base64
import dataclasses
from hashlib import sha256
import json
import math
from typing import Any, Iterable

import numpy as np


ROUTE_LABEL = "androidenv_accessibility_sidecar"
UI_ELEMENT_FIELDS = (
    "text",
    "content_description",
    "class_name",
    "bbox",
    "bbox_pixels",
    "hint_text",
    "is_checked",
    "is_checkable",
    "is_clickable",
    "is_editable",
    "is_enabled",
    "is_focused",
    "is_focusable",
    "is_long_clickable",
    "is_scrollable",
    "is_selected",
    "is_visible",
    "package_name",
    "resource_name",
    "tooltip",
    "resource_id",
    "metadata",
)


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _qualified_type(value: Any) -> str:
    cls = type(value)
    return f"{cls.__module__}.{cls.__qualname__}"


def encode_typed(value: Any) -> dict[str, Any]:
    """Encode supported values without string coercion or float precision loss."""
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, np.bool_):
        return {"type": "numpy.bool", "dtype": str(value.dtype), "value": bool(value)}
    if isinstance(value, int):
        return {"type": "int", "value": str(value)}
    if isinstance(value, np.integer):
        return {"type": "numpy.int", "dtype": str(value.dtype), "value": str(int(value))}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("UNSUPPORTED_NONFINITE_FLOAT")
        return {"type": "float", "hex": value.hex()}
    if isinstance(value, np.floating):
        as_float = float(value)
        if not math.isfinite(as_float):
            raise TypeError("UNSUPPORTED_NONFINITE_NUMPY_FLOAT")
        return {"type": "numpy.float", "dtype": str(value.dtype), "hex": as_float.hex()}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, bytes):
        return {"type": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "type": "dataclass",
            "class": _qualified_type(value),
            "fields": [
                {"name": field.name, "value": encode_typed(getattr(value, field.name))}
                for field in dataclasses.fields(value)
            ],
        }
    if isinstance(value, list):
        return {"type": "list", "items": [encode_typed(item) for item in value]}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [encode_typed(item) for item in value]}
    if isinstance(value, dict):
        items = [
            {"key": encode_typed(key), "value": encode_typed(item)}
            for key, item in value.items()
        ]
        items.sort(key=lambda item: canonical_json_bytes(item["key"]))
        return {"type": "dict", "items": items}
    raise TypeError(f"UNSUPPORTED_SERIALIZATION_TYPE:{_qualified_type(value)}")


def serialize_ui_elements(elements: Iterable[Any]) -> tuple[bytes, dict[str, Any]]:
    """Serialize every dataclass field and return an auditable type manifest."""
    records: list[dict[str, Any]] = []
    actual_types: dict[str, set[str]] = {name: set() for name in UI_ELEMENT_FIELDS}
    null_counts: dict[str, int] = {name: 0 for name in UI_ELEMENT_FIELDS}
    declared_types: dict[str, str] = {}
    element_class: str | None = None
    for index, element in enumerate(elements):
        if not dataclasses.is_dataclass(element):
            raise TypeError(f"UI_ELEMENT_NOT_DATACLASS:{index}:{_qualified_type(element)}")
        fields = tuple(field.name for field in dataclasses.fields(element))
        if fields != UI_ELEMENT_FIELDS:
            raise ValueError(f"UI_ELEMENT_FIELD_DRIFT:{fields}")
        current_class = _qualified_type(element)
        if element_class is None:
            element_class = current_class
        elif current_class != element_class:
            raise TypeError(f"UI_ELEMENT_CLASS_DRIFT:{current_class}:{element_class}")
        encoded_fields: list[dict[str, Any]] = []
        for field in dataclasses.fields(element):
            value = getattr(element, field.name)
            declared_types[field.name] = str(field.type)
            actual_types[field.name].add(_qualified_type(value) if value is not None else "none")
            null_counts[field.name] += int(value is None)
            encoded_fields.append({"name": field.name, "value": encode_typed(value)})
        records.append({"index": index, "fields": encoded_fields})
    payload = {
        "schema_version": "role_binding_timing.androidenv_sidecar.elements.v0.2.8",
        "route_label": ROUTE_LABEL,
        "element_class": element_class,
        "field_order": list(UI_ELEMENT_FIELDS),
        "elements": records,
    }
    raw = canonical_json_bytes(payload)
    if canonical_json_bytes(json.loads(raw.decode("utf-8"))) != raw:
        raise RuntimeError("CANONICAL_JSON_ROUNDTRIP_FAILED")
    manifest = {
        "field_count": len(UI_ELEMENT_FIELDS),
        "field_order": list(UI_ELEMENT_FIELDS),
        "declared_types": declared_types,
        "actual_types": {name: sorted(values) for name, values in actual_types.items()},
        "null_counts": null_counts,
        "element_count": len(records),
        "element_class": element_class,
        "canonical_bytes": len(raw),
        "canonical_sha256": sha256_bytes(raw),
    }
    return raw, manifest


def validate_pixels(pixels: np.ndarray, expected_shape: tuple[int, int, int]) -> dict[str, Any]:
    if not isinstance(pixels, np.ndarray):
        raise TypeError(f"PIXELS_NOT_NDARRAY:{type(pixels).__name__}")
    if pixels.dtype != np.uint8:
        raise ValueError(f"PIXEL_DTYPE:{pixels.dtype}")
    if tuple(pixels.shape) != expected_shape:
        raise ValueError(f"PIXEL_SHAPE:{tuple(pixels.shape)}:{expected_shape}")
    if not pixels.flags.c_contiguous:
        raise ValueError("PIXELS_NOT_C_CONTIGUOUS")
    raw = pixels.tobytes(order="C")
    return {
        "shape": list(pixels.shape),
        "dtype": str(pixels.dtype),
        "order": "C",
        "raw_bytes": len(raw),
        "raw_sha256": sha256_bytes(raw),
    }


def deterministic_forest_bytes(forest: Any) -> bytes:
    if forest is None or not hasattr(forest, "SerializeToString"):
        raise TypeError("FOREST_NOT_PROTOBUF")
    raw = forest.SerializeToString(deterministic=True)
    if not raw:
        raise ValueError("FOREST_EMPTY_SERIALIZATION")
    if forest.SerializeToString(deterministic=True) != raw:
        raise RuntimeError("FOREST_NONDETERMINISTIC")
    return raw


def protobuf_field_manifest(message: Any) -> dict[str, Any]:
    """Describe the pinned protobuf field surface without reading values."""
    descriptor = getattr(message, "DESCRIPTOR", None)
    if descriptor is None:
        raise TypeError("FOREST_DESCRIPTOR_MISSING")
    seen: set[str] = set()
    messages: list[dict[str, Any]] = []

    def visit(current: Any) -> None:
        if current.full_name in seen:
            return
        seen.add(current.full_name)
        fields = []
        for field in sorted(current.fields, key=lambda item: item.number):
            item = {
                "name": field.name,
                "full_name": field.full_name,
                "number": field.number,
                "label": field.label,
                "type": field.type,
                "type_name": field.message_type.full_name if field.message_type else (
                    field.enum_type.full_name if field.enum_type else None
                ),
                "is_repeated": field.label == 3,
            }
            fields.append(item)
            if field.message_type is not None:
                visit(field.message_type)
        messages.append({"full_name": current.full_name, "fields": fields})

    visit(descriptor)
    messages.sort(key=lambda item: item["full_name"])
    result = {"root_message": descriptor.full_name, "messages": messages}
    result["canonical_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _bbox_record(value: Any) -> list[float | int] | None:
    if value is None:
        return None
    required = ("x_min", "x_max", "y_min", "y_max")
    if not all(hasattr(value, name) for name in required):
        return None
    return [getattr(value, name) for name in required]


def derive_stable_oracle_candidates(
    elements: Iterable[Any], *, expected_package: str, screen_width: int, screen_height: int
) -> list[dict[str, Any]]:
    """Derive strong, unique IDs without app/task literals or coordinates."""
    candidates: list[dict[str, Any]] = []
    for index, element in enumerate(elements):
        if getattr(element, "package_name", None) != expected_package:
            continue
        resource = getattr(element, "resource_name", None) or getattr(element, "resource_id", None)
        class_name = getattr(element, "class_name", None)
        bbox = _bbox_record(getattr(element, "bbox_pixels", None))
        if not resource or not class_name or bbox is None:
            continue
        x_min, x_max, y_min, y_max = bbox
        if not all(isinstance(value, (int, np.integer)) for value in bbox):
            continue
        if not (0 <= x_min < x_max <= screen_width and 0 <= y_min < y_max <= screen_height):
            continue
        identity = {
            "package_name": expected_package,
            "resource": resource,
            "class_name": class_name,
            "bbox_pixels": [int(value) for value in bbox],
        }
        candidates.append(
            {
                "element_index": index,
                "oracle_id": sha256_bytes(canonical_json_bytes(identity)),
                "identity": identity,
            }
        )
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate["oracle_id"]] = counts.get(candidate["oracle_id"], 0) + 1
    return [candidate for candidate in candidates if counts[candidate["oracle_id"]] == 1]


def qualify_observation(
    *,
    elements: list[Any],
    expected_package: str,
    foreground_packages: dict[str, list[str]],
    oracle_candidates: list[dict[str, Any]],
    pixel_validation: dict[str, Any],
    forest_bytes: bytes,
    identity_before: dict[str, Any],
    identity_after: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if not elements:
        issues.append("EMPTY_ACCESSIBILITY_ELEMENTS")
    element_packages = sorted(
        {getattr(item, "package_name", None) for item in elements if getattr(item, "package_name", None)}
    )
    if expected_package not in element_packages:
        issues.append("A11Y_EXPECTED_PACKAGE_MISSING")
    for source in ("activity_packages", "window_packages", "env_packages"):
        if expected_package not in foreground_packages.get(source, []):
            issues.append(f"FOREGROUND_{source.upper()}_MISSING")
    if not oracle_candidates:
        issues.append("STABLE_ORACLE_FIELDS_MISSING")
    if not pixel_validation.get("raw_sha256"):
        issues.append("SCREENSHOT_VALIDATION_MISSING")
    if not forest_bytes:
        issues.append("FOREST_BYTES_EMPTY")
    continuity_keys = (
        "adb_pid",
        "emulator_grpc_pid",
        "a11y_component",
        "a11y_apk_sha256",
        "sidecar_host_port",
        "sidecar_wrapper_id",
    )
    for key in continuity_keys:
        if identity_before.get(key) != identity_after.get(key):
            issues.append(f"IDENTITY_DRIFT:{key}")
    if identity_before.get("fallback_5037_listener_pids") or identity_after.get("fallback_5037_listener_pids"):
        issues.append("FORBIDDEN_5037_LISTENER")
    if not identity_before.get("qualified") or not identity_after.get("qualified"):
        issues.append("IDENTITY_NOT_QUALIFIED")
    return issues
