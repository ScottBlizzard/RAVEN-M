#!/usr/bin/env python3
"""Independently verify the frozen A12 reference-segment feasibility.

This builder deliberately does not import the A12 production memory and never
reads A12 candidates or replay output.  It reimplements the frozen RGB,
screen-equivalence, action-family, and state-reset rules over materialized raw
episodes.  Its purpose is to detect a protocol-invalid design before GPU use.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import unicodedata
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
FROZEN_A10_REPORT = ROOT / "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json"
MATERIALIZED_MANIFEST = ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _verify_materialized_trace(trace_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify every materialized input byte before deriving the stop verdict."""
    declared = [
        item
        for record in manifest.get("records") or []
        for item in record.get("files") or []
    ] + list(manifest.get("suite_files") or [])
    root = trace_root.resolve()
    errors: list[str] = []
    observed_bytes = 0
    for item in declared:
        relative = Path(str(item["path"]))
        path = (root / relative).resolve()
        if root not in path.parents:
            errors.append(f"path_outside_trace_root:{relative.as_posix()}")
            continue
        if not path.is_file():
            errors.append(f"missing:{relative.as_posix()}")
            continue
        size = path.stat().st_size
        observed_bytes += size
        if size != int(item["bytes"]):
            errors.append(f"size_mismatch:{relative.as_posix()}")
            continue
        if _sha(path) != str(item["sha256"]):
            errors.append(f"sha256_mismatch:{relative.as_posix()}")
    if len(declared) != int(manifest.get("file_count", -1)):
        errors.append("manifest_file_count_mismatch")
    if observed_bytes != int(manifest.get("total_bytes", -1)):
        errors.append("manifest_total_bytes_mismatch")
    return {
        "status": "pass" if not errors else "fail",
        "declared_file_count": len(declared),
        "observed_total_bytes": observed_bytes,
        "errors": errors,
    }


