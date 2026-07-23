"""Apply one reviewer's component labels to the frozen retrieval CSV."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"yes", "no"}
COMPONENT_COLUMNS = (
    "relevant_label",
    "route_appropriate_label",
    "useful_label",
    "harmful_label",
)


def derive_utility(row: dict[str, str]) -> str:
    supported = (
        row["route"] != "FACT"
        or row["fact_supported_label"] == "yes"
    )
    return (
        "yes"
        if (
            row["relevant_label"] == "yes"
            and row["route_appropriate_label"] == "yes"
            and row["useful_label"] == "yes"
            and row["harmful_label"] == "no"
            and supported
        )
        else "no"
    )


def apply_labels(
    rows: list[dict[str, str]],
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    if payload.get("schema_version") != "retrieval_labels.v1":
        raise ValueError("Unexpected retrieval-label schema.")
    if payload.get("review_status") != "completed_single_reviewer":
        raise ValueError("Retrieval review is not completed_single_reviewer.")
    labels = {
        str(item["audit_id"]): item for item in payload.get("items", [])
    }
    expected = [row["audit_id"] for row in rows]
    if len(rows) != 50 or set(labels) != set(expected):
        raise ValueError("Labels do not exactly match the frozen 50 rows.")
    if len(labels) != len(payload.get("items", [])):
        raise ValueError("Duplicate audit_id in retrieval labels.")
    output = []
    for source in rows:
        row = dict(source)
        label = labels[row["audit_id"]]
        for column in COMPONENT_COLUMNS:
            value = str(label.get(column, "")).strip().lower()
            if value not in ALLOWED:
                raise ValueError(f"{row['audit_id']} has invalid {column}.")
            row[column] = value
        if row["route"] == "FACT":
            fact = str(
                label.get("fact_supported_label", "")
            ).strip().lower()
            if fact not in ALLOWED:
                raise ValueError(
                    f"{row['audit_id']} needs fact_supported_label."
                )
            row["fact_supported_label"] = fact
        else:
            row["fact_supported_label"] = ""
        row["utility_label"] = derive_utility(row)
        row["review_notes"] = str(label.get("review_notes", "")).strip()
        needs_note = (
            row["utility_label"] == "no"
            or row["harmful_label"] == "yes"
            or (
                row["route"] == "FACT"
                and row["fact_supported_label"] == "no"
            )
        )
        if needs_note and not row["review_notes"]:
            raise ValueError(
                f"{row['audit_id']} needs a note for a negative/harm label."
            )
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--retrieval-audit",
        type=Path,
        default=PROJECT_ROOT / "metadata/retrieval_audit_50.csv",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=PROJECT_ROOT / "metadata/retrieval_audit_labels.json",
    )
    args = parser.parse_args()
    with args.retrieval_audit.open(
        encoding="utf-8",
        newline="",
    ) as stream:
        rows = list(csv.DictReader(stream))
    payload = json.loads(args.labels.read_text(encoding="utf-8"))
    output = apply_labels(rows, payload)
    temporary = args.retrieval_audit.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    temporary.replace(args.retrieval_audit)
    print(
        json.dumps(
            {
                "status": "ok",
                "rows": len(output),
                "utility_yes": sum(
                    row["utility_label"] == "yes" for row in output
                ),
                "harmful_yes": sum(
                    row["harmful_label"] == "yes" for row in output
                ),
                "csv_sha256": sha256(
                    args.retrieval_audit.read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
