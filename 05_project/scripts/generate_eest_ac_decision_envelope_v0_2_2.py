"""Generate v0.2.2 prompt/schema artifacts from the authoritative envelope."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_contract_v0_2_2 import (  # noqa: E402
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    build_decision_schema,
    load_contract,
    render_executor_prompt,
)


def main() -> None:
    contract = load_contract()
    DEFAULT_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SCHEMA_PATH.write_text(
        json.dumps(build_decision_schema(contract), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    DEFAULT_PROMPT_PATH.write_text(render_executor_prompt(contract), encoding="utf-8")
    print(json.dumps({
        "status": "generated",
        "schema": str(DEFAULT_SCHEMA_PATH),
        "prompt": str(DEFAULT_PROMPT_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
