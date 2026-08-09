import json

from raven_m.public_frameworks.mobileuse.logging import LayeredEventLog


def test_hash_chain_and_all_levels(tmp_path):
    path = tmp_path / "events.jsonl"
    log = LayeredEventLog(path, arm_id="arm", episode_id="episode")
    for level in ("L0", "L1", "L2", "L3", "L4", "L5"):
        log.write(level, "fixture", level_value=level)
    assert LayeredEventLog.validate(path) == []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [record["sequence"] for record in records] == list(range(6))
    assert {record["level"] for record in records} == {"L0", "L1", "L2", "L3", "L4", "L5"}


def test_tampering_is_detected(tmp_path):
    path = tmp_path / "events.jsonl"
    log = LayeredEventLog(path, arm_id="arm", episode_id="episode")
    log.write("L0", "a")
    line = json.loads(path.read_text(encoding="utf-8"))
    line["event"] = "tampered"
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    assert "digest:0" in LayeredEventLog.validate(path)
