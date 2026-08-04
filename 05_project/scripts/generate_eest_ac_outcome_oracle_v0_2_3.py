"""Generate the v0.2.3 held-out trace schema from the single contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.outcome_oracle_v0_2_3 import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    build_trace_schema,
    load_contract,
)


def main() -> None:
    schema = build_trace_schema(load_contract())
    DEFAULT_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SCHEMA_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "generated", "schema": str(DEFAULT_SCHEMA_PATH)}, indent=2))


if __name__ == "__main__":
    main()
