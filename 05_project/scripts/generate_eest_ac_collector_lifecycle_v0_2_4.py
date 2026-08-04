"""Generate the v0.2.4 completion schema from its machine contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.collector_lifecycle_v0_2_4 import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    build_completion_schema,
    load_contract,
)


def main() -> None:
    schema = build_completion_schema(load_contract())
    DEFAULT_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SCHEMA_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(DEFAULT_SCHEMA_PATH)


if __name__ == "__main__":
    main()
