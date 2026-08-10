"""Zero-generation replay of the corrected A2-v1r1 guard over raw A1 traces."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from raven_m.official_qwen_mobile.progress_memory import RepeatedNoProgressGuard


def _snapshot(record: dict, shape: list[int]) -> dict:
    return {
        "pixel_sha256": record["pixel_sha256"],
        "pixel_shape": shape,
        "pixel_dtype": "|u1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a1-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.a1_root.resolve()
    episodes = []
    successful_hypothetical_blocks = []
    for episode_path in sorted((root / "episodes").glob("*/episode.json")):
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        if int(episode["seed"]) != 20260806:
            continue
        guard = RepeatedNoProgressGuard()
        blocks = []
        directory = episode_path.parent
        for step in episode.get("steps") or []:
            mapped = step.get("mapped_action")
            after_record = step.get("after")
            if not step.get("executed") or not mapped or not after_record:
                continue
            before = _snapshot(step["before"], step["transition"]["before_shape"])
            assessment = guard.assess(before=before, mapped_action=mapped)
            if assessment["blocked"]:
                blocks.append({"step": int(step["step"]), **assessment})
            after = _snapshot(after_record, step["transition"]["after_shape"])
            guard.observe(before=before, after=after, mapped_action=mapped, transition=step["transition"])
        record = {"task_name": episode["task_name"], "episode_id": episode["episode_id"], "success": episode["success"], "hypothetical_blocks": blocks}
        episodes.append(record)
        if episode["success"] and blocks:
            successful_hypothetical_blocks.append(record)
    if len(episodes) != 19:
        raise RuntimeError(f"expected 19 A1 episodes, found {len(episodes)}")
    payload = {
        "schema": "a2_v1r1_exact_guard_a1_replay_v1",
        "generation_calls": 0,
        "a1_root": str(root),
        "episode_count": len(episodes),
        "hypothetical_block_episode_count": sum(int(bool(item["hypothetical_blocks"])) for item in episodes),
        "successful_episode_hypothetical_block_count": len(successful_hypothetical_blocks),
        "qualification_pass": not successful_hypothetical_blocks,
        "successful_episode_hypothetical_blocks": successful_hypothetical_blocks,
        "episodes": episodes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "sha256": sha256(args.output.read_bytes()).hexdigest(), "qualification_pass": payload["qualification_pass"], "hypothetical_block_episode_count": payload["hypothetical_block_episode_count"]}, indent=2))
    if not payload["qualification_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