def _pixels(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _visible_rgb(pixels: np.ndarray) -> np.ndarray:
    value = np.asarray(pixels)
    if (
        value.ndim != 3
        or value.shape[0] < 25
        or value.shape[1] < 8
        or value.shape[2] < 3
        or not np.issubdtype(value.dtype, np.integer)
        or (value.size and (int(value.min()) < 0 or int(value.max()) > 255))
    ):
        raise RuntimeError("invalid model-visible RGB")
    return np.ascontiguousarray(value[:, :, :3])


def _descriptor(pixels: np.ndarray) -> dict[str, Any]:
    rgb = _visible_rgb(pixels)
    top = int(math.floor(0.04 * rgb.shape[0]))
    bottom = int(math.ceil(0.96 * rgb.shape[0]))
    crop = np.ascontiguousarray(rgb[top:bottom, :, :3])
    exact_payload = f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()

    def bounds(size: int, count: int, index: int) -> tuple[int, int]:
        start = min(size - 1, max(0, int(math.floor(index * size / count))))
        stop = min(size, max(start + 1, int(math.ceil((index + 1) * size / count))))
        return start, stop

    integral = crop.astype(np.uint64).cumsum(axis=0).cumsum(axis=1)

    def rectangle_sum(r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
        total = integral[r1 - 1, c1 - 1].copy()
        if r0:
            total -= integral[r0 - 1, c1 - 1]
        if c0:
            total -= integral[r1 - 1, c0 - 1]
        if r0 and c0:
            total += integral[r0 - 1, c0 - 1]
        return total

    luma: list[int] = []
    for row in range(9):
        r0, r1 = bounds(crop.shape[0], 9, row)
        for column in range(16):
            c0, c1 = bounds(crop.shape[1], 16, column)
            mean = rectangle_sum(r0, r1, c0, c1) // ((r1 - r0) * (c1 - c0))
            y = (77 * int(mean[0]) + 150 * int(mean[1]) + 29 * int(mean[2])) // 256
            luma.append(min(15, max(0, y // 16)))
    matrix = np.asarray(luma, dtype=np.uint8).reshape(9, 16)
    edge_values = np.concatenate(
        ((matrix[:, 1:] > matrix[:, :-1]).ravel(), (matrix[1:, :] > matrix[:-1, :]).ravel())
    ).astype(np.uint8)
    edge_bytes = np.packbits(edge_values, bitorder="big").tobytes()
    return {
        "exact_sha256": sha256(exact_payload).hexdigest(),
        "descriptor_sha256": sha256(bytes(luma) + edge_bytes).hexdigest(),
        "luma_q": luma,
        "edge_bits_hex": edge_bytes.hex(),
        "crop_shape": list(crop.shape),
    }


def _distance(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, float, float]:
    if left["exact_sha256"] == right["exact_sha256"]:
        return 0.0, 0.0, 0.0
    luma_left = np.asarray(left["luma_q"], dtype=np.int16)
    luma_right = np.asarray(right["luma_q"], dtype=np.int16)
    dl = float(np.abs(luma_left - luma_right).sum()) / (144.0 * 15.0)
    edges_left = np.unpackbits(
        np.frombuffer(bytes.fromhex(left["edge_bits_hex"]), dtype=np.uint8),
        bitorder="big",
    )[:263]
    edges_right = np.unpackbits(
        np.frombuffer(bytes.fromhex(right["edge_bits_hex"]), dtype=np.uint8),
        bitorder="big",
    )[:263]
    de = float(np.count_nonzero(edges_left != edges_right)) / 263.0
    return dl, de, 0.7 * dl + 0.3 * de


def _equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    dl, de, dv = _distance(left, right)
    return dl <= 0.06 and de <= 0.12 and dv <= 0.055


def _changed_fraction(before: np.ndarray, after: np.ndarray) -> float:
    left, right = _visible_rgb(before), _visible_rgb(after)
    if left.shape != right.shape:
        return 1.0
    delta = np.max(np.abs(left.astype(np.int16) - right.astype(np.int16)), axis=2)
    return float(np.count_nonzero(delta > 5)) / float(delta.size)


def _coordinate(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError("invalid canonical coordinate")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise RuntimeError("invalid canonical coordinate")
    return result


def _duration(value: Any) -> str:
    result = float(value or 0)
    return "short" if result < 700 else "medium" if result <= 1500 else "long"


def _family(action: dict[str, Any]) -> tuple[Any, ...]:
    kind = str(action.get("type") or "")
    if kind in {"tap", "long_press"}:
        x, y = _coordinate(action.get("x")), _coordinate(action.get("y"))
        result: tuple[Any, ...] = (kind, min(11, int(12 * x)), min(23, int(24 * y)))
        return result + ((_duration(action.get("duration_ms")),) if kind == "long_press" else ())
    if kind == "swipe":
        x, y, x2, y2 = (_coordinate(action.get(key)) for key in ("x", "y", "x2", "y2"))
        dx, dy = x2 - x, y2 - y
        direction = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")
        length = math.hypot(dx, dy)
        bucket = "short" if length < 0.25 else "medium" if length < 0.55 else "long"
        return (kind, direction, bucket, min(2, int(3 * x)), min(3, int(4 * y)))
    if kind == "type_text":
        text = unicodedata.normalize("NFKC", str(action.get("text") or ""))
        size = len(text)
        bucket = "1-8" if size <= 8 else "9-32" if size <= 32 else "33-96" if size <= 96 else "97+"
        return (kind, sha256(text.encode()).hexdigest(), bucket, bool(action.get("clear_text")))
    if kind == "wait":
        return (kind, _duration(action.get("duration_ms")))
    if kind == "answer":
        text = unicodedata.normalize("NFKC", str(action.get("text") or ""))
        return (kind, sha256(text.encode()).hexdigest())
    if kind in {"press_back", "press_home", "press_enter", "press_recents"}:
        return (kind,)
    raise RuntimeError(f"unsupported canonical action: {kind!r}")


def _action(step: dict[str, Any]) -> dict[str, Any]:
    return dict(
        (step.get("decision") or {}).get("canonical_action")
        or (step.get("mapped_action") or {}).get("canonical")
        or {}
    )


def _audit_descriptor(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "exact_sha256": value["exact_sha256"],
        "descriptor_sha256": value["descriptor_sha256"],
        "crop_shape": value["crop_shape"],
    }


def build(trace_root: Path) -> dict[str, Any]:
    frozen = _load(FROZEN_A10_REPORT)
    manifest = _load(MATERIALIZED_MANIFEST)
    materialized_verification = _verify_materialized_trace(trace_root, manifest)
    manifest_by_episode = {
        str(item["episode_id"]): item for item in manifest.get("records") or []
    }
    references: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for episode in frozen.get("episodes") or []:
        if episode.get("role") != "a6":
            continue
        for item in episode.get("loop_qualification_records") or []:
            references.append((episode, item))

    segments: list[dict[str, Any]] = []
    for episode_record, reference in references:
        episode_id = str(episode_record["episode_id"])
        episode_dir = trace_root / "a6" / "episodes" / episode_id
        episode_path = episode_dir / "episode.json"
        episode = _load(episode_path)
        steps = [item for item in episode.get("steps") or [] if item.get("executed")]
        second = int(reference["second_no_progress_step"])
        second_step = steps[second]
        second_before = _pixels(episode_dir / second_step["before"]["screenshot"])
        second_after = _pixels(episode_dir / second_step["after"]["screenshot"])
        second_before_desc = _descriptor(second_before)
        second_after_desc = _descriptor(second_after)
        second_fraction = _changed_fraction(second_before, second_after)
        family = _family(_action(second_step))
        second_valid = second_fraction <= 0.001 and _equivalent(
            second_before_desc, second_after_desc
        )

        candidates: list[dict[str, Any]] = []
        for first in range(max(0, second - 12), second):
            first_step = steps[first]
            if _family(_action(first_step)) != family:
                continue
            first_before = _pixels(episode_dir / first_step["before"]["screenshot"])
            first_after = _pixels(episode_dir / first_step["after"]["screenshot"])
            first_before_desc = _descriptor(first_before)
            first_after_desc = _descriptor(first_after)
            first_fraction = _changed_fraction(first_before, first_after)
            if (
                first_fraction > 0.001
                or not _equivalent(first_before_desc, first_after_desc)
                or not _equivalent(first_before_desc, second_before_desc)
            ):
                continue
            chain_valid = True
            reset_step: int | None = None
            for middle in range(first + 1, second):
                middle_step = steps[middle]
                middle_before = _pixels(episode_dir / middle_step["before"]["screenshot"])
                middle_after = _pixels(episode_dir / middle_step["after"]["screenshot"])
                middle_before_desc = _descriptor(middle_before)
                middle_after_desc = _descriptor(middle_after)
                middle_fraction = _changed_fraction(middle_before, middle_after)
                if (
                    middle_fraction > 0.001
                    or not _equivalent(middle_before_desc, middle_after_desc)
                    or not _equivalent(middle_before_desc, first_before_desc)
                ):
                    chain_valid = False
                    reset_step = middle
                    break
            candidates.append(
                {
                    "first_source_step": first,
                    "first_changed_fraction": round(first_fraction, 9),
                    "no_reset_between_supports": chain_valid,
                    "first_reset_source_step": reset_step,
                    "first_screen": _audit_descriptor(first_before_desc),
                }
            )

        valid_candidates = [item for item in candidates if item["no_reset_between_supports"]]
        first = valid_candidates[-1] if valid_candidates else None
        independently_valid = bool(second_valid and first is not None)
        manifest_record = manifest_by_episode[episode_id]
        identity = {
            "episode_id": episode_id,
            "second_failure_source_step": second,
            "a10_source_frontier_id": reference["source_frontier_id"],
            "a10_branch_id": reference["branch_id"],
        }
        segments.append(
            {
                "segment_id": f"a12seg_{_canonical_sha(identity)[:16]}",
                "role": "a6",
                "episode_id": episode_id,
                "task_name_audit_only": episode.get("task_name"),
                "legacy_a10_identity": identity,
                "episode_json_sha256": manifest_record["episode_json_sha256"],
                "first_failure_source_step": None if first is None else first["first_source_step"],
                "second_failure_source_step": second,
                "required_maturity_step": second,
                "required_actual_read_step": second + 1,
                "action_family": family,
                "second_changed_fraction": round(second_fraction, 9),
                "second_no_progress": second_valid,
                "second_screen": _audit_descriptor(second_before_desc),
                "second_screen_full": second_before_desc,
                "prior_support_candidates": candidates,
                "pairwise_support_valid": independently_valid,
                "independently_valid_for_a12": False,
                "invalid_reason": None if independently_valid else "no_surviving_first_support_under_a12_reset_rules",
            }
        )

    # Pairwise validity is only a loose upper bound.  The real A12 state machine
    # matures on the chronological second support, reads immediately, records a
    # semantic one-shot, and then enforces the episode read cap.  Simulate those
    # consequences over the frozen segment order rather than independently
    # choosing a convenient later pair for each reference.
    pairwise_valid_count = sum(bool(item["pairwise_support_valid"]) for item in segments)
    by_episode: dict[str, list[dict[str, Any]]] = {}
    for item in segments:
        by_episode.setdefault(str(item["episode_id"]), []).append(item)
    for episode_segments in by_episode.values():
        episode_segments.sort(key=lambda item: int(item["second_failure_source_step"]))
        delivered: list[dict[str, Any]] = []
        read_steps: list[int] = []
        for item in episode_segments:
            if not item["pairwise_support_valid"]:
                continue
            first = int(item["first_failure_source_step"])
            second = int(item["second_failure_source_step"])
            chronological_supports = [
                support for support in item["prior_support_candidates"]
                if support["no_reset_between_supports"]
            ]
            if len(chronological_supports) >= 2:
                item["actual_earliest_maturity_step"] = int(
                    chronological_supports[1]["first_source_step"]
                )
                item["invalid_reason"] = "earlier_pair_matured_before_frozen_second_step"
                continue
            item["actual_earliest_maturity_step"] = second
            if any(
                prior["action_family"] == item["action_family"]
                and _equivalent(prior["screen"], item["second_screen_full"])
                for prior in delivered
            ):
                item["invalid_reason"] = "one_shot_equivalent_failure_already_delivered"
                continue
            read_step = second + 1
            if len(read_steps) >= 5:
                item["invalid_reason"] = "episode_read_cap_suppressed"
                continue
            if read_steps and read_step - read_steps[-1] < 4:
                item["invalid_reason"] = "global_cooldown_suppressed"
                continue
            item["independently_valid_for_a12"] = True
            item["invalid_reason"] = None
            read_steps.append(read_step)
            delivered.append(
                {
                    "action_family": item["action_family"],
                    "screen": item["second_screen_full"],
                }
            )
    for item in segments:
        item.pop("second_screen_full", None)
    valid_count = sum(bool(item["independently_valid_for_a12"]) for item in segments)
    errors: list[str] = []
    if len(segments) != 23:
        errors.append("frozen_a6_reference_segment_count_not_23")
    if valid_count != 23:
        errors.append("frozen_a6_reference_segments_not_all_independently_valid")
    if valid_count < 20:
        errors.append("a12_theoretical_max_qualifiable_segments_below_20")
    if materialized_verification["status"] != "pass":
        errors.append("materialized_trace_verification_failed")
    return {
        "schema": "a12_reference_segments_v1",
        "status": "pass" if not errors else "protocol_invalid",
        "verdict": "A12_PROTOCOL_INVALID" if errors else "A12_REFERENCE_FREEZE_PASS",
        "generation_calls": 0,
        "independent_builder": True,
        "imports_a12_production_memory": False,
        "source": {
            "frozen_a10_report_sha256": _sha(FROZEN_A10_REPORT),
            "materialized_manifest_sha256": _sha(MATERIALIZED_MANIFEST),
            "builder_source_sha256": _sha(Path(__file__).resolve()),
            "materialized_trace_root_name": trace_root.name,
            "materialized_trace_verification": materialized_verification,
        },
        "parameters": {
            "changed_fraction_threshold": 0.001,
            "first_support_max_gap_actions": 12,
            "screen_dl_threshold": 0.06,
            "screen_de_threshold": 0.12,
            "screen_dv_threshold": 0.055,
            "material_progress_or_context_loss_resets_all_active_evidence": True,
        },
        "frozen_reference_segment_count": len(segments),
        "pairwise_support_valid_segment_count": pairwise_valid_count,
        "independently_valid_segment_count": valid_count,
        "theoretical_max_after_chronology_cooldown_one_shot_and_cap": valid_count,
        "required_valid_segment_count": 23,
        "required_qualifiable_segment_count": 20,
        "segments": segments,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build(args.trace_root.resolve())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({key: value for key, value in report.items() if key != "segments"}, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
