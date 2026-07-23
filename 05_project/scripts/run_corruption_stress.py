"""Run 20 deterministic non-Hard corruption fixtures against the router."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.memory.models import (  # noqa: E402
    MemoryConfig,
    MemoryItem,
    MemorySource,
    RetrievalQuery,
)
from raven_m.memory.retrieval import score_item  # noqa: E402


def fixture(index: int) -> tuple[str, MemoryItem, RetrievalQuery]:
    group = index // 5
    if group == 0:
        perturbation = "stale_same_page"
        memory_type = "episodic_fact"
        status = "stale"
        page = "screen:current"
        origin = "direct_visual_observation"
    elif group == 1:
        perturbation = "contradicted_same_page"
        memory_type = "episodic_fact"
        status = "contradicted"
        page = "screen:current"
        origin = "direct_visual_observation"
    elif group == 2:
        perturbation = "unverified_wrong_page"
        memory_type = "page_hint"
        status = "candidate"
        page = "screen:wrong"
        origin = "model_inference"
    else:
        perturbation = "failure_wrong_page"
        memory_type = "failure"
        status = "observed"
        page = "screen:wrong"
        origin = "direct_action_outcome"
    item = MemoryItem(
        memory_id=(
            f"f_{index + 1:04d}"
            if memory_type == "failure"
            else f"m_{index + 1:04d}"
        ),
        episode_id=f"corruption-fixture-{index:02d}",
        memory_type=memory_type,
        content={
            "subject": "save_control",
            "predicate": "location_or_effect",
            "object": f"wrong_value_{index}",
            "natural_language": (
                "A corrupted save-control memory should not be trusted as "
                f"fact in fixture {index}."
            ),
        },
        task_id="SyntheticNonHardRouterFixture",
        created_step=0,
        last_confirmed_step=0,
        source=MemorySource(
            observation_ids=(f"obs_{index:06d}",),
            screenshot_paths=(f"fixture_{index:02d}.png",),
            screenshot_sha256=(f"{index:064x}",),
        ),
        evidence={
            "origin": origin,
            "action_outcome": (
                "same-page action failed" if memory_type == "failure" else None
            ),
            "independent_confirmations": 0,
        },
        verification_status=status,
        page_signature=page,
        confidence_model=0.95,
    )
    query = RetrievalQuery(
        step_id=1,
        task_terms=("save", "control"),
        required_variables=("save_control",),
        page_signature="screen:current",
    )
    return perturbation, item, query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metadata" / "corruption_stress.json",
    )
    args = parser.parse_args()
    config = MemoryConfig()
    results: list[dict[str, Any]] = []
    for index in range(20):
        perturbation, item, query = fixture(index)
        routed = score_item(item, query, config)
        results.append(
            {
                "fixture_id": f"C{index + 1:02d}",
                "perturbation": perturbation,
                "memory_id": item.memory_id,
                "status": item.verification_status,
                "memory_type": item.memory_type,
                "route": routed.route,
                "reliability": round(routed.reliability, 8),
                "score": round(routed.score, 8),
                "passed": routed.route != "FACT",
            }
        )
    passed = sum(int(item["passed"]) for item in results)
    output = {
        "schema_version": "corruption_stress.v1",
        "scope": "synthetic_non_hard_router_fixtures",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_count": len(results),
        "non_fact_count": passed,
        "corruption_rejection_rate": passed / len(results),
        "status": "passed" if passed == len(results) else "failed",
        "fixtures": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if output["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
