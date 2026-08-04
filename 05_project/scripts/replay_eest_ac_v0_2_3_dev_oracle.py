"""Development-only replay of contaminated prior traces under v0.2.3 oracle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.outcome_oracle_v0_2_3 import (  # noqa: E402
    canonical_json,
    context_route_signature,
    evaluate_trace_v0_2_3,
    value_sha256,
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _observation(item: dict[str, Any]) -> dict[str, Any]:
    packages = sorted(item.get("package_names", []))
    a11y_available = bool(item.get("a11y_available"))
    a11y = item.get("a11y_sha256") if a11y_available else None
    return {
        "pixel_sha256": item["pixel_sha256"],
        "a11y_available": a11y_available,
        "a11y_sha256": a11y,
        "page_content_sha256": a11y,
        "package_names": packages,
        "activity": None,
        "route_signature": context_route_signature(packages, None) if packages else None,
    }


def _resolver(packages: list[str], source: str) -> dict[str, Any]:
    return {
        "target_packages": sorted(packages),
        "target_activities": [],
        "provenance_sha256": value_sha256({"development_source": source, "packages": sorted(packages)}),
    }


def _trace(
    *,
    trace_id: str,
    action_class: str,
    action: dict[str, Any],
    pre: dict[str, Any],
    posts: list[dict[str, Any]],
    resolver: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "action_class": action_class,
        "action": action,
        "resolver": resolver,
        "pre": _observation(pre),
        "post": [_observation(item) for item in posts],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    live_root = REPOSITORY_ROOT / "runs/eest_ac_v0_2_2_envelope_qualification_20260804/probes"
    v1_path = REPOSITORY_ROOT / "reports/eest_ac/eest_ac_v0_2_2_measurement_contract_v1_failed.json"
    v2_path = REPOSITORY_ROOT / "reports/eest_ac/eest_ac_v0_2_2_settling_window_qualification.json"
    rows: list[dict[str, Any]] = []
    live_classes = {
        "DEQ-SCROLL-01": "scroll",
        "DEQ-OPEN-02": "open_app",
        "DEQ-BACK-03": "navigation_press",
    }
    for cell_dir in sorted(live_root.iterdir()):
        result_path = cell_dir / "probe_result.json"
        before_path = cell_dir / "before.json"
        result = _load(result_path)
        before = _load(before_path)["observation"]
        action_class = live_classes[result["probe_id"]]
        terminal_packages = result["transition"]["samples"][-1]["package_names"]
        trace = _trace(
            trace_id=f"DEV-LIVE-{result['probe_id']}",
            action_class=action_class,
            action=result["decision"]["control_plane"]["action"],
            pre=before,
            posts=result["transition"]["samples"],
            resolver=_resolver(terminal_packages, result["probe_id"]) if action_class == "open_app" else None,
        )
        decision = evaluate_trace_v0_2_3(trace).record()
        rows.append({
            "trace_id": trace["trace_id"],
            "development_contaminated": True,
            "held_out_eligible": False,
            "source_kind": "v0.2.2_live",
            "source_files": [
                {"path": str(result_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"), "sha256": _hash(result_path)},
                {"path": str(before_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"), "sha256": _hash(before_path)},
            ],
            "trace_input_sha256": value_sha256(trace),
            "oracle": decision,
        })

    for version, path in (("v1", v1_path), ("v2", v2_path)):
        report = _load(path)
        for case in report["cases"]:
            case_id = case["case_id"]
            if "settings_scroll" in case_id:
                action_class = "scroll"
            elif "camera" in case_id:
                action_class = "navigation_press"
            else:
                action_class = "scroll"
            trace = _trace(
                trace_id=f"DEV-MEAS-{version}-{case_id}",
                action_class=action_class,
                action=case["test_action"],
                pre=case["before"],
                posts=case["raw_transition"]["samples"],
            )
            decision = evaluate_trace_v0_2_3(trace).record()
            rows.append({
                "trace_id": trace["trace_id"],
                "development_contaminated": True,
                "held_out_eligible": False,
                "source_kind": f"v0.2.2_measurement_{version}",
                "projection_note": (
                    "camera wait is projected as a navigation-class pixel-only control"
                    if "camera" in case_id else
                    "system-edge swipe is projected as scroll evidence availability control"
                    if "a11y_missing" in case_id else
                    "scroll positive remains development-only"
                ),
                "source_files": [{"path": str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"), "sha256": _hash(path)}],
                "trace_input_sha256": value_sha256(trace),
                "oracle": decision,
            })
    by_id = {row["trace_id"]: row for row in rows}
    required = {
        "DEV-LIVE-DEQ-SCROLL-01": "accept",
        "DEV-LIVE-DEQ-OPEN-02": "accept",
        "DEV-LIVE-DEQ-BACK-03": "accept",
        "DEV-MEAS-v2-dynamic_negative_camera": "reject",
        "DEV-MEAS-v2-a11y_missing_negative_notification_shade": "uncertain",
    }
    directional_pass = all(by_id[key]["oracle"]["decision"] == expected for key, expected in required.items())
    if not directional_pass:
        raise RuntimeError("Development replay directional sanity failed.")
    result = {
        "schema_version": "eest_ac_dev_oracle_replay.v0_2_3",
        "status": "pass",
        "zero_model_generation_calls": 0,
        "development_contaminated": True,
        "held_out_eligible": False,
        "contributes_to_pass_metrics": False,
        "source_corpora": [
            {"path": str(v1_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"), "sha256": _hash(v1_path)},
            {"path": str(v2_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"), "sha256": _hash(v2_path)},
        ],
        "rows": rows,
        "directional_requirements": required,
        "directional_pass": directional_pass,
        "decision_counts": {
            key: sum(row["oracle"]["decision"] == key for row in rows)
            for key in ("accept", "reject", "uncertain")
        },
    }
    _write(args.output, result)
    print(json.dumps({
        "status": "pass",
        "rows": len(rows),
        "decision_counts": result["decision_counts"],
        "held_out_eligible": False,
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
