from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
REPORT = (
    ROOT / "reports/protocol_v2_2_r66_h17_candidate_preflight.json"
)
REPORT_SHA256 = (
    "ecbe677cad372d0c8c6ef4f8316d7488ec7993242d1f11c7911280cea8af4f01"
)


def payload() -> dict:
    assert sha256(REPORT.read_bytes()).hexdigest() == REPORT_SHA256
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_r66_h17_preflight_is_byte_frozen_and_zero_call() -> None:
    report = payload()
    assert report["passed"] is True
    assert report["model_calls"] == 0
    assert report["gpu_experiment_cells"] == 0
    assert report["automatic_batch_1_launch"] is False
    assert report["automatic_next_batch"] is False
    assert report["automatic_gate_g_transition"] is False


def test_r66_h17_preflight_matches_exact_source_and_package() -> None:
    report = payload()
    assert report["source_commit"] == (
        "e364e727d9c31d547cf5b8805b281bc79c2be6f6"
    )
    assert report["source_tag"] == "protocol-v2-2-r66-local-candidate"
    assert report["execution_commit"] == (
        "633b29f87c640f82abc144233140b402bffeef6c"
    )
    resolved = subprocess.check_output(
        [
            "git",
            "rev-list",
            "-n",
            "1",
            "protocol-v2-2-r66-h17-candidate-package",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    assert resolved == "633b29f87c640f82abc144233140b402bffeef6c"


def test_r66_h17_preflight_freezes_all_files_and_pairs() -> None:
    report = payload()
    checks = report["manifest_audit"]["freeze_file_checks"]
    assert len(checks) == 28
    assert all(item["passed"] for item in checks)
    pairs = report["pair_hash_checks"]
    assert len(pairs) == 6
    assert all(item["passed"] for item in pairs)
    assert all(item["restart_stable"] for item in report["instance_records"])
    assert report["protocol_v1_seal"]["file_count"] == 197
    assert report["protocol_v1_seal"]["passed"] is True


def test_r66_h17_preflight_matches_exact_live_environment() -> None:
    report = payload()
    health = report["model_health"]
    assert health["status"] == "ok"
    assert health["loaded"] is True
    assert health["revision"] == (
        "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
    )
    assert health["backend"] == (
        "qwen3_vl_32b_transformers_bf16_4x4090_v1"
    )
    assert report["emulator_connected"] is True


def test_r66_h17_preflight_recorded_fresh_suite_absence() -> None:
    assert payload()["fresh_suite_directory_absent"] is True
