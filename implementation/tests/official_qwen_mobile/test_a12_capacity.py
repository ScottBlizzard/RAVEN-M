from __future__ import annotations

import json
import tracemalloc

import numpy as np

from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (
    ActionFailureRecord,
    ActiveScreenContext,
    DeliveredFailureSignature,
    MinimalActionDivergenceMemory,
    PostReadWatch,
    ReadEvent,
    canonical_action_family,
    describe_visual_state,
    render_action_label,
    render_memory,
)


def test_maximum_simultaneous_state_is_bounded() -> None:
    pixels = np.zeros((25, 40, 3), dtype=np.uint8)
    descriptor = describe_visual_state(pixels)
    tracemalloc.start(); before, _ = tracemalloc.get_traced_memory()
    memory = MinimalActionDivergenceMemory()
    memory.goal_sha256 = "g" * 64
    memory.active_context = ActiveScreenContext("context", descriptor, 0, 20, 19, 6)
    families = [canonical_action_family({"type": "tap", "x": (index + .1) / 12, "y": (index * 2 + .1) / 24}) for index in range(8)]
    for index, family in enumerate(families):
        key = f"{index:064x}"
        label = render_action_label(family)
        memory.failure_records[key] = ActionFailureRecord(
            f"record-{index}", "context", family, key, label,
            "READY" if index == 0 else "SEEN_ONCE", 2 if index == 0 else 1,
            index, index, index if index == 0 else None,
            "a" * 64, "b" * 64, "c" * 64 if index == 0 else None,
            "d" * 64 if index == 0 else None, .001,
            .001 if index == 0 else None, "e" * 64,
            "f" * 64 if index == 0 else None,
            index if index == 0 else None, index + 1 if index == 0 else None,
            index + 1 if index == 0 else None, "s" * 64 if index == 0 else None,
            None,
        )
    longest = render_memory("long-press cell 12/12,24/24 (medium)")
    for index in range(5):
        family = ("press_back",)
        signature = f"{index + 10:064x}"
        memory.delivered_failures.append(DeliveredFailureSignature(f"delivered-{index}", descriptor, family, signature, signature, index))
        event = ReadEvent(
            f"read-{index}", index, f"record-{index}", "READY", index,
            index, "EXACT", 0.0, 2, [index, index + 1], family, signature,
            "press Back", signature, True, True, longest,
            f"{index + 20:064x}", len(longest), len(longest.encode()), 100,
        )
        memory.read_events.append(event)
        memory.post_read_watches.append(PostReadWatch(f"watch-{index}", event.read_id, index, descriptor, family))
    memory.descriptor_cache = [("x", descriptor), ("y", descriptor)]
    memory.max_observed_failure_record_count = 8
    memory.max_rendered_chars = len(longest)
    memory.max_rendered_utf8_bytes = len(longest.encode())
    memory.max_rendered_tokens = 100
    current, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    audit = memory.audit_record()
    payload = json.dumps(audit, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    assert len(memory.failure_records) == 8
    assert sum(record.state == "READY" for record in memory.failure_records.values()) == 1
    assert len(memory.delivered_failures) == len(memory.read_events) == len(memory.post_read_watches) == 5
    assert len(memory.descriptor_cache) == 2
    assert len(payload) <= 131072
    assert peak - before <= 2 * 1024 * 1024
