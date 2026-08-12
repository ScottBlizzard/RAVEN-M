"""A12 Minimal Action-Divergence Memory (MADM).

The mechanism is deliberately small: it remembers only whether the same
canonical action family produced no material visible progress twice on one
model-visible RGB screen.  It never calls a model, interprets a query, reads
hidden UI state, changes an action, or terminates an episode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
import unicodedata
from typing import Any

import numpy as np


MECHANISM_ID = "a12_minimal_action_divergence_memory_v1"
EXPERIMENT_ID = "A12_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
TRIGGER_KIND = "REPEATED_NO_PROGRESS_ACTION"

MAX_FAILURE_RECORDS = 8
MAX_DELIVERED_FAILURES = 5
MAX_READ_EVENTS = 5
MAX_POST_READ_WATCHES = 5
MAX_DESCRIPTOR_CACHE = 2
MAX_NONEMPTY_READS_PER_EPISODE = 5
GLOBAL_COOLDOWN_EXECUTED_ACTIONS = 4
FIRST_SUPPORT_MAX_GAP_ACTIONS = 12
MAX_VISIBLE_CHARS_PER_READ = 240
MAX_UTF8_BYTES_PER_READ = 480
MAX_ACTION_LABEL_CHARS = 48
MAX_AUDIT_JSON_BYTES = 131072


class A12VisibleInputError(RuntimeError):
    """Raised when the model-visible RGB value violates the frozen contract."""


class A12IntegrityError(RuntimeError):
    """Raised when controller ordering or a canonical action is invalid."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _json_sha256(value: Any) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_round_floats(item) for item in value)
    return value


def extract_visible_rgb_only(snapshot: dict[str, Any]) -> np.ndarray:
    pixels = np.asarray(snapshot.get("pixels"))
    if (
        pixels.ndim != 3
        or pixels.shape[0] < 25
        or pixels.shape[1] < 8
        or pixels.shape[2] < 3
        or not np.issubdtype(pixels.dtype, np.integer)
    ):
        raise A12VisibleInputError(
            "A12 requires H>=25, W>=8, C>=3 integer model-visible RGB"
        )
    if pixels.size and (int(pixels.min()) < 0 or int(pixels.max()) > 255):
        raise A12VisibleInputError("A12 RGB values must be in [0,255]")
    return np.ascontiguousarray(pixels[:, :, :3])


@dataclass(frozen=True)
class VisualDescriptor:
    exact_sha256: str
    descriptor_sha256: str
    luma_q: tuple[int, ...]
    edge_bits_hex: str
    crop_shape: tuple[int, int, int]


