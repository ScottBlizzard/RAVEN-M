"""Protocol-v0.2 multi-framework benchmark infrastructure.

This package is intentionally controller-agnostic.  It normalizes, audits and
budgets controller output; it must never improve or repair a controller policy.
"""

from .arm_registry import ARM_REGISTRY, ArmSpec
from .runner import CellLimits, StageAuthorization

__all__ = ["ARM_REGISTRY", "ArmSpec", "CellLimits", "StageAuthorization"]
