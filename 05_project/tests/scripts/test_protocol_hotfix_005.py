from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import apply_pairing_hash_hotfix_005 as hotfix  # noqa: E402


def test_runtime_object_addresses_are_normalized_recursively() -> None:
    raw = {
        "image": {
            "_im": "<ImagingCore object at 0x000001EE9710D550>",
            "label": "keep 0x1234 in ordinary text",
        }
    }
    normalized = hotfix.normalize_runtime_object_reprs(raw)
    assert raw["image"]["_im"].endswith("D550>")
    assert normalized == {
        "image": {
            "_im": "<ImagingCore object>",
            "label": "keep 0x1234 in ordinary text",
        }
    }


def test_semantically_identical_pil_params_have_same_hash() -> None:
    first = {
        "file_name": "receipt.jpg",
        "receipt_image": {
            "_im": "<ImagingCore object at 0x0000011111111111>",
            "_mode": "RGB",
            "_size": [500, 500],
        },
    }
    second = {
        "file_name": "receipt.jpg",
        "receipt_image": {
            "_im": "<ImagingCore object at 0x0000022222222222>",
            "_mode": "RGB",
            "_size": [500, 500],
        },
    }
    assert hotfix.canonical_params_sha256(first) == (
        hotfix.canonical_params_sha256(second)
    )


def test_repair_is_scoped_and_preserves_prior_hash(monkeypatch) -> None:
    monkeypatch.setattr(
        hotfix,
        "amendment_result_identity",
        lambda: {"amendment_id": hotfix.AMENDMENT_ID},
    )
    affected = {
        "pair_id": hotfix.EXPECTED_PAIR_ID,
        "task_params": {
            "_im": "<ImagingCore object at 0x0000011111111111>"
        },
        "params_sha256": "old",
        "protocol_amendments": [],
    }
    repaired, changed = hotfix.repair_result(affected)
    assert changed
    assert affected["params_sha256"] == "old"
    assert repaired["params_sha256_before_hotfix_005"] == "old"
    assert repaired["params_sha256"] != "old"
    assert repaired["protocol_amendments"] == [
        {"amendment_id": hotfix.AMENDMENT_ID}
    ]

    unrelated = {**affected, "pair_id": "H01-s20260720"}
    same, changed = hotfix.repair_result(unrelated)
    assert not changed
    assert same is unrelated
