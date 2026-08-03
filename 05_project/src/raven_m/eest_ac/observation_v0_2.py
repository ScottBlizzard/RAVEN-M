"""Bounded dual-modal observation stabilization for EEST-AC v0.2."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time
from typing import Any, Callable


_IGNORED_PACKAGES = frozenset({"com.android.systemui"})
_A11Y_FIELDS = (
    "text",
    "content_description",
    "hint_text",
    "tooltip",
    "class_name",
    "package_name",
    "resource_name",
    "resource_id",
    "is_clickable",
    "is_editable",
    "is_checkable",
    "is_checked",
    "is_selected",
    "is_scrollable",
    "is_enabled",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _value(element: Any, field: str) -> Any:
    return element.get(field) if isinstance(element, dict) else getattr(element, field, None)


def _text(value: Any) -> str:
    return " ".join(str(value).split()) if value is not None else ""


@dataclass(frozen=True)
class ObservationFingerprint:
    pixel_sha256: str
    a11y_sha256: str | None
    a11y_available: bool
    state_signature: str
    visible_texts: tuple[str, ...]
    package_names: tuple[str, ...]
    element_count: int

    def record(self) -> dict[str, Any]:
        return {
            "pixel_sha256": self.pixel_sha256,
            "a11y_sha256": self.a11y_sha256,
            "a11y_available": self.a11y_available,
            "state_signature": self.state_signature,
            "visible_texts": list(self.visible_texts),
            "package_names": list(self.package_names),
            "element_count": self.element_count,
        }


@dataclass(frozen=True)
class CapturedObservation:
    state: Any
    fingerprint: ObservationFingerprint


@dataclass(frozen=True)
class StabilizedTransition:
    post_observations: tuple[CapturedObservation, ...]
    final_observation: CapturedObservation
    outcome: str
    no_effect_confirmed: bool
    post_observations_agree: bool

    def audit_record(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "no_effect_confirmed": self.no_effect_confirmed,
            "post_observations_agree": self.post_observations_agree,
            "sample_count": len(self.post_observations),
            "samples": [item.fingerprint.record() for item in self.post_observations],
        }


def fingerprint_state(state: Any) -> ObservationFingerprint:
    pixels = state.pixels
    pixel_sha = sha256(pixels.tobytes()).hexdigest()
    records: list[dict[str, Any]] = []
    texts: set[str] = set()
    packages: set[str] = set()
    for element in getattr(state, "ui_elements", ()) or ():
        if _value(element, "is_visible") is False:
            continue
        package = _text(_value(element, "package_name"))
        if package in _IGNORED_PACKAGES:
            continue
        record: dict[str, Any] = {}
        for field in _A11Y_FIELDS:
            item = _value(element, field)
            if item is None:
                continue
            if field in _A11Y_FIELDS[:8]:
                item = _text(item)
                if not item:
                    continue
            record[field] = item
        if record:
            records.append(record)
        if package:
            packages.add(package)
        for field in ("text", "content_description", "hint_text", "tooltip"):
            item = _text(_value(element, field))
            if item:
                texts.add(item)
    available = bool(records)
    a11y_sha = (
        sha256(
            _canonical_json(sorted(_canonical_json(item) for item in records)).encode(
                "utf-8"
            )
        ).hexdigest()
        if available
        else None
    )
    signature = sha256(
        _canonical_json({"pixel": pixel_sha, "a11y": a11y_sha}).encode("utf-8")
    ).hexdigest()
    return ObservationFingerprint(
        pixel_sha256=pixel_sha,
        a11y_sha256=a11y_sha,
        a11y_available=available,
        state_signature=signature,
        visible_texts=tuple(sorted(texts)),
        package_names=tuple(sorted(packages)),
        element_count=len(records),
    )


class ObservationStabilizer:
    """Observe twice after a delay; take one bounded tie-break sample."""

    def __init__(
        self,
        *,
        delay_seconds: float = 1.0,
        max_post_observations: int = 3,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if delay_seconds < 0 or max_post_observations not in {2, 3}:
            raise ValueError("Invalid bounded stabilization policy.")
        self.delay_seconds = delay_seconds
        self.max_post_observations = max_post_observations
        self.sleep_fn = sleep_fn

    @staticmethod
    def capture(state: Any) -> CapturedObservation:
        return CapturedObservation(state=state, fingerprint=fingerprint_state(state))

    def _get(self, env: Any) -> CapturedObservation:
        return self.capture(env.get_state(wait_to_stabilize=True))

    def observe_after(
        self,
        *,
        env: Any,
        before: CapturedObservation,
    ) -> StabilizedTransition:
        posts = [self._get(env)]
        self.sleep_fn(self.delay_seconds)
        posts.append(self._get(env))
        if (
            self.max_post_observations == 3
            and posts[0].fingerprint.state_signature
            != posts[1].fingerprint.state_signature
        ):
            self.sleep_fn(self.delay_seconds)
            posts.append(self._get(env))
        signatures = [item.fingerprint.state_signature for item in posts]
        post_agreement = len(set(signatures)) == 1
        before_fp = before.fingerprint
        no_effect = bool(
            before_fp.a11y_available
            and all(item.fingerprint.a11y_available for item in posts)
            and post_agreement
            and all(
                item.fingerprint.pixel_sha256 == before_fp.pixel_sha256
                and item.fingerprint.a11y_sha256 == before_fp.a11y_sha256
                for item in posts
            )
        )
        return StabilizedTransition(
            post_observations=tuple(posts),
            final_observation=posts[-1],
            outcome="no_effect_confirmed" if no_effect else "changed_or_uncertain",
            no_effect_confirmed=no_effect,
            post_observations_agree=post_agreement,
        )
