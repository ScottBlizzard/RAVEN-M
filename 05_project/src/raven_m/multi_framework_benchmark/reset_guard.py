"""Protocol lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass, field


LIFECYCLE = (
    "device_verified", "task_verified", "seed_set", "initialized",
    "stabilized", "initial_hashes_saved", "controller_complete",
    "evaluator_called", "evaluator_saved", "task_torn_down", "reset_complete",
    "residue_check_passed",
)


@dataclass
class ResetGuard:
    events: list[str] = field(default_factory=list)
    reset_warnings: int = 0
    scored_cells_since_cold_boot: int = 0

    def mark(self, event: str) -> None:
        expected = LIFECYCLE[len(self.events)] if len(self.events) < len(LIFECYCLE) else None
        if event != expected:
            raise RuntimeError(f"Lifecycle order violation: expected {expected}, got {event}")
        self.events.append(event)

    @property
    def complete(self) -> bool:
        return tuple(self.events) == LIFECYCLE

    def should_cold_reboot(self, emulator_crashed: bool = False) -> bool:
        return emulator_crashed or self.scored_cells_since_cold_boot >= 10 or self.reset_warnings >= 2
