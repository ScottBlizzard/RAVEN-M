"""Replay all frozen v0.2 raw decisions through the v0.2.1 contract."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_adapter_v0_2_1 import EestActionAdapterV021  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_1 import (  # noqa: E402
    DecisionContractError,
    parse_decision_v0_2_1,
    rejected_action_fingerprint,
)
from raven_m.eest_ac.schema import (  # noqa: E402
    EestDecisionValidationError,
    parse_eest_decision,
)


V02_SCHEMA = PROJECT_ROOT / "schemas/eest_ac_decision.v0_2.schema.json"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v0-2-run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    batch_path = args.v0_2_run_root / "batch_complete.json"
    batch = _read(batch_path)
    if batch.get("cell_count") != 9 or not batch.get("trajectory_blind_lock_released"):
        raise RuntimeError("The frozen v0.2 source batch is incomplete.")

    adapter = EestActionAdapterV021()
    rows: list[dict[str, Any]] = []
    repair_identical_count = 0
    initial_by_cell: dict[int, str | None] = {}
    for cell in sorted(batch["results"], key=lambda item: item["cell"]):
        summary = _read(REPOSITORY_ROOT / cell["episode_summary_path"])
        for call_index, record in enumerate(summary["model_call_records"], start=1):
            raw = record["content"]
            try:
                parse_eest_decision(raw, schema_path=V02_SCHEMA)
            except EestDecisionValidationError:
                original_invalid = True
            else:
                original_invalid = False
            classification: str
            normalized = None
            adapter_audit = None
            error_code = None
            try:
                parsed = parse_decision_v0_2_1(raw)
            except DecisionContractError as exc:
                classification = "must_repair"
                error_code = exc.code
            else:
                normalized = parsed.canonicalization.record() if parsed.canonicalization else None
                classification = "safe_normalize" if parsed.canonicalization and parsed.canonicalization.changed else "canonical_direct"
                if parsed.decision.get("action") is not None:
                    mapped = adapter.map_action(
                        parsed.decision["action"],
                        screen_width=1080,
                        screen_height=2400,
                    )
                    adapter_audit = mapped.audit_record()
            fingerprint = rejected_action_fingerprint(raw)
            identical = False
            if record["role"] == "executor":
                initial_by_cell[cell["cell"]] = fingerprint
            elif record["role"] == "executor_repair":
                identical = fingerprint is not None and fingerprint == initial_by_cell.get(cell["cell"])
                repair_identical_count += int(identical)
            rows.append(
                {
                    "cell": cell["cell"],
                    "task_key": cell["task_key"],
                    "arm": cell["arm"],
                    "call_index": call_index,
                    "role": record["role"],
                    "raw": raw,
                    "original_v0_2_invalid": original_invalid,
                    "v0_2_1_classification": classification,
                    "normalization": normalized,
                    "adapter_audit": adapter_audit,
                    "must_repair_code": error_code,
                    "repair_identical_to_initial_action": identical,
                    "usage": record["usage"],
                }
            )

    counts = Counter(row["v0_2_1_classification"] for row in rows)
    result = {
        "schema_version": "eest_ac_v0_2_action_replay.v0_2_1",
        "source_batch": str(args.v0_2_run_root).replace("\\", "/"),
        "source_batch_sha256": sha256(batch_path.read_bytes()).hexdigest(),
        "raw_output_count": len(rows),
        "confusion": {
            "original_invalid": sum(row["original_v0_2_invalid"] for row in rows),
            "safe_normalize": counts["safe_normalize"],
            "must_repair": counts["must_repair"],
            "canonical_direct": counts["canonical_direct"],
            "repair_outputs_identical_to_initial_invalid_action": repair_identical_count,
        },
        "must_repair_codes": dict(sorted(Counter(row["must_repair_code"] for row in rows if row["must_repair_code"]).items())),
        "rows": rows,
    }
    if len(rows) != 18 or result["confusion"]["original_invalid"] != 18:
        raise RuntimeError("Frozen replay did not recover exactly 18 invalid v0.2 outputs.")
    _write(args.output, result)
    print(json.dumps({"status": "pass", **result["confusion"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
