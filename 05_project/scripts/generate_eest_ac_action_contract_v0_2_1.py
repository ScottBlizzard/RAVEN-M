"""Generate/check EEST-AC v0.2.1 schema and prompt from one contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_contract_v0_2_1 import (  # noqa: E402
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    build_decision_schema,
    load_contract,
    render_executor_prompt,
)


def _render() -> dict[Path, str]:
    contract = load_contract()
    return {
        DEFAULT_SCHEMA_PATH: json.dumps(
            build_decision_schema(contract),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        DEFAULT_PROMPT_PATH: render_executor_prompt(contract),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = _render()
    if args.write:
        for path, text in rendered.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        print(json.dumps({"status": "written", "paths": [str(path) for path in rendered]}, indent=2))
        return
    drift = []
    for path, expected in rendered.items():
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        if actual != expected:
            drift.append(str(path))
    if drift:
        raise RuntimeError(f"Generated action-contract artifacts drifted: {drift}")
    print(json.dumps({"status": "pass", "checked": [str(path) for path in rendered]}, indent=2))


if __name__ == "__main__":
    main()
