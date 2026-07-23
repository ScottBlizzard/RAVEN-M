"""Materialize the preregistered blocked order without loading any task."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def blocked_records(
    *,
    tasks: list[dict[str, Any]],
    instance_seed: int,
    variants: list[str],
    blocked_order_seed: int,
    phase: str,
) -> list[dict[str, Any]]:
    ordered_tasks = list(tasks)
    random.Random(blocked_order_seed + instance_seed).shuffle(ordered_tasks)
    records = []
    for task in ordered_tasks:
        ordered_variants = list(variants)
        numeric_id = int(task["id"][1:])
        random.Random(
            blocked_order_seed + instance_seed + numeric_id
        ).shuffle(ordered_variants)
        for variant in ordered_variants:
            records.append(
                {
                    "phase": phase,
                    "pair_id": f"{task['id']}-s{instance_seed}",
                    "task_id": task["id"],
                    "task_class": task["class_name"],
                    "instance_seed": instance_seed,
                    "variant": variant,
                    "native_max_steps": task["native_max_steps"],
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "configs/task_manifests/androidworld_hard_v1.json",
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        default=PROJECT_ROOT / "configs/experiments/seeds_v1.json",
    )
    parser.add_argument(
        "--ablation",
        type=Path,
        default=PROJECT_ROOT
        / "configs/task_manifests/ablation8_v1.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT
        / "configs/experiments/hard_schedule_v1.json",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    seeds = json.loads(args.seeds.read_text(encoding="utf-8"))
    ablation = json.loads(args.ablation.read_text(encoding="utf-8"))
    blocked_seed = int(seeds["blocked_order_seed"])
    breadth_seed = int(seeds["breadth_seed"])
    records = blocked_records(
        tasks=manifest["tasks"],
        instance_seed=breadth_seed,
        variants=seeds["breadth_variants"],
        blocked_order_seed=blocked_seed,
        phase="breadth",
    )
    for instance_seed in seeds["instance_seeds"]:
        if instance_seed == breadth_seed:
            continue
        records.extend(
            blocked_records(
                tasks=manifest["tasks"],
                instance_seed=int(instance_seed),
                variants=seeds["confirmatory_variants"],
                blocked_order_seed=blocked_seed,
                phase="confirmatory_additional",
            )
        )
    records.extend(
        blocked_records(
            tasks=manifest["tasks"],
            instance_seed=breadth_seed,
            variants=["S0"],
            blocked_order_seed=blocked_seed,
            phase="strict_control",
        )
    )
    ablation_ids = set(ablation["task_ids"])
    ablation_tasks = [
        item for item in manifest["tasks"] if item["id"] in ablation_ids
    ]
    ablation_variants = [
        "MREL",
        "MNO_WM",
        "MNO_VEL",
        "MNO_FRM",
        "MNO_PSI",
        "MNO_CRITIC",
        "B3_CTX",
        "B3_CALL",
    ]
    for instance_seed in ablation["instance_seeds"]:
        variants = list(ablation_variants)
        if instance_seed != breadth_seed:
            variants.append("S0")
        records.extend(
            blocked_records(
                tasks=ablation_tasks,
                instance_seed=int(instance_seed),
                variants=variants,
                blocked_order_seed=blocked_seed,
                phase="ablation_controls",
            )
        )
    for sequence, record in enumerate(records, start=1):
        record["sequence"] = sequence
    canonical = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    output = {
        "schema_version": "hard_schedule.v1",
        "manifest_id": manifest["manifest_id"],
        "blocked_order_seed": blocked_seed,
        "breadth_episode_count": sum(
            item["phase"] == "breadth" for item in records
        ),
        "confirmatory_additional_episode_count": sum(
            item["phase"] == "confirmatory_additional" for item in records
        ),
        "strict_control_episode_count": sum(
            item["phase"] == "strict_control" for item in records
        ),
        "ablation_control_episode_count": sum(
            item["phase"] == "ablation_controls" for item in records
        ),
        "total_unique_episode_count": len(records),
        "records_sha256": sha256(canonical).hexdigest(),
        "records": records,
    }
    if output["breadth_episode_count"] != 95:
        raise SystemExit("Breadth schedule must contain 95 episodes.")
    if output["confirmatory_additional_episode_count"] != 114:
        raise SystemExit(
            "Additional confirmatory schedule must contain 114 episodes."
        )
    if output["strict_control_episode_count"] != 19:
        raise SystemExit("Strict control schedule must contain 19 episodes.")
    if output["ablation_control_episode_count"] != 136:
        raise SystemExit(
            "Ablation/control schedule must contain 136 episodes."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
