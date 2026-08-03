"""Offline prompt/schema/adapter and exact-token conformance audit."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
from tokenizers import Tokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_adapter_v0_2_1 import EestActionAdapterV021  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_1 import (  # noqa: E402
    DEFAULT_CONTRACT_PATH,
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    build_decision_schema,
    load_contract,
    render_executor_prompt,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


ASCII = "".join(chr(index) for index in range(33, 127))


def _high_entropy(length: int, offset: int = 0) -> str:
    return "".join(ASCII[(index * 37 + offset) % len(ASCII)] for index in range(length))


def _maximum_field(spec: dict[str, Any], offset: int) -> Any:
    kind = spec["kind"]
    if kind == "coordinate":
        return 1.0
    if kind == "integer":
        return spec["maximum"]
    if kind == "boolean":
        return True
    if kind == "string":
        return _high_entropy(spec["maxLength"], offset)
    raise RuntimeError(f"Unknown field kind: {kind}")


def _maximal_decisions(contract: dict[str, Any]) -> list[dict[str, Any]]:
    values = []
    for action_spec in contract["actions"]:
        action = {"type": action_spec["type"]}
        for index, (field, spec) in enumerate(action_spec["fields"].items()):
            if field in action_spec["required"]:
                action[field] = _maximum_field(spec, index)
        values.append(
            {
                "status": action_spec["phase"],
                "action": action,
                "intent": _high_entropy(24, 1),
                "evidence": [
                    {
                        "entity": _high_entropy(16, 2),
                        "field": _high_entropy(16, 3),
                        "value": _high_entropy(40, 4),
                        "scope": "cross_page",
                    }
                ],
                "citations": ["task:" + "".join("Ab3-"[index % 4] for index in range(35))],
            }
        )
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_contract()
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt = DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")
    generated = schema == build_decision_schema(contract) and prompt == render_executor_prompt(contract)
    if not generated:
        raise RuntimeError("Generated prompt/schema drifted from the action contract.")

    matrix = EestActionAdapterV021().conformance_matrix()
    if not all(row["adapter_conformant"] for row in matrix):
        raise RuntimeError("Adapter conformance matrix failed.")
    prompt_rows = []
    for item in contract["actions"]:
        example = json.dumps(item["example"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        present = example in prompt and f"required={','.join(item['required'])}" in prompt
        prompt_rows.append({"type": item["type"], "syntax_and_example_present": present})
    if not all(row["syntax_and_example_present"] for row in prompt_rows):
        raise RuntimeError("Prompt does not contain every contract action form.")

    tokenizer = Tokenizer.from_file(str(args.tokenizer_json))
    validator = Draft202012Validator(schema)
    serialized_rows = []
    for value in _maximal_decisions(contract):
        errors = list(validator.iter_errors(value))
        if errors:
            raise RuntimeError(f"Maximal decision failed schema: {errors[0].message}")
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        tokens = len(tokenizer.encode(raw).ids)
        serialized_rows.append(
            {
                "type": value["action"]["type"],
                "utf8_bytes": len(raw.encode("utf-8")),
                "qwen_tokens": tokens,
                "under_256": tokens < 256,
                "serialized_sha256": sha256(raw.encode("utf-8")).hexdigest(),
            }
        )
    if not all(row["under_256"] for row in serialized_rows):
        raise RuntimeError("At least one maximal high-entropy decision reaches 256 tokens.")

    result = {
        "schema_version": "eest_ac_action_contract_audit.v0_2_1",
        "status": "pass",
        "zero_model_generation_calls": 0,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "hashes": {
            "contract": _hash(DEFAULT_CONTRACT_PATH),
            "schema": _hash(DEFAULT_SCHEMA_PATH),
            "prompt": _hash(DEFAULT_PROMPT_PATH),
            "tokenizer_json": _hash(args.tokenizer_json),
        },
        "generated_artifacts_exact": generated,
        "prompt_matrix": prompt_rows,
        "schema_adapter_matrix": matrix,
        "maximal_serialization": {
            "construction": "all required action fields at schema maxima plus high-entropy maximum intent/evidence/citation fields",
            "max_new_tokens": 256,
            "maximum_qwen_tokens": max(row["qwen_tokens"] for row in serialized_rows),
            "maximum_utf8_bytes": max(row["utf8_bytes"] for row in serialized_rows),
            "rows": serialized_rows,
        },
    }
    _write(args.output, result)
    print(
        json.dumps(
            {
                "status": "pass",
                "actions": len(matrix),
                "maximum_qwen_tokens": result["maximal_serialization"]["maximum_qwen_tokens"],
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