def describe_visual_state(pixels: np.ndarray) -> VisualDescriptor:
    rgb = extract_visible_rgb_only({"pixels": pixels})
    height = rgb.shape[0]
    top = int(math.floor(0.04 * height))
    bottom = int(math.ceil(0.96 * height))
    crop = np.ascontiguousarray(rgb[top:bottom, :, :3])
    exact_payload = (
        f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    )
    exact_sha = sha256(exact_payload).hexdigest()

    def bounds(size: int, count: int, index: int) -> tuple[int, int]:
        start = int(math.floor(index * size / count))
        stop = int(math.ceil((index + 1) * size / count))
        start = min(size - 1, max(0, start))
        stop = min(size, max(start + 1, stop))
        return start, stop

    # uint64 integral image makes the integer cell mean deterministic and safe.
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

    luma_q: list[int] = []
    for row in range(9):
        r0, r1 = bounds(crop.shape[0], 9, row)
        for column in range(16):
            c0, c1 = bounds(crop.shape[1], 16, column)
            mean = rectangle_sum(r0, r1, c0, c1) // ((r1 - r0) * (c1 - c0))
            luminance = (
                77 * int(mean[0]) + 150 * int(mean[1]) + 29 * int(mean[2])
            ) // 256
            luma_q.append(min(15, max(0, luminance // 16)))

    matrix = np.asarray(luma_q, dtype=np.uint8).reshape(9, 16)
    edge_values = np.concatenate(
        (
            (matrix[:, 1:] > matrix[:, :-1]).ravel(),
            (matrix[1:, :] > matrix[:-1, :]).ravel(),
        )
    ).astype(np.uint8)
    edge_bytes = np.packbits(edge_values, bitorder="big").tobytes()
    return VisualDescriptor(
        exact_sha256=exact_sha,
        descriptor_sha256=sha256(bytes(luma_q) + edge_bytes).hexdigest(),
        luma_q=tuple(luma_q),
        edge_bits_hex=edge_bytes.hex(),
        crop_shape=tuple(int(value) for value in crop.shape),
    )


def visual_distance(
    left: VisualDescriptor, right: VisualDescriptor
) -> tuple[float, float, float]:
    if left.exact_sha256 == right.exact_sha256:
        return 0.0, 0.0, 0.0
    luma_left = np.asarray(left.luma_q, dtype=np.int16)
    luma_right = np.asarray(right.luma_q, dtype=np.int16)
    dl = float(np.abs(luma_left - luma_right).sum()) / (144.0 * 15.0)
    edges_left = np.unpackbits(
        np.frombuffer(bytes.fromhex(left.edge_bits_hex), dtype=np.uint8),
        bitorder="big",
    )[:263]
    edges_right = np.unpackbits(
        np.frombuffer(bytes.fromhex(right.edge_bits_hex), dtype=np.uint8),
        bitorder="big",
    )[:263]
    de = float(np.count_nonzero(edges_left != edges_right)) / 263.0
    return dl, de, 0.7 * dl + 0.3 * de


def compare_screens(
    current: VisualDescriptor, representative: VisualDescriptor
) -> tuple[str, float]:
    if current.exact_sha256 == representative.exact_sha256:
        return "EXACT", 0.0
    dl, de, dv = visual_distance(current, representative)
    if dl <= 0.06 and de <= 0.12 and dv <= 0.055:
        return "NEAR", dv
    return "NONE", dv


def screen_equivalent(left: VisualDescriptor, right: VisualDescriptor) -> bool:
    return compare_screens(left, right)[0] != "NONE"


def changed_pixel_fraction(before: np.ndarray, after: np.ndarray) -> float:
    left = extract_visible_rgb_only({"pixels": before})
    right = extract_visible_rgb_only({"pixels": after})
    if left.shape != right.shape:
        return 1.0
    delta = np.max(
        np.abs(left.astype(np.int16) - right.astype(np.int16)), axis=2
    )
    return float(np.count_nonzero(delta > 5)) / float(delta.size)


def _finite_coordinate(value: Any) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise A12IntegrityError("canonical coordinate must be finite")
    coordinate = float(value)
    if not 0.0 <= coordinate <= 1.0:
        raise A12IntegrityError("canonical coordinate must be in [0,1]")
    return coordinate


def _duration_bucket(duration_ms: Any) -> str:
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)):
        raise A12IntegrityError("duration_ms must be finite numeric")
    duration = float(duration_ms)
    if not math.isfinite(duration) or duration < 0:
        raise A12IntegrityError("duration_ms must be finite and non-negative")
    return "short" if duration < 700 else "medium" if duration <= 1500 else "long"


def validate_canonical_action(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        raise A12IntegrityError("canonical action must be a mapping")
    kind = str(action.get("type") or "")
    allowed = {
        "tap", "long_press", "swipe", "type_text", "wait", "press_back",
        "press_home", "press_enter", "press_recents", "answer",
    }
    if kind not in allowed:
        raise A12IntegrityError(f"unsupported canonical action: {kind!r}")
    return dict(action)


def canonical_action_family(action: dict[str, Any]) -> tuple[Any, ...]:
    action = validate_canonical_action(action)
    kind = str(action["type"])
    if kind in {"tap", "long_press"}:
        x = _finite_coordinate(action.get("x"))
        y = _finite_coordinate(action.get("y"))
        family: tuple[Any, ...] = (
            kind, min(11, int(math.floor(12 * x))),
            min(23, int(math.floor(24 * y))),
        )
        if kind == "long_press":
            family += (_duration_bucket(action.get("duration_ms", 0)),)
        return family
    if kind == "swipe":
        x = _finite_coordinate(action.get("x"))
        y = _finite_coordinate(action.get("y"))
        x2 = _finite_coordinate(action.get("x2"))
        y2 = _finite_coordinate(action.get("y2"))
        dx, dy = x2 - x, y2 - y
        if abs(dx) >= abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"
        length = math.hypot(dx, dy)
        length_bucket = (
            "short" if length < 0.25 else "medium" if length < 0.55 else "long"
        )
        return (
            "swipe", direction, length_bucket,
            min(2, int(math.floor(3 * x))),
            min(3, int(math.floor(4 * y))),
        )
    if kind == "type_text":
        text = unicodedata.normalize("NFKC", str(action.get("text") or ""))
        length = len(text)
        length_bucket = (
            "1-8" if length <= 8 else "9-32" if length <= 32
            else "33-96" if length <= 96 else "97+"
        )
        return (
            "type_text", sha256(text.encode("utf-8")).hexdigest(),
            length_bucket, bool(action.get("clear_text")),
        )
    if kind == "wait":
        return ("wait", _duration_bucket(action.get("duration_ms", 0)))
    if kind in {"press_back", "press_home", "press_enter", "press_recents"}:
        return (kind,)
    text = unicodedata.normalize("NFKC", str(action.get("text") or ""))
    return ("answer", sha256(text.encode("utf-8")).hexdigest())


def render_action_label(family: tuple[Any, ...]) -> str:
    kind = str(family[0])
    if kind == "tap":
        label = f"tap cell {int(family[1]) + 1}/12,{int(family[2]) + 1}/24"
    elif kind == "long_press":
        label = (
            f"long-press cell {int(family[1]) + 1}/12,"
            f"{int(family[2]) + 1}/24 ({family[3]})"
        )
    elif kind == "swipe":
        label = f"swipe {family[1]} ({family[2]})"
    elif kind == "type_text":
        label = "enter the same text"
    elif kind == "press_back":
        label = "press Back"
    elif kind == "press_home":
        label = "press Home"
    elif kind == "press_enter":
        label = "press Enter"
    elif kind == "press_recents":
        label = "press Recents"
    elif kind == "wait":
        label = f"wait ({family[1]})"
    elif kind == "answer":
        label = "submit the same answer"
    else:
        raise A12IntegrityError(f"unknown canonical family: {kind!r}")
    if len(label) > MAX_ACTION_LABEL_CHARS:
        raise A12IntegrityError("action label exceeds frozen maximum")
    return label


def render_memory(action_label: str) -> str:
    rendered = (
        f"A12 memory: On this screen, {action_label} produced no material "
        "visible change twice. Try a different action family or target. "
        "Retry is allowed; nothing is blocked."
    )
    if not rendered:
        raise A12IntegrityError("empty renderer output")
    if len(rendered) > MAX_VISIBLE_CHARS_PER_READ:
        raise A12IntegrityError("rendered char cap exceeded")
    if len(rendered.encode("utf-8")) > MAX_UTF8_BYTES_PER_READ:
        raise A12IntegrityError("rendered byte cap exceeded")
    return rendered


@dataclass
class ActiveScreenContext:
    context_id: str
    representative_descriptor: VisualDescriptor
    created_read_step: int
    last_matched_read_step: int
    last_matched_source_step: int
    context_epoch: int


@dataclass
class ActionFailureRecord:
    record_id: str
    context_id: str
    action_family: tuple[Any, ...]
    action_key_sha256: str
    action_label: str
    state: str
    support_count: int
    first_support_step: int
    last_support_step: int
    second_support_step: int | None
    first_before_exact_sha256: str
    first_after_exact_sha256: str
    second_before_exact_sha256: str | None
    second_after_exact_sha256: str | None
    first_changed_fraction: float
    second_changed_fraction: float | None
    first_summary_sha256: str
    second_summary_sha256: str | None
    maturity_step: int | None
    eligible_read_step: int | None
    expiry_read_step: int | None
    evidence_signature: str | None
    suppression_reason: str | None


@dataclass
class DeliveredFailureSignature:
    delivered_id: str
    representative_descriptor: VisualDescriptor
    action_family: tuple[Any, ...]
    action_key_sha256: str
    evidence_signature: str
    delivered_read_step: int


@dataclass
class ReadEvent:
    read_id: str
    read_step: int
    candidate_record_id: str
    candidate_state_before_read: str
    maturity_step: int
    eligible_read_step: int
    screen_match_kind: str
    visual_distance: float
    support_count: int
    support_steps: list[int]
    action_family: tuple[Any, ...]
    action_key_sha256: str
    action_label: str
    evidence_signature: str
    all_hard_gates_passed: bool
    actual_nonempty: bool
    exact_injected_text: str
    rendered_sha256: str
    rendered_chars: int
    rendered_utf8_bytes: int
    rendered_tokens: int | None = None


@dataclass
class PostReadWatch:
    watch_id: str
    read_id: str
    read_step: int
    failed_screen_descriptor: VisualDescriptor
    failed_action_family: tuple[Any, ...]
    next_action_step: int | None = None
    next_action_family: tuple[Any, ...] | None = None
    next_action_diverged: bool | None = None
    material_progress_within_2: bool = False
    same_failed_action_within_4: bool = False
    context_loss_within_2: bool = False
    closed: bool = False
    close_step: int | None = None


def _descriptor_audit(descriptor: VisualDescriptor) -> dict[str, Any]:
    return {
        "exact_sha256": descriptor.exact_sha256,
        "descriptor_sha256": descriptor.descriptor_sha256,
        "luma_q_packed_hex": "".join(format(value, "x") for value in descriptor.luma_q),
        "edge_bits_hex": descriptor.edge_bits_hex,
        "crop_shape": descriptor.crop_shape,
    }


class MinimalActionDivergenceMemory:
    """The complete bounded A12 MADM episode state machine."""

    mechanism_id = MECHANISM_ID

    def __init__(self, *, experiment_id: str = EXPERIMENT_ID) -> None:
        self.experiment_id = str(experiment_id)
        self.reset()

    def reset(self) -> None:
        self.goal_sha256 = ""
        self.active_context: ActiveScreenContext | None = None
        self.failure_records: dict[str, ActionFailureRecord] = {}
        self.delivered_failures: list[DeliveredFailureSignature] = []
        self.read_events: list[ReadEvent] = []
        self.post_read_watches: list[PostReadWatch] = []
        self.descriptor_cache: list[tuple[str, VisualDescriptor]] = []
        self.context_epoch = 0
        self.last_observed_step = -1
        self.read_count = 0
        self.nonempty_read_count = 0
        self.last_nonempty_read_step: int | None = None
        self.max_observed_failure_record_count = 0
        self.max_rendered_chars = 0
        self.max_rendered_utf8_bytes = 0
        self.max_rendered_tokens = 0
        self.counters = {
            "support_created_count": 0,
            "candidate_matured_count": 0,
            "eligibility_check_count": 0,
            "eligible_candidate_count": 0,
            "nonempty_read_count": 0,
            "context_loss_count": 0,
            "material_progress_reset_count": 0,
            "first_support_expiry_count": 0,
            "candidate_suppressed_count": 0,
            "candidate_expired_count": 0,
            "one_shot_suppressed_count": 0,
            "cooldown_suppressed_count": 0,
            "cap_suppressed_count": 0,
            "failure_record_eviction_count": 0,
        }

    def _describe(self, pixels: np.ndarray) -> VisualDescriptor:
        rgb = extract_visible_rgb_only({"pixels": pixels})
        height = rgb.shape[0]
        crop = np.ascontiguousarray(
            rgb[
                int(math.floor(0.04 * height)):int(math.ceil(0.96 * height)),
                :, :3,
            ]
        )
        cache_key = sha256(
            f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
        ).hexdigest()
        for existing_key, descriptor in reversed(self.descriptor_cache):
            if existing_key == cache_key:
                return descriptor
        descriptor = describe_visual_state(rgb)
        self.descriptor_cache.append((cache_key, descriptor))
        self.descriptor_cache = self.descriptor_cache[-MAX_DESCRIPTOR_CACHE:]
        return descriptor

    def _bind_new_context(
        self, descriptor: VisualDescriptor, read_step: int
    ) -> ActiveScreenContext:
        self.context_epoch += 1
        context_id = _json_sha256(
            {
                "context_epoch": self.context_epoch,
                "descriptor_sha256": descriptor.descriptor_sha256,
                "exact_sha256": descriptor.exact_sha256,
            }
        )
        self.active_context = ActiveScreenContext(
            context_id=context_id,
            representative_descriptor=descriptor,
            created_read_step=read_step,
            last_matched_read_step=read_step,
            last_matched_source_step=self.last_observed_step,
            context_epoch=self.context_epoch,
        )
        return self.active_context

    def _invalidate_active_context(self, *, reason: str) -> list[str]:
        invalidated = [record.record_id for record in self.failure_records.values()]
        for record in self.failure_records.values():
            if record.state == "READY":
                self.counters["candidate_expired_count"] += 1
            record.state = "EXPIRED"
            record.suppression_reason = reason
        self.failure_records = {}
        self.active_context = None
        self.counters["context_loss_count"] += 1
        return invalidated

    def _delivered_equivalent(
        self, *, descriptor: VisualDescriptor, action_family: tuple[Any, ...]
    ) -> bool:
        return any(
            delivered.action_family == action_family
            and screen_equivalent(
                delivered.representative_descriptor, descriptor
            )
            for delivered in self.delivered_failures
        )

    def _expire_old_first_supports(self, current_source_step: int) -> None:
        for record in self.failure_records.values():
            if (
                record.state == "SEEN_ONCE"
                and current_source_step - record.first_support_step
                > FIRST_SUPPORT_MAX_GAP_ACTIONS
            ):
                record.state = "EXPIRED"
                record.suppression_reason = "first_support_expired"
                self.counters["first_support_expiry_count"] += 1

    def _enforce_failure_record_capacity(self) -> None:
        while len(self.failure_records) > MAX_FAILURE_RECORDS:
            ready = [r for r in self.failure_records.values() if r.state == "READY"]
            if len(ready) > 1:
                raise A12IntegrityError("more than one READY record")
            candidates = [
                (key, record) for key, record in self.failure_records.items()
                if record.state != "READY"
            ]
            if not candidates:
                raise A12IntegrityError("failure capacity contains only READY records")
            state_priority = {"EXPIRED": 0, "SUPPRESSED": 1, "SEEN_ONCE": 2}
            victim_key, victim = min(
                candidates,
                key=lambda item: (
                    state_priority.get(item[1].state, 3),
                    item[1].last_support_step,
                    item[1].action_key_sha256,
                ),
            )
            victim.state = "EXPIRED"
            del self.failure_records[victim_key]
            self.counters["failure_record_eviction_count"] += 1
        self.max_observed_failure_record_count = max(
            self.max_observed_failure_record_count, len(self.failure_records)
        )

    @staticmethod
    def _first_support_record(
        *, context: ActiveScreenContext, source_step: int,
        action_family: tuple[Any, ...], action_key: str, action_label: str,
        before_desc: VisualDescriptor, after_desc: VisualDescriptor,
        changed_fraction: float, summary_sha: str,
    ) -> ActionFailureRecord:
        return ActionFailureRecord(
            record_id=f"a12f_{source_step}_{action_key[:12]}",
            context_id=context.context_id,
            action_family=action_family,
            action_key_sha256=action_key,
            action_label=action_label,
            state="SEEN_ONCE",
            support_count=1,
            first_support_step=source_step,
            last_support_step=source_step,
            second_support_step=None,
            first_before_exact_sha256=before_desc.exact_sha256,
            first_after_exact_sha256=after_desc.exact_sha256,
            second_before_exact_sha256=None,
            second_after_exact_sha256=None,
            first_changed_fraction=changed_fraction,
            second_changed_fraction=None,
            first_summary_sha256=summary_sha,
            second_summary_sha256=None,
            maturity_step=None,
            eligible_read_step=None,
            expiry_read_step=None,
            evidence_signature=None,
            suppression_reason=None,
        )

    @staticmethod
    def _gate_failure_reason(gate: dict[str, bool]) -> str:
        ordered = (
            "state_ready", "exact_immediate_read", "not_expired",
            "screen_match", "not_delivered", "episode_cap", "cooldown",
        )
        return next((f"gate_{name}_failed" for name in ordered if not gate[name]), "unknown_gate_failure")

    def _read_audit(
        self, *, read_step: int, reason: str,
        candidate: ActionFailureRecord | None = None,
        eligible: bool = False, actual_nonempty: bool = False,
        hard_gates: dict[str, bool] | None = None,
        screen_match_kind: str | None = None,
        visual_distance_value: float | None = None,
        exact_injected_text: str = "",
    ) -> dict[str, Any]:
        return _round_floats(
            {
                "mechanism_id": MECHANISM_ID,
                "trigger_kind": TRIGGER_KIND if candidate else None,
                "read_step": read_step,
                "candidate_present": candidate is not None,
                "candidate_record_id": candidate.record_id if candidate else None,
                "candidate_state": candidate.state if candidate else None,
                "mature": bool(candidate and candidate.support_count == 2),
                "eligible": eligible,
                "actual_nonempty": actual_nonempty,
                "nonempty": actual_nonempty,
                "reason": reason,
                "hard_gates": hard_gates or {},
                "screen_match_kind": screen_match_kind,
                "visual_distance": visual_distance_value,
                "maturity_step": candidate.maturity_step if candidate else None,
                "eligible_read_step": candidate.eligible_read_step if candidate else None,
                "expiry_read_step": candidate.expiry_read_step if candidate else None,
                "evidence_signature": candidate.evidence_signature if candidate else None,
                "exact_injected_text": exact_injected_text,
                "rendered_chars": len(exact_injected_text),
                "rendered_utf8_bytes": len(exact_injected_text.encode("utf-8")),
                "model_calls_added": 0,
                "guard_enabled": False,
                "action_override_count": 0,
                "forced_termination_count": 0,
            }
        )

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        read_step = self.read_count
        self.read_count += 1

        goal = str(context.get("goal") or "")
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if not self.goal_sha256:
            self.goal_sha256 = goal_sha
        elif goal_sha != self.goal_sha256:
            raise A12IntegrityError("goal changed within episode")

        pixels = extract_visible_rgb_only(dict(context.get("before") or {}))
        descriptor = self._describe(pixels)
        if self.active_context is None:
            self._bind_new_context(descriptor, read_step)
            return "", self._read_audit(
                read_step=read_step, reason="initial_context_bound"
            )

        match_kind, distance = compare_screens(
            descriptor, self.active_context.representative_descriptor
        )
        if match_kind == "NONE":
            self._invalidate_active_context(reason="screen_context_loss")
            self._bind_new_context(descriptor, read_step)
            return "", self._read_audit(
                read_step=read_step,
                reason="context_reset",
                screen_match_kind="NONE",
                visual_distance_value=distance,
            )

        self.active_context.last_matched_read_step = read_step
        self._expire_old_first_supports(self.last_observed_step)
        ready = [
            record for record in self.failure_records.values()
            if record.state == "READY"
        ]
        if len(ready) > 1:
            raise A12IntegrityError("more than one READY record")
        if not ready:
            return "", self._read_audit(
                read_step=read_step,
                reason="no_ready_candidate",
                screen_match_kind=match_kind,
                visual_distance_value=distance,
            )

        candidate = ready[0]
        self.counters["eligibility_check_count"] += 1
        gate = {
            "state_ready": candidate.state == "READY",
            "exact_immediate_read": read_step == candidate.eligible_read_step,
            "not_expired": bool(
                candidate.expiry_read_step is not None
                and read_step <= candidate.expiry_read_step
            ),
            "screen_match": match_kind in {"EXACT", "NEAR"},
            "not_delivered": not self._delivered_equivalent(
                descriptor=self.active_context.representative_descriptor,
                action_family=candidate.action_family,
            ),
            "episode_cap": self.nonempty_read_count < MAX_NONEMPTY_READS_PER_EPISODE,
            "cooldown": (
                self.last_nonempty_read_step is None
                or read_step - self.last_nonempty_read_step
                >= GLOBAL_COOLDOWN_EXECUTED_ACTIONS
            ),
        }
        eligible = all(gate.values())
        if not eligible:
            reason = self._gate_failure_reason(gate)
            candidate.state = "SUPPRESSED"
            candidate.suppression_reason = reason
            self.counters["candidate_suppressed_count"] += 1
            if not gate["cooldown"]:
                self.counters["cooldown_suppressed_count"] += 1
            if not gate["episode_cap"]:
                self.counters["cap_suppressed_count"] += 1
            if not gate["not_delivered"]:
                self.counters["one_shot_suppressed_count"] += 1
            return "", self._read_audit(
                read_step=read_step,
                reason=reason,
                candidate=candidate,
                eligible=False,
                hard_gates=gate,
                screen_match_kind=match_kind,
                visual_distance_value=distance,
            )

        state_before = candidate.state
        rendered = render_memory(candidate.action_label)
        if not rendered:
            raise A12IntegrityError("empty renderer output")
        candidate.state = "DELIVERED"
        if len(self.delivered_failures) >= MAX_DELIVERED_FAILURES:
            raise A12IntegrityError("delivered failure capacity exceeded")
        if candidate.evidence_signature is None:
            raise A12IntegrityError("READY candidate lacks evidence signature")
        delivered = DeliveredFailureSignature(
            delivered_id=f"a12d_{read_step}_{candidate.evidence_signature[:12]}",
            representative_descriptor=self.active_context.representative_descriptor,
            action_family=candidate.action_family,
            action_key_sha256=candidate.action_key_sha256,
            evidence_signature=candidate.evidence_signature,
            delivered_read_step=read_step,
        )
        self.delivered_failures.append(delivered)
        self.nonempty_read_count += 1
        self.last_nonempty_read_step = read_step
        self.counters["eligible_candidate_count"] += 1
        self.counters["nonempty_read_count"] += 1

        if len(self.read_events) >= MAX_READ_EVENTS:
            raise A12IntegrityError("read event capacity exceeded")
        read_id = f"a12r_{read_step}_{candidate.evidence_signature[:12]}"
        event = ReadEvent(
            read_id=read_id,
            read_step=read_step,
            candidate_record_id=candidate.record_id,
            candidate_state_before_read=state_before,
            maturity_step=int(candidate.maturity_step),
            eligible_read_step=int(candidate.eligible_read_step),
            screen_match_kind=match_kind,
            visual_distance=distance,
            support_count=candidate.support_count,
            support_steps=[
                candidate.first_support_step, int(candidate.second_support_step)
            ],
            action_family=candidate.action_family,
            action_key_sha256=candidate.action_key_sha256,
            action_label=candidate.action_label,
            evidence_signature=candidate.evidence_signature,
            all_hard_gates_passed=True,
            actual_nonempty=True,
            exact_injected_text=rendered,
            rendered_sha256=sha256(rendered.encode("utf-8")).hexdigest(),
            rendered_chars=len(rendered),
            rendered_utf8_bytes=len(rendered.encode("utf-8")),
        )
        self.read_events.append(event)
        if len(self.post_read_watches) >= MAX_POST_READ_WATCHES:
            raise A12IntegrityError("post-read watch capacity exceeded")
        self.post_read_watches.append(
            PostReadWatch(
                watch_id=f"a12w_{read_step}_{candidate.evidence_signature[:12]}",
                read_id=read_id,
                read_step=read_step,
                failed_screen_descriptor=self.active_context.representative_descriptor,
                failed_action_family=candidate.action_family,
            )
        )
        del self.failure_records[candidate.action_key_sha256]
        self.max_rendered_chars = max(self.max_rendered_chars, len(rendered))
        self.max_rendered_utf8_bytes = max(
            self.max_rendered_utf8_bytes, len(rendered.encode("utf-8"))
        )
        return rendered, self._read_audit(
            read_step=read_step,
            reason="delivered",
            candidate=candidate,
            eligible=True,
            actual_nonempty=True,
            hard_gates=gate,
            screen_match_kind=match_kind,
            visual_distance_value=distance,
            exact_injected_text=rendered,
        )

    def _update_post_read_watches(
        self, *, source_step: int, action_family: tuple[Any, ...],
        before_descriptor: VisualDescriptor, after_descriptor: VisualDescriptor,
        no_progress: bool,
    ) -> None:
        for watch in self.post_read_watches:
            if watch.closed:
                continue
            offset = source_step - watch.read_step
            if offset < 0:
                continue
            if watch.next_action_step is None:
                watch.next_action_step = source_step
                watch.next_action_family = action_family
                watch.next_action_diverged = (
                    action_family != watch.failed_action_family
                )
            before_match = screen_equivalent(
                before_descriptor, watch.failed_screen_descriptor
            )
            after_match = screen_equivalent(
                after_descriptor, watch.failed_screen_descriptor
            )
            if offset <= 1 and not no_progress:
                watch.material_progress_within_2 = True
            if offset <= 1 and (not before_match or not after_match):
                watch.context_loss_within_2 = True
            if (
                offset <= 3
                and before_match
                and action_family == watch.failed_action_family
                and no_progress
            ):
                watch.same_failed_action_within_4 = True
            if offset >= 3:
                watch.closed = True
                watch.close_step = source_step

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        source_step = int(kwargs["source_step"])
        if source_step != self.last_observed_step + 1:
            raise A12IntegrityError("non-monotonic source_step")
        if any(record.state == "READY" for record in self.failure_records.values()):
            raise A12IntegrityError("READY record survived its immediate read window")

        before_pixels = extract_visible_rgb_only(dict(kwargs.get("before") or {}))
        after_pixels = extract_visible_rgb_only(dict(kwargs.get("after") or {}))
        action = validate_canonical_action(
            dict(kwargs.get("canonical_action") or {})
        )
        action_family = canonical_action_family(action)
        action_key = _json_sha256(action_family)
        action_label = render_action_label(action_family)
        summary_sha = sha256(
            str(kwargs.get("action_summary") or "").encode("utf-8")
        ).hexdigest()
        before_desc = self._describe(before_pixels)
        after_desc = self._describe(after_pixels)

        if self.active_context is None:
            self._bind_new_context(before_desc, max(0, self.read_count - 1))
        elif not screen_equivalent(
            before_desc, self.active_context.representative_descriptor
        ):
            self._invalidate_active_context(reason="before_context_loss")
            self._bind_new_context(before_desc, max(0, self.read_count - 1))

        changed_fraction = changed_pixel_fraction(before_pixels, after_pixels)
        same_screen_after = screen_equivalent(before_desc, after_desc)
        no_progress = same_screen_after and changed_fraction <= 0.001
        self._update_post_read_watches(
            source_step=source_step,
            action_family=action_family,
            before_descriptor=before_desc,
            after_descriptor=after_desc,
            no_progress=no_progress,
        )

        common = {
            "source_step": source_step,
            "action_family": action_family,
            "action_key_sha256": action_key,
            "changed_pixel_fraction": changed_fraction,
            "no_material_progress": no_progress,
            "trigger_kind": TRIGGER_KIND,
            "model_calls_added": 0,
            "guard_enabled": False,
            "action_override_count": 0,
            "forced_termination_count": 0,
        }
        if not no_progress:
            invalidated = self._invalidate_active_context(
                reason="material_visible_progress_or_context_change"
            )
            self.counters["material_progress_reset_count"] += 1
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": bool(invalidated),
                    "context_invalidated": True,
                    "invalidated_record_ids": invalidated,
                    "support_created": False,
                    "candidate_matured": False,
                    "candidate_id": None,
                }
            )

        if self.active_context is None:
            raise A12IntegrityError("no active context after no-progress action")
        self.active_context.last_matched_source_step = source_step
        if self._delivered_equivalent(
            descriptor=self.active_context.representative_descriptor,
            action_family=action_family,
        ):
            self.counters["one_shot_suppressed_count"] += 1
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": False,
                    "context_invalidated": False,
                    "support_created": False,
                    "candidate_matured": False,
                    "candidate_id": None,
                    "reason": "already_delivered_for_equivalent_screen_action",
                }
            )

        record = self.failure_records.get(action_key)
        if record is None:
            record = self._first_support_record(
                context=self.active_context,
                source_step=source_step,
                action_family=action_family,
                action_key=action_key,
                action_label=action_label,
                before_desc=before_desc,
                after_desc=after_desc,
                changed_fraction=changed_fraction,
                summary_sha=summary_sha,
            )
            self.failure_records[action_key] = record
            self.counters["support_created_count"] += 1
            self._enforce_failure_record_capacity()
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": True,
                    "context_invalidated": False,
                    "support_created": True,
                    "support_count": 1,
                    "candidate_matured": False,
                    "candidate_id": None,
                }
            )

        if (
            record.state == "EXPIRED"
            and record.suppression_reason == "first_support_expired"
        ):
            replacement = self._first_support_record(
                context=self.active_context,
                source_step=source_step,
                action_family=action_family,
                action_key=action_key,
                action_label=action_label,
                before_desc=before_desc,
                after_desc=after_desc,
                changed_fraction=changed_fraction,
                summary_sha=summary_sha,
            )
            self.failure_records[action_key] = replacement
            self.counters["support_created_count"] += 1
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": True,
                    "context_invalidated": False,
                    "support_created": True,
                    "support_count": 1,
                    "candidate_matured": False,
                    "candidate_id": None,
                    "reason": "old_first_support_replaced",
                }
            )
        if record.state in {"SUPPRESSED", "EXPIRED"}:
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": False,
                    "context_invalidated": False,
                    "support_created": False,
                    "candidate_matured": False,
                    "candidate_id": None,
                    "reason": f"inert_record_{record.state.casefold()}",
                }
            )
        if record.state != "SEEN_ONCE":
            raise A12IntegrityError(f"unexpected failure state: {record.state}")
        if source_step - record.first_support_step > FIRST_SUPPORT_MAX_GAP_ACTIONS:
            record.state = "EXPIRED"
            self.counters["first_support_expiry_count"] += 1
            replacement = self._first_support_record(
                context=self.active_context,
                source_step=source_step,
                action_family=action_family,
                action_key=action_key,
                action_label=action_label,
                before_desc=before_desc,
                after_desc=after_desc,
                changed_fraction=changed_fraction,
                summary_sha=summary_sha,
            )
            self.failure_records[action_key] = replacement
            self.counters["support_created_count"] += 1
            self.last_observed_step = source_step
            return _round_floats(
                {
                    **common,
                    "written": True,
                    "context_invalidated": False,
                    "support_created": True,
                    "support_count": 1,
                    "candidate_matured": False,
                    "candidate_id": None,
                    "reason": "old_first_support_replaced",
                }
            )

        record.state = "READY"
        record.support_count = 2
        record.second_support_step = source_step
        record.last_support_step = source_step
        record.second_before_exact_sha256 = before_desc.exact_sha256
        record.second_after_exact_sha256 = after_desc.exact_sha256
        record.second_changed_fraction = changed_fraction
        record.second_summary_sha256 = summary_sha
        record.maturity_step = source_step
        record.eligible_read_step = source_step + 1
        record.expiry_read_step = source_step + 1
        record.evidence_signature = _json_sha256(
            {
                "mechanism_id": MECHANISM_ID,
                "context_descriptor_sha256": (
                    self.active_context.representative_descriptor.descriptor_sha256
                ),
                "action_family": action_family,
                "first_support_step": record.first_support_step,
                "second_support_step": source_step,
            }
        )
        self.counters["candidate_matured_count"] += 1
        self.last_observed_step = source_step
        return _round_floats(
            {
                **common,
                "written": True,
                "context_invalidated": False,
                "support_created": True,
                "support_count": 2,
                "candidate_matured": True,
                "candidate_id": record.record_id,
                "maturity_step": source_step,
                "eligible_read_step": source_step + 1,
                "expiry_read_step": source_step + 1,
                "evidence_signature": record.evidence_signature,
            }
        )

    def audit_record(self) -> dict[str, Any]:
        active_context: dict[str, Any] | None = None
        if self.active_context is not None:
            active_context = asdict(self.active_context)
            active_context["representative_descriptor"] = _descriptor_audit(
                self.active_context.representative_descriptor
            )

        delivered_failures: list[dict[str, Any]] = []
        for delivered in self.delivered_failures:
            item = asdict(delivered)
            item["representative_descriptor"] = _descriptor_audit(
                delivered.representative_descriptor
            )
            delivered_failures.append(item)

        watches: list[dict[str, Any]] = []
        for watch in self.post_read_watches:
            item = asdict(watch)
            item["failed_screen_descriptor"] = _descriptor_audit(
                watch.failed_screen_descriptor
            )
            watches.append(item)

        record: dict[str, Any] = {
            "schema": "a12_madm_audit_v1",
            "mechanism_id": MECHANISM_ID,
            "experiment_id": self.experiment_id,
            "causal_boundary": {
                "allowed_inputs": [
                    "goal", "before.pixels", "after.pixels",
                    "canonical_action", "action_summary", "source_step",
                ],
                "query_used_for_decision": False,
                "action_summary_used_for_decision": False,
                "model_calls_added": 0,
                "evaluator_used_for_decision": False,
                "hidden_ui_used_for_decision": False,
                "future_information_used": False,
                "task_name_used": False,
                "episode_id_used": False,
                "guard_enabled": False,
                "action_override_count": 0,
                "forced_termination_count": 0,
            },
            "parameters": {
                "trigger_kind": TRIGGER_KIND,
                "rgb_channel_delta": 5,
                "changed_fraction_threshold": 0.001,
                "screen_dl_threshold": 0.06,
                "screen_de_threshold": 0.12,
                "screen_dv_threshold": 0.055,
                "required_no_progress_supports": 2,
                "first_support_max_gap_actions": 12,
                "ready_read_window": 1,
                "global_cooldown_executed_actions": 4,
                "max_active_contexts": 1,
                "max_failure_records": 8,
                "max_delivered_failures": 5,
                "max_read_events": 5,
                "max_post_read_watches": 5,
                "max_descriptor_cache": 2,
                "max_nonempty_reads": 5,
                "max_visible_chars_per_read": 240,
                "max_utf8_bytes_per_read": 480,
                "max_rendered_tokens_per_read": 100,
                "max_rendered_tokens_per_episode": 500,
                "max_audit_json_bytes": 131072,
                "max_resident_state_delta_bytes": 2097152,
                "tap_grid": [12, 24],
                "swipe_start_grid": [3, 4],
                "duration_buckets_ms": [700, 1500],
                "swipe_length_buckets": [0.25, 0.55],
            },
            "goal": {"goal_sha256": self.goal_sha256},
            "active_context": active_context,
            "failure_records": [
                asdict(record) for record in self.failure_records.values()
            ],
            "delivered_failures": delivered_failures,
            "read_events": [asdict(event) for event in self.read_events],
            "post_read_watches": watches,
            "counters": dict(self.counters),
            "capacity": {
                "active_failure_record_count": len(self.failure_records),
                "max_observed_failure_record_count": (
                    self.max_observed_failure_record_count
                ),
                "delivered_failure_count": len(self.delivered_failures),
                "read_event_count": len(self.read_events),
                "post_read_watch_count": len(self.post_read_watches),
                "descriptor_cache_count": len(self.descriptor_cache),
                "max_rendered_chars": self.max_rendered_chars,
                "max_rendered_utf8_bytes": self.max_rendered_utf8_bytes,
                "max_rendered_tokens": self.max_rendered_tokens,
                "serialized_audit_bytes": 0,
                "resident_state_delta_bytes": None,
            },
        }
        record = _round_floats(record)
        previous = -1
        while record["capacity"]["serialized_audit_bytes"] != previous:
            previous = record["capacity"]["serialized_audit_bytes"]
            record["capacity"]["serialized_audit_bytes"] = len(
                json.dumps(
                    record, ensure_ascii=True, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            )
        if record["capacity"]["serialized_audit_bytes"] > MAX_AUDIT_JSON_BYTES:
            raise A12IntegrityError("serialized audit exceeds frozen capacity")
        return record

    def decision_state(self) -> dict[str, Any]:
        """Return the deterministic decision projection, excluding audit hashes."""
        return _round_floats(
            {
                "active_context": (
                    None
                    if self.active_context is None
                    else {
                        "representative": _descriptor_audit(
                            self.active_context.representative_descriptor
                        ),
                        "context_epoch": self.active_context.context_epoch,
                    }
                ),
                "failure_records": [
                    {
                        "action_family": record.action_family,
                        "state": record.state,
                        "support_count": record.support_count,
                        "first_support_step": record.first_support_step,
                        "second_support_step": record.second_support_step,
                        "eligible_read_step": record.eligible_read_step,
                        "expiry_read_step": record.expiry_read_step,
                        "evidence_signature": record.evidence_signature,
                    }
                    for record in self.failure_records.values()
                ],
                "delivered": [
                    {
                        "representative": _descriptor_audit(
                            delivered.representative_descriptor
                        ),
                        "action_family": delivered.action_family,
                    }
                    for delivered in self.delivered_failures
                ],
                "read_count": self.read_count,
                "nonempty_read_count": self.nonempty_read_count,
                "last_nonempty_read_step": self.last_nonempty_read_step,
            }
        )


# Explicit, readable alias used by some arm loaders.
MinimalActionDivergenceWorkingMemory = MinimalActionDivergenceMemory
