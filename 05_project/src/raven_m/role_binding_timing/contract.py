"""Single-source contract access and conformance checks."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEFAULT_CONTRACT_PATH = (
    PROJECT_ROOT / "contracts/role_binding_timing_stage1.v0_1.json"
)
GROUNDING_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/role_binding_timing_grounding.v0_1.schema.json"
)
ACTION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/role_binding_timing_action.v0_1.schema.json"
)
SNAPSHOT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/role_binding_timing_snapshot.v0_1.schema.json"
)


class ContractError(ValueError):
    """Raised when frozen contract components diverge."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "role_binding_timing.contract.v0_1":
        raise ContractError("Unexpected role-binding timing contract version.")
    for key in ("grounding_output_schema", "action_output_schema"):
        Draft202012Validator.check_schema(contract[key])
    return contract


def grounding_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    return deepcopy((contract or load_contract())["grounding_output_schema"])


def action_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    return deepcopy((contract or load_contract())["action_output_schema"])


def assert_generated_schema_conformance(
    contract: dict[str, Any] | None = None,
) -> dict[str, str]:
    contract = contract or load_contract()
    expected = {
        GROUNDING_SCHEMA_PATH: grounding_schema(contract),
        ACTION_SCHEMA_PATH: action_schema(contract),
    }
    result: dict[str, str] = {}
    for path, generated in expected.items():
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        if on_disk != generated:
            raise ContractError(f"Generated schema drift: {path}")
        result[str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")] = (
            sha256_path(path)
        )
    snapshot = json.loads(SNAPSHOT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(snapshot)
    result[str(SNAPSHOT_SCHEMA_PATH.relative_to(REPOSITORY_ROOT)).replace("\\", "/")] = (
        sha256_path(SNAPSHOT_SCHEMA_PATH)
    )
    return result


def assert_contract_budget(contract: dict[str, Any] | None = None) -> None:
    contract = contract or load_contract()
    model = contract["model"]
    if model != {
        "id": "Qwen/Qwen3-VL-32B-Instruct",
        "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
        "backend": "qwen3_vl_32b_transformers_bf16_4x4090_v1",
        "temperature": 0,
        "do_sample": False,
        "max_new_tokens_per_call": 128,
        "calls_per_cell": 2,
        "action_proposals_per_cell": 1,
    }:
        raise ContractError("Frozen model/decoding/call/action budget drifted.")
    if contract["token_policy"]["early_late_text_token_tolerance"] != 0:
        raise ContractError("Prompt-token tolerance must remain exactly zero.")
    if contract.get("generation_eligible") is not False:
        raise ContractError("The v0.1 contract must remain generation-ineligible.")
