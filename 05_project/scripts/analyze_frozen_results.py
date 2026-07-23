"""Generate all protocol-v1 tables, statistics, figures, and report text."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
BOOTSTRAP_SEED = 20260723
BOOTSTRAP_REPLICATES = 10_000
EXPECTED_COVERAGE = {
    "B0": 57,
    "B1": 19,
    "B2": 19,
    "B3": 57,
    "S0": 27,
    "M0": 57,
    "MREL": 16,
    "MNO_WM": 16,
    "MNO_VEL": 16,
    "MNO_FRM": 16,
    "MNO_PSI": 16,
    "MNO_CRITIC": 16,
    "B3_CTX": 16,
    "B3_CALL": 16,
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (math.nan, math.nan)
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            p * (1 - p) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return center - radius, center + radius


def exact_mcnemar(b: int, c: int) -> float:
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, k)
        for k in range(0, min(b, c) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def percentile_interval(values: np.ndarray) -> tuple[float, float]:
    lower, upper = np.percentile(values, [2.5, 97.5])
    return float(lower), float(upper)


def paired_rows(
    results: list[dict[str, Any]],
    treatment: str,
    control: str,
) -> list[dict[str, Any]]:
    selected = {
        (item["task_id"], item["instance_seed"], item["variant"]): item
        for item in results
        if item["valid_scored_episode"]
    }
    pairs = []
    keys = sorted(
        {
            (task, seed)
            for task, seed, variant in selected
            if variant == treatment
        }
        & {
            (task, seed)
            for task, seed, variant in selected
            if variant == control
        }
    )
    for task, seed in keys:
        treated = selected[(task, seed, treatment)]
        baseline = selected[(task, seed, control)]
        pairs.append(
            {
                "task_id": task,
                "instance_seed": seed,
                "treatment": int(treated["success"]),
                "control": int(baseline["success"]),
                "difference": (
                    int(treated["success"]) - int(baseline["success"])
                ),
            }
        )
    return pairs


def bootstrap(
    pairs: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    task_ids = sorted({item["task_id"] for item in pairs})
    groups = {
        task_id: np.array(
            [
                item["difference"]
                for item in pairs
                if item["task_id"] == task_id
            ],
            dtype=float,
        )
        for task_id in task_ids
    }
    clustered = np.empty(BOOTSTRAP_REPLICATES)
    for index in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(task_ids, size=len(task_ids), replace=True)
        clustered[index] = np.concatenate(
            [groups[task_id] for task_id in sampled]
        ).mean()
    differences = np.array(
        [item["difference"] for item in pairs],
        dtype=float,
    )
    instance = np.empty(BOOTSTRAP_REPLICATES)
    for index in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(
            differences,
            size=len(differences),
            replace=True,
        )
        instance[index] = sampled.mean()
    return clustered, instance


def numeric(items: Iterable[dict[str, Any]], key: str) -> list[float]:
    return [float(item[key]) for item in items]


def summarize_variant(
    variant: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    valid = [item for item in items if item["valid_scored_episode"]]
    successes = sum(int(item["success"]) for item in valid)
    low, high = wilson(successes, len(valid))
    steps = numeric(valid, "executed_action_count")
    calls = numeric(valid, "model_call_count")
    tokens = numeric(valid, "total_tokens")
    wall = numeric(valid, "episode_wall_seconds")
    return {
        "variant": variant,
        "successes": successes,
        "denominator": len(valid),
        "tsr": successes / len(valid) if valid else math.nan,
        "wilson95_low": low,
        "wilson95_high": high,
        "mean_steps": mean(steps) if steps else math.nan,
        "median_steps": median(steps) if steps else math.nan,
        "mean_calls": mean(calls) if calls else math.nan,
        "median_calls": median(calls) if calls else math.nan,
        "mean_total_tokens": mean(tokens) if tokens else math.nan,
        "median_total_tokens": median(tokens) if tokens else math.nan,
        "median_wall_seconds": median(wall) if wall else math.nan,
        "success_per_100_calls": (
            100 * successes / sum(calls) if sum(calls) else 0.0
        ),
        "success_per_million_tokens": (
            1_000_000 * successes / sum(tokens) if sum(tokens) else 0.0
        ),
        "loop_events": sum(item["loop_event_count"] for item in valid),
        "memory_citation_decisions": sum(
            item["memory_citation_decision_count"] for item in valid
        ),
    }


def comparison(
    results: list[dict[str, Any]],
    treatment: str,
    control: str,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    pairs = paired_rows(results, treatment, control)
    if not pairs:
        raise RuntimeError(f"No paired rows for {treatment} vs {control}.")
    clustered, instance = bootstrap(pairs)
    b = sum(
        item["control"] == 1 and item["treatment"] == 0 for item in pairs
    )
    c = sum(
        item["control"] == 0 and item["treatment"] == 1 for item in pairs
    )
    cluster_ci = percentile_interval(clustered)
    instance_ci = percentile_interval(instance)
    return (
        {
            "treatment": treatment,
            "control": control,
            "paired_instances": len(pairs),
            "task_clusters": len({item["task_id"] for item in pairs}),
            "absolute_tsr_difference": mean(
                item["difference"] for item in pairs
            ),
            "cluster_bootstrap95_low": cluster_ci[0],
            "cluster_bootstrap95_high": cluster_ci[1],
            "instance_bootstrap95_low": instance_ci[0],
            "instance_bootstrap95_high": instance_ci[1],
            "control_success_treatment_failure_b": b,
            "control_failure_treatment_success_c": c,
            "exact_mcnemar_p": exact_mcnemar(b, c),
        },
        clustered,
        instance,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-summary",
        type=Path,
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "reports/generated",
    )
    args = parser.parse_args()
    results: list[dict[str, Any]] = []
    source_hashes = {}
    for path in args.suite_summary:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not payload.get("finished"):
            raise RuntimeError(f"Suite is unfinished: {path}")
        if payload.get("audit_error_count") or payload.get(
            "pairing_error_count"
        ):
            raise RuntimeError(f"Suite audit failed: {path}")
        results.extend(payload["results"])
        source_hashes[path.as_posix()] = sha256(path.read_bytes()).hexdigest()
    keys = [
        (item["task_id"], item["instance_seed"], item["variant"])
        for item in results
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate task/seed/variant result cells.")
    coverage = {
        variant: sum(item["variant"] == variant for item in results)
        for variant in EXPECTED_COVERAGE
    }
    if coverage != EXPECTED_COVERAGE:
        raise RuntimeError(
            f"Frozen result coverage differs: {coverage}"
        )
    by_variant = {
        variant: [item for item in results if item["variant"] == variant]
        for variant in EXPECTED_COVERAGE
    }
    main_rows = [
        summarize_variant(variant, by_variant[variant])
        for variant in EXPECTED_COVERAGE
    ]
    comparisons = []
    bootstrap_rows = []
    for treatment, control in (("M0", "B3"), ("M0", "B0")):
        stats, clustered, instance = comparison(
            results,
            treatment,
            control,
        )
        comparisons.append(stats)
        for index, (cluster_value, instance_value) in enumerate(
            zip(clustered, instance, strict=True)
        ):
            bootstrap_rows.append(
                {
                    "comparison": f"{treatment}_minus_{control}",
                    "replicate": index,
                    "clustered_difference": cluster_value,
                    "instance_difference": instance_value,
                }
            )
    ablation_rows = []
    for variant in (
        "MREL",
        "MNO_WM",
        "MNO_VEL",
        "MNO_FRM",
        "MNO_PSI",
        "MNO_CRITIC",
        "B3_CTX",
        "B3_CALL",
        "S0",
    ):
        pairs = paired_rows(results, "M0", variant)
        ablation_rows.append(
            {
                "control_variant": variant,
                "full_variant": "M0",
                "paired_instances": len(pairs),
                "m0_successes": sum(item["treatment"] for item in pairs),
                "control_successes": sum(item["control"] for item in pairs),
                "m0_minus_control": (
                    mean(item["difference"] for item in pairs)
                    if pairs
                    else math.nan
                ),
                "m0_only_wins": sum(
                    item["treatment"] == 1 and item["control"] == 0
                    for item in pairs
                ),
                "control_only_wins": sum(
                    item["treatment"] == 0 and item["control"] == 1
                    for item in pairs
                ),
            }
        )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "table_main.csv", main_rows)
    write_csv(output / "table_efficiency.csv", main_rows)
    write_csv(output / "table_ablation.csv", ablation_rows)
    write_csv(output / "bootstrap_replicates.csv", bootstrap_rows)
    statistics = {
        "schema_version": "frozen_analysis.v1",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "coverage": coverage,
        "source_suite_sha256": source_hashes,
        "primary_and_secondary_comparisons": comparisons,
    }
    write_json(output / "statistics.json", statistics)

    labels = [row["variant"] for row in main_rows]
    estimates = np.array([row["tsr"] for row in main_rows])
    lower = np.array([row["wilson95_low"] for row in main_rows])
    upper = np.array([row["wilson95_high"] for row in main_rows])
    x = np.arange(len(labels))
    fig, axis = plt.subplots(figsize=(12, 5))
    axis.errorbar(
        x,
        estimates,
        yerr=np.vstack([estimates - lower, upper - estimates]),
        fmt="o",
        capsize=4,
        color="#1f5d8f",
    )
    axis.set_xticks(x, labels, rotation=45, ha="right")
    axis.set_ylabel("Task success rate")
    axis.set_ylim(0, 1)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output / "figure_tsr_wilson.png", dpi=220)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 5))
    for row in main_rows:
        axis.scatter(
            row["median_calls"],
            row["tsr"],
            label=row["variant"],
            s=50,
        )
    axis.set_xlabel("Median model calls per episode")
    axis.set_ylabel("Task success rate")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure_efficiency_pareto.png", dpi=220)
    plt.close(fig)

    primary = comparisons[0]
    direction = (
        "positive"
        if primary["absolute_tsr_difference"] > 0
        else (
            "negative"
            if primary["absolute_tsr_difference"] < 0
            else "zero"
        )
    )
    report = f"""# Frozen protocol-v1 results

All values in this document were generated from the four completed suite
summaries listed in `statistics.json`; no task or case was selected to improve
the aggregate result.

## Main result

M0 minus B3 is {primary['absolute_tsr_difference']:.4f} absolute TSR
(clustered 95% bootstrap interval
[{primary['cluster_bootstrap95_low']:.4f},
{primary['cluster_bootstrap95_high']:.4f}]). The observed direction is
**{direction}**. Exact McNemar p =
{primary['exact_mcnemar_p']:.6g}, with b =
{primary['control_success_treatment_failure_b']} and c =
{primary['control_failure_treatment_success_c']}.

This assessment reports the estimate and uncertainty as observed. It does not
convert a low-power or null result into a universal performance claim.

## Artifacts

- `table_main.csv`: TSR numerators, denominators, Wilson intervals.
- `table_efficiency.csv`: steps, calls, tokens, latency, cost-normalized rates.
- `table_ablation.csv`: every predeclared paired component/control cell.
- `bootstrap_replicates.csv`: all 10,000 clustered and instance replicates.
- `figure_tsr_wilson.png` and `figure_efficiency_pareto.png`.
"""
    (output / "results_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(statistics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
