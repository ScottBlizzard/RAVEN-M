"""Contract-audited AndroidWorld adapter for EEST-AC v0.2.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from raven_m.eest_ac.action_contract_v0_2_2 import action_schema, load_contract
from raven_m.env.androidworld_adapter import AndroidWorldAdapter, MappedAction


@dataclass(frozen=True)
class ContractMappedActionV022:
    canonical: dict[str, Any]
    contract_operation: str
    delegate: MappedAction

    def audit_record(self) -> dict[str, Any]:
        return {
            "canonical": self.canonical,
            "contract_operation": self.contract_operation,
            "delegate": self.delegate.audit_record(),
        }


class EestActionAdapterV022:
    """Map only actions validated against the v0.2.2 authoritative catalog."""

    def __init__(self, delegate: AndroidWorldAdapter | None = None) -> None:
        self.contract = load_contract()
        self.delegate = delegate or AndroidWorldAdapter()
        self._by_type = {item["type"]: item for item in self.contract["actions"]}
        self._validator = Draft202012Validator(action_schema(self.contract))

    def map_action(
        self,
        canonical: dict[str, Any],
        *,
        screen_width: int,
        screen_height: int,
    ) -> ContractMappedActionV022:
        errors = list(self._validator.iter_errors(canonical))
        if errors:
            raise ValueError(f"ACTION_CONTRACT_REJECTED:{errors[0].message}")
        mapped = self.delegate.map_action(
            canonical,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        expected = self._by_type[canonical["type"]]["adapter_operation"]
        actual = self._operation(mapped)
        if actual != expected:
            raise RuntimeError(f"ADAPTER_CONFORMANCE:{canonical['type']} expected={expected} actual={actual}")
        return ContractMappedActionV022(dict(canonical), expected, mapped)

    @staticmethod
    def _operation(mapped: MappedAction) -> str:
        action_type = mapped.canonical["type"]
        if action_type == "answer":
            return "interaction_cache_answer"
        if mapped.upstream_action is not None:
            return str(mapped.upstream_action["action_type"])
        return {
            "swipe": "adb_swipe",
            "long_press": "adb_long_press",
            "wait": "sleep",
        }.get(action_type, "unsupported")

    def execute(self, env: Any, mapped: ContractMappedActionV022) -> None:
        self.delegate.execute(env, mapped.delegate)

    def conformance_matrix(self, *, screen_width: int = 1080, screen_height: int = 2400) -> list[dict[str, Any]]:
        rows = []
        for item in self.contract["actions"]:
            mapped = self.map_action(
                item["example"],
                screen_width=screen_width,
                screen_height=screen_height,
            )
            rows.append({
                "type": item["type"],
                "phase": item["phase"],
                "required": item["required"],
                "optional": item["optional"],
                "schema_accepts_example": True,
                "adapter_expected": item["adapter_operation"],
                "adapter_actual": mapped.contract_operation,
                "adapter_conformant": mapped.contract_operation == item["adapter_operation"],
            })
        return rows
