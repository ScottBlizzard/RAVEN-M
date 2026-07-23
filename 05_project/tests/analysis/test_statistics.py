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


def test_case_selection_uses_predeclared_cells() -> None:
    results = []
    outcomes = {
        "H01": (True, False),
        "H02": (False, True),
        "H03": (True, True),
        "H04": (False, False),
        "H05": (False, False),
    }
    for task_id, (m0_success, b3_success) in outcomes.items():
        for variant, success, calls in (
            ("M0", m0_success, 8),
            ("B3", b3_success, 10),
        ):
            results.append(
                {
                    "task_id": task_id,
                    "instance_seed": 1,
                    "variant": variant,
                    "valid_scored_episode": True,
                    "success": success,
                    "failure_code": None if success else "FAIL",
                    "model_call_count": calls,
                    "task_goal": task_id,
                    "episode_path": f"{task_id}/{variant}",
                }
            )
    task_meta = {
        task_id: {
            "optimal_steps_from_task_list": index + 1,
            "tags": [f"category_{index}"],
        }
        for index, task_id in enumerate(outcomes)
    }
    cases = analysis.select_cases(results, task_meta)
    cells = [item["cell"] for item in cases]
    assert "m0_success_b3_failure" in cells
    assert "m0_failure_b3_success" in cells
    assert "both_success" in cells
    assert cells.count("both_failure") == 2
