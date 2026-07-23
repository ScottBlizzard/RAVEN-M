from dataclasses import dataclass
from enum import Enum

from raven_m.controller.episode_controller import _json_safe


class Kind(Enum):
    FOOD = "food"


@dataclass
class Expense:
    name: str
    amount: float
    kind: Kind


def test_json_safe_handles_nested_androidworld_style_objects() -> None:
    value = {"expenses": [Expense("Lunch", 12.5, Kind.FOOD)]}
    assert _json_safe(value) == {
        "expenses": [{"name": "Lunch", "amount": 12.5, "kind": "food"}]
    }
