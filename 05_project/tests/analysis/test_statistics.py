import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "analyze_frozen_results.py"
)
SPEC = importlib.util.spec_from_file_location("analyze_frozen_results", SCRIPT)
assert SPEC and SPEC.loader
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def test_wilson_and_exact_mcnemar_known_values() -> None:
    low, high = analysis.wilson(5, 10)
    assert 0.23 < low < 0.24
    assert 0.76 < high < 0.77
    assert analysis.exact_mcnemar(0, 0) == 1.0
    assert analysis.exact_mcnemar(0, 5) == 0.0625


def test_cluster_bootstrap_is_deterministic_and_task_clustered() -> None:
    pairs = [
        {
            "task_id": f"H{task:02d}",
            "instance_seed": seed,
            "difference": 1 if task % 2 else -1,
        }
        for task in range(1, 5)
        for seed in (1, 2, 3)
    ]
    first_cluster, first_instance = analysis.bootstrap(pairs)
    second_cluster, second_instance = analysis.bootstrap(pairs)
    assert len(first_cluster) == 10_000
    assert np.array_equal(first_cluster, second_cluster)
    assert np.array_equal(first_instance, second_instance)
