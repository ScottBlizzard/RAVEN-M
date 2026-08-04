"""Frozen terminal-window state-change policy for EEST-AC v0.2.2."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from raven_m.eest_ac.action_contract_v0_2_2 import load_contract
from raven_m.eest_ac.observation_v0_2 import CapturedObservation, StabilizedTransition


class QualificationObservationStabilizerV022:
    """Take the exact bounded post-action sequence frozen for qualification."""

    def __init__(self, *, sleep_fn: Any = time.sleep) -> None:
        policy = load_contract()["qualification_observation_contract"]
        self.delay_seconds = float(policy["delay_seconds"])
        self.post_observations = int(policy["maximum_post_observations"])
        self.sleep_fn = sleep_fn

    @staticmethod
    def capture(state: Any) -> CapturedObservation:
        from raven_m.eest_ac.observation_v0_2 import ObservationStabilizer

        return ObservationStabilizer.capture(state)

    def observe_after(self, *, env: Any, before: CapturedObservation) -> StabilizedTransition:
        posts = [self.capture(env.get_state(wait_to_stabilize=True))]
        for _ in range(1, self.post_observations):
            self.sleep_fn(self.delay_seconds)
            posts.append(self.capture(env.get_state(wait_to_stabilize=True)))
        signatures = [item.fingerprint.state_signature for item in posts]
        post_agreement = len(set(signatures)) == 1
        before_fp = before.fingerprint
        no_effect = bool(
            before_fp.a11y_available
            and all(item.fingerprint.a11y_available for item in posts[-2:])
            and len({item.fingerprint.state_signature for item in posts[-2:]}) == 1
            and posts[-1].fingerprint.state_signature == before_fp.state_signature
        )
        return StabilizedTransition(
            post_observations=tuple(posts),
            final_observation=posts[-1],
            outcome="no_effect_confirmed" if no_effect else "changed_or_uncertain",
            no_effect_confirmed=no_effect,
            post_observations_agree=post_agreement,
        )


@dataclass(frozen=True)
class StableChangeAuditV022:
    stable_change: bool
    terminal_window_size: int
    terminal_a11y_available: bool
    terminal_pixel_agreement: bool
    terminal_a11y_agreement: bool
    terminal_package_agreement: bool
    terminal_differs_from_pre: bool
    pre_state_signature: str
    terminal_state_signature: str | None
    terminal_samples: tuple[dict[str, Any], ...]
    reasons: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        return {
            "stable_change": self.stable_change,
            "terminal_window_size": self.terminal_window_size,
            "terminal_a11y_available": self.terminal_a11y_available,
            "terminal_pixel_agreement": self.terminal_pixel_agreement,
            "terminal_a11y_agreement": self.terminal_a11y_agreement,
            "terminal_package_agreement": self.terminal_package_agreement,
            "terminal_differs_from_pre": self.terminal_differs_from_pre,
            "pre_state_signature": self.pre_state_signature,
            "terminal_state_signature": self.terminal_state_signature,
            "terminal_samples": list(self.terminal_samples),
            "reasons": list(self.reasons),
        }


def audit_stable_change_v0_2_2(
    *,
    before: CapturedObservation,
    transition: StabilizedTransition,
) -> StableChangeAuditV022:
    policy = load_contract()["qualification_observation_contract"]
    window_size = int(policy["terminal_window_observations"])
    posts = transition.post_observations
    terminal = posts[-window_size:] if len(posts) >= window_size else posts
    fingerprints = [item.fingerprint for item in terminal]
    enough = len(fingerprints) == window_size
    a11y_available = enough and all(item.a11y_available for item in fingerprints)
    pixel_agreement = enough and len({item.pixel_sha256 for item in fingerprints}) == 1
    a11y_agreement = enough and len({item.a11y_sha256 for item in fingerprints}) == 1
    package_agreement = enough and len({item.package_names for item in fingerprints}) == 1
    final_signature = fingerprints[-1].state_signature if fingerprints else None
    differs = final_signature is not None and final_signature != before.fingerprint.state_signature
    checks = {
        "insufficient_terminal_samples": enough,
        "terminal_a11y_unavailable": a11y_available,
        "terminal_pixels_unsettled": pixel_agreement,
        "terminal_a11y_unsettled": a11y_agreement,
        "terminal_packages_unsettled": package_agreement,
        "terminal_did_not_change": differs,
    }
    reasons = tuple(name for name, passed in checks.items() if not passed)
    stable = all(checks.values())
    return StableChangeAuditV022(
        stable_change=stable,
        terminal_window_size=len(fingerprints),
        terminal_a11y_available=a11y_available,
        terminal_pixel_agreement=pixel_agreement,
        terminal_a11y_agreement=a11y_agreement,
        terminal_package_agreement=package_agreement,
        terminal_differs_from_pre=differs,
        pre_state_signature=before.fingerprint.state_signature,
        terminal_state_signature=final_signature,
        terminal_samples=tuple(item.record() for item in fingerprints),
        reasons=reasons,
    )
