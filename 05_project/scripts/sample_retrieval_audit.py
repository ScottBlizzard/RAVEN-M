"""Create the frozen 50-event non-Hard retrieval review packet."""

from __future__ import annotations

import argparse
import base64
import csv
from html import escape
from io import BytesIO
import json
from pathlib import Path
import random
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SEED = 20260724
SAMPLE_SIZE = 50


def snapshot_updates(
    event: dict[str, Any],
) -> list[dict[str, Any]]:
    kind = event.get("event")
    if kind in {"write", "transition"}:
        return [event["item"]]
    if kind in {"contradiction", "supersede"}:
        return event["items"]
    return []


def collect(suite_dir: Path) -> list[dict[str, Any]]:
    candidates = []
    for episode_dir in sorted((suite_dir / "episodes").glob("*")):
        episode_path = episode_dir / "episode.json"
        event_path = episode_dir / "memory_events.jsonl"
        if not episode_path.is_file() or not event_path.is_file():
            continue
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        steps = {int(item["step"]): item for item in episode["steps"]}
        state: dict[str, dict[str, Any]] = {}
        events = [
            json.loads(line)
            for line in event_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for event in events:
            for item in snapshot_updates(event):
                state[item["memory_id"]] = item
            if event.get("event") != "route":
                continue
            if event["route"] == "SUPPRESS":
                continue
            item = state.get(event["memory_id"])
            if not item:
                continue
            step = int(event["step"])
            step_record = steps.get(step, {})
            decision = step_record.get("decision") or {}
            source_path = (
                item.get("source", {}).get("screenshot_paths", [None])[0]
            )
            candidates.append(
                {
                    "episode_dir": episode_dir,
                    "episode_id": episode["episode_id"],
                    "variant": episode["variant"],
                    "task_name": episode["task_name"],
                    "task_goal": episode["task_goal"],
                    "event_index": event["event_index"],
                    "step": step,
                    "memory_id": item["memory_id"],
                    "memory_type": item["memory_type"],
                    "route": event["route"],
                    "status": item["verification_status"],
                    "score": event["score"],
                    "reliability": event["reliability"],
                    "content": item["content"]["natural_language"],
                    "source_screenshot": source_path,
                    "decision_summary": decision.get(
                        "decision_summary", ""
                    ),
                    "action": json.dumps(
                        decision.get("action"),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "cited": item["memory_id"]
                    in decision.get("memory_citations", []),
                }
            )
    return candidates


def image_data_url(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((480, 800), Image.Resampling.LANCZOS)
        stream = BytesIO()
        image.save(stream, format="JPEG", quality=72, optimize=True)
    encoded = base64.b64encode(stream.getvalue()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def select_sample(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(candidates) < SAMPLE_SIZE:
        raise ValueError(
            f"Need {SAMPLE_SIZE} non-suppressed routes; found "
            f"{len(candidates)}."
        )
    rng = random.Random(SAMPLE_SEED)
    by_route: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        by_route.setdefault(item["route"], []).append(item)
    selected = []
    # Guarantee route diversity, then fill from all remaining events.
    for route in sorted(by_route):
        group = by_route[route][:]
        rng.shuffle(group)
        selected.extend(group[: min(5, len(group))])
    selected_keys = {
        (item["episode_id"], item["event_index"]) for item in selected
    }
    remainder = [
        item
        for item in candidates
        if (item["episode_id"], item["event_index"]) not in selected_keys
    ]
    rng.shuffle(remainder)
    selected.extend(remainder[: SAMPLE_SIZE - len(selected)])
    return selected[:SAMPLE_SIZE]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "metadata/retrieval_audit_50.csv",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=PROJECT_ROOT / "metadata/retrieval_audit_50.html",
    )
    args = parser.parse_args()
    candidates = collect(args.suite_dir)
    try:
        selected = select_sample(candidates)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    rows = []
    html_rows = []
    for audit_index, item in enumerate(selected, start=1):
        source = item["source_screenshot"]
        source_path = item["episode_dir"] / source if source else None
        row = {
            "audit_id": f"R{audit_index:03d}",
            "episode_id": item["episode_id"],
            "variant": item["variant"],
            "task_name": item["task_name"],
            "event_index": item["event_index"],
            "step": item["step"],
            "memory_id": item["memory_id"],
            "memory_type": item["memory_type"],
            "route": item["route"],
            "status": item["status"],
            "score": item["score"],
            "reliability": item["reliability"],
            "cited": item["cited"],
            "task_goal": item["task_goal"],
            "content": item["content"],
            "decision_summary": item["decision_summary"],
            "action": item["action"],
            "source_screenshot": (
                str(source_path.resolve()) if source_path else ""
            ),
            "relevant_label": "",
            "route_appropriate_label": "",
            "fact_supported_label": "",
            "useful_label": "",
            "harmful_label": "",
            "utility_label": "",
            "review_notes": "",
        }
        rows.append(row)
        image_html = (
            f'<img src="{image_data_url(source_path)}">'
            if source_path and source_path.is_file()
            else "<em>missing image</em>"
        )
        html_rows.append(
            "<section>"
            f"<h2>{escape(row['audit_id'])} · {escape(row['route'])} · "
            f"{escape(row['memory_id'])}</h2>"
            f"<p><b>Task:</b> {escape(row['task_goal'])}</p>"
            f"<p><b>Memory:</b> {escape(row['content'])}</p>"
            f"<p><b>Decision:</b> "
            f"{escape(row['decision_summary'])}</p>"
            f"<p><b>Action:</b> {escape(row['action'])} · "
            f"<b>Cited:</b> {row['cited']}</p>"
            f"{image_html}</section>"
        )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    html = """<!doctype html><meta charset="utf-8">
<title>RAVEN-M retrieval audit 50</title>
<style>
body{font:15px/1.45 system-ui;max-width:1100px;margin:auto;padding:24px}
section{border:1px solid #bbb;border-radius:10px;padding:16px;margin:18px 0}
img{max-width:480px;max-height:800px;border:1px solid #ddd}
h2{margin-top:0} p{overflow-wrap:anywhere}
</style>
<h1>Non-Hard retrieval audit — frozen sample seed 20260724</h1>
<p><b>Fixed rubric.</b> Relevant: applies to the current task/subgoal.
Route-appropriate: FACT is visibly supported and current; HYPOTHESIS is
plausible but still needs verification; ALERT correctly warns about a
conflict/failure. Useful: reduces decision uncertainty or guides a concrete
check/action. Harmful: accepting it could plausibly cause a wrong action,
loop, or premature completion. Utility is yes exactly when relevant,
route-appropriate, useful, not harmful, and any FACT is screenshot-supported.
Use only the displayed task, memory, decision, provenance screenshot, and
route; do not use evaluator outcomes.</p>
""" + "\n".join(html_rows)
    args.output_html.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "candidate_count": len(candidates),
                "sample_count": len(rows),
                "sample_seed": SAMPLE_SEED,
                "route_counts": {
                    route: sum(row["route"] == route for row in rows)
                    for route in sorted({row["route"] for row in rows})
                },
                "csv": str(args.output_csv),
                "html": str(args.output_html),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
