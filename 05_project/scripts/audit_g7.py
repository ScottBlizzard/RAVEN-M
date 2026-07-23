"""Evaluate the final non-Hard method gate before protocol freeze."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-summary", type=Path, required=True)
    parser.add_argument(
        "--retrieval-audit",
        type=Path,
        default=PROJECT_ROOT / "metadata/retrieval_audit_50.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metadata/g7_audit.json",
    )
    args = parser.parse_args()
    suite = json.loads(args.suite_summary.read_text(encoding="utf-8"))
    g6 = json.loads(
        (PROJECT_ROOT / "metadata/g6_audit.json").read_text(
            encoding="utf-8"
        )
    )
    corruption = json.loads(
        (PROJECT_ROOT / "metadata/corruption_stress.json").read_text(
            encoding="utf-8"
        )
    )
    with args.retrieval_audit.open(
        encoding="utf-8",
        newline="",
    ) as stream:
        rows = list(csv.DictReader(stream))
    allowed = {"yes", "no"}
    label_columns = (
        "relevant_label",
        "route_appropriate_label",
        "utility_label",
        "harmful_label",
    )
    label_errors = [
        f"{row.get('audit_id')}:{column}"
        for row in rows
        for column in label_columns
        if row.get(column, "").strip().lower() not in allowed
    ]
    fact_errors = [
        row.get("audit_id")
        for row in rows
        if row.get("route") == "FACT"
        and row.get("fact_supported_label", "").strip().lower()
        not in allowed
    ]
    utility_yes = sum(
        row.get("utility_label", "").strip().lower() == "yes"
        for row in rows
    )
    utility_rate = utility_yes / len(rows) if rows else 0.0
    harmful_yes = sum(
        row.get("harmful_label", "").strip().lower() == "yes"
        for row in rows
    )
    m0 = suite["variant_results"]["M0"]
    checks: dict[str, Any] = {
        "suite_finished": suite.get("finished") is True,
        "m0_episode_count_at_least_8": m0["episode_count"] >= 8,
        "m0_acceptance_passed": m0["acceptance_passed"] is True,
        "no_invariant_error": m0["invariant_error_count"] == 0,
        "no_stale_fact": m0["stale_fact_route_count"] == 0,
        "context_cap_respected": m0["context_cap_respected"] is True,
        "g6_passed": g6["status"] == "passed",
        "corruption_stress_passed": corruption["status"] == "passed",
        "retrieval_sample_exactly_50": len(rows) == 50,
        "retrieval_labels_complete": not label_errors and not fact_errors,
        "retrieval_utility_at_least_80pct": utility_rate >= 0.80,
    }
    errors = [key for key, passed in checks.items() if not passed]
    output = {
        "schema_version": "g7_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "suite_id": suite["suite_id"],
        "checks": checks,
        "m0": m0,
        "retrieval_audit": {
            "sample_count": len(rows),
            "utility_yes": utility_yes,
            "utility_rate": utility_rate,
            "harmful_yes": harmful_yes,
            "label_errors": label_errors,
            "fact_label_errors": fact_errors,
        },
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
