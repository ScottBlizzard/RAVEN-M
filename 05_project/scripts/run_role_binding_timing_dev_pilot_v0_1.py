from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.models.transformers_client import (  # noqa: E402
    BACKEND_ID,
    MODEL_ID,
    MODEL_REVISION,
    TransformersClient,
)
from raven_m.role_binding_timing.dev_pilot_v0_1 import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    build_cells,
    load_dev_config,
    prompt_certificate,
    run_cell,
    summarize,
)
from raven_m.role_binding_timing.token_audit import (  # noqa: E402
    HuggingFaceChatTokenCounter,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--tokenizer-cache",
        type=Path,
        default=Path("D:/ZJU/Summer_Camp/_model_tokenizer_cache"),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-cells", type=int)
    args = parser.parse_args()

    config = load_dev_config(args.config)
    counter = HuggingFaceChatTokenCounter(
        model=config["model"]["id"],
        revision=config["model"]["revision"],
        cache_dir=args.tokenizer_cache,
        local_files_only=True,
    )
    certificates = prompt_certificate(config, counter=counter)
    cells = build_cells(config)
    if args.limit_cells is not None:
        cells = cells[: args.limit_cells]
    preflight = {
        "schema_version": "role_binding_timing.dev_pilot_preflight.v0_1",
        "config_sha256": sha256(args.config.read_bytes()).hexdigest(),
        "resolved_config_sha256": sha256(
            json.dumps(config, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "planned_cells": len(cells),
        "planned_calls": len(cells) * 2,
        "prompt_certificates": certificates,
        "all_early_late_token_differences_zero": all(
            item["absolute_total_difference"] == 0 for item in certificates
        ),
        "development_contaminated": True,
        "confirmatory_claim_allowed": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.dry_run:
        print(json.dumps(preflight, ensure_ascii=False, indent=2), flush=True)
        return 0

    client = TransformersClient(config["model"]["base_url"])
    health = client.health()
    actual = {
        "model": health.get("model"),
        "revision": health.get("revision"),
        "backend": health.get("backend"),
    }
    expected = {"model": MODEL_ID, "revision": MODEL_REVISION, "backend": BACKEND_ID}
    if actual != expected:
        raise RuntimeError(f"Model identity mismatch: {actual}")
    (args.output / "model_health.json").write_text(
        json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    records = []
    for index, cell in enumerate(cells, start=1):
        result_path = args.output / "cells" / f"{cell.cell_id}.json"
        if result_path.is_file():
            record = json.loads(result_path.read_text(encoding="utf-8"))
            print(f"[{index}/{len(cells)}] resume {cell.cell_id}", flush=True)
        else:
            print(f"[{index}/{len(cells)}] run {cell.cell_id}", flush=True)
            record = run_cell(
                cell,
                client=client,
                counter=counter,
                output_dir=args.output / "cells",
            )
            metric = record.get("metrics") or {}
            print(
                f"  valid={record['valid']} wrong={metric.get('wrong_target_first_targeting_action')} "
                f"source_as_target={metric.get('source_as_target')}",
                flush=True,
            )
        records.append(record)
    summary = summarize(records, config["gates"])
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
