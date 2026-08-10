"""Zero-generation preflight for the official Qwen Mobile Agent arm."""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.protocol import (  # noqa: E402
    OFFICIAL_QWEN_COMMIT,
    OFFICIAL_SYSTEM_PROMPT,
    build_user_prompt,
    parse_official_response,
)


EXPECTED_MODEL_MANIFEST_SHA256 = (
    "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
)
EXPECTED_OFFICIAL_SHARD13_SHA256 = (
    "b64f2289871261fdd1abbd3b78bcd66011b341de3dc8eeb2ed1a473ee7c8d95c"
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument(
        "--qwen-repo",
        type=Path,
        default=Path("/root/autodl-tmp/Qwen3-VL"),
    )
    parser.add_argument("--sha256-manifest", type=Path)
    args = parser.parse_args()

    required = ["config.json", "generation_config.json", "preprocessor_config.json"]
    missing = [name for name in required if not (args.model_dir / name).is_file()]
    shards = sorted(args.model_dir.glob("*.safetensors"))
    if missing or len(shards) != 14:
        raise RuntimeError(
            f"model preflight failed: missing={missing}, safetensor_shards={len(shards)}"
        )
    config = json.loads((args.model_dir / "config.json").read_text(encoding="utf-8"))
    generation_config = json.loads(
        (args.model_dir / "generation_config.json").read_text(encoding="utf-8")
    )
    expected_generation = {
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "repetition_penalty": 1.0,
    }
    actual_generation = {
        key: generation_config.get(key) for key in expected_generation
    }
    if actual_generation != expected_generation:
        raise RuntimeError(
            "model generation config drift: "
            f"{actual_generation!r} != {expected_generation!r}"
        )

    qwen_commit = subprocess.check_output(
        ["git", "-C", str(args.qwen_repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if qwen_commit != OFFICIAL_QWEN_COMMIT:
        raise RuntimeError(
            f"Qwen repository drift: {qwen_commit} != {OFFICIAL_QWEN_COMMIT}"
        )
    notebook_path = args.qwen_repo / "cookbooks" / "mobile_agent.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    official_notebook_prompt: str | None = None
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        try:
            tree = ast.parse("".join(cell.get("source", [])))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(
                isinstance(target, ast.Name) and target.id == "system_prompt"
                for target in node.targets
            ):
                official_notebook_prompt = ast.literal_eval(node.value)
                break
        if official_notebook_prompt is not None:
            break
    if official_notebook_prompt != OFFICIAL_SYSTEM_PROMPT:
        raise RuntimeError("transcribed system prompt differs from the frozen notebook")

    manifest_path = args.sha256_manifest or args.model_dir.with_suffix(".sha256")
    manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    hashes: dict[str, str] = {}
    for line in manifest_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise RuntimeError(f"invalid SHA-256 manifest line: {line!r}")
        hashes[match.group(2)] = match.group(1)
    expected_shard_names = {item.name for item in shards}
    if not expected_shard_names.issubset(hashes):
        raise RuntimeError("SHA-256 manifest does not cover every model shard")
    manifest_sha256 = sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_sha256 != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError(
            "frozen model manifest drift: "
            f"{manifest_sha256} != {EXPECTED_MODEL_MANIFEST_SHA256}"
        )
    if (
        hashes.get("model-00013-of-00014.safetensors")
        != EXPECTED_OFFICIAL_SHARD13_SHA256
    ):
        raise RuntimeError("the frozen cross-source weight-shard anchor drifted")
    model_files = sorted(
        item for item in args.model_dir.iterdir() if item.is_file()
    )
    actual_names = {item.name for item in model_files}
    if not set(hashes).issubset(actual_names):
        raise RuntimeError(
            "model manifest/file-set drift: "
            f"missing_from_disk={sorted(set(hashes) - actual_names)!r}, "
            f"unmanifested={sorted(actual_names - set(hashes))!r}"
        )
    actual_files: list[dict[str, object]] = []
    for model_file in model_files:
        actual_hash = file_sha256(model_file)
        if actual_hash != hashes[model_file.name]:
            raise RuntimeError(
                f"model file hash mismatch: {model_file.name}: "
                f"{actual_hash} != {hashes[model_file.name]}"
            )
        actual_files.append(
            {
                "name": model_file.name,
                "bytes": model_file.stat().st_size,
                "sha256": actual_hash,
                "realpath": str(model_file.resolve()),
            }
        )
    raw = (
        "Thought: inspect.\nAction: Tap the control.\n<tool_call>\n"
        '{"name":"mobile_use","arguments":{"action":"click","coordinate":[999,0]}}'
        "\n</tool_call>"
    )
    decision = parse_official_response(raw)
    if decision.canonical_action != {"type": "tap", "x": 1.0, "y": 0.0}:
        raise RuntimeError("official coordinate adapter self-test failed")
    prompt = build_user_prompt("test", [])
    record = {
        "status": "pass",
        "generation_calls": 0,
        "model_dir": str(args.model_dir.resolve()),
        "model_type": config.get("model_type"),
        "safetensor_shard_count": len(shards),
        "safetensor_total_bytes": sum(item.stat().st_size for item in shards),
        "official_qwen_commit": qwen_commit,
        "official_system_prompt_sha256": sha256(OFFICIAL_SYSTEM_PROMPT.encode()).hexdigest(),
        "official_user_template_sha256": sha256(prompt.encode()).hexdigest(),
        "model_config_sha256": sha256(
            (args.model_dir / "config.json").read_bytes()
        ).hexdigest(),
        "model_generation_config": actual_generation,
        "model_sha256_manifest": str(manifest_path.resolve()),
        "model_sha256_manifest_sha256": manifest_sha256,
        "model_file_count": len(actual_files),
        "model_total_bytes": sum(int(item["bytes"]) for item in actual_files),
        "model_files": actual_files,
        "unmanifested_ancillary_files": sorted(actual_names - set(hashes)),
        "official_hf_shard13_sha256_anchor": EXPECTED_OFFICIAL_SHARD13_SHA256,
    }
    print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
