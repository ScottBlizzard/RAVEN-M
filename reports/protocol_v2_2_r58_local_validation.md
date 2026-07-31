# Protocol v2.2 r58 Local Validation

## Decision

**PASS locally.** r58 may advance to exact-source wrapper preparation and a
zero-model-call H01 preflight. This report does not authorize a live smoke or
any formal Gate-F cell.

Candidate source:

- commit: `76887d8bff23f3babbc8de31b20e5fbb3ea17766`
- tag: `protocol-v2-2-r58-local-candidate`
- tag resolves exactly to the candidate commit

## What r58 changes

r58 reconciles one stale no-effect record only when a prior exact-coordinate
tap had identical immediate semantic before/after hashes, but the next fresh
pre-action semantic hash has changed. This models the exact r57 webpage trace:
the visible value temporarily disappeared and the next generated number
arrived after the immediate observation window.

The reconciliation is additionally task-bound. The tap must hit one labelled,
visible, enabled, clickable, non-editable, non-commit control, and that control
must match either an explicit repeated target label or a button role in an
application named by the task. Consequently Android's unrelated `Just once`
button is not eligible even though the task later requests five clicks.

## Validation result

- Complete project tests: **430/430**
- Focused guard/controller tests: **121/121**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Historical r56 and r57 execution-freeze tests: passed
- Real model health: `ok`, exact Qwen3-VL revision/backend matched
- Emulator: `device`
- Real model calls: 0
- GPU experiment cells: 0

The denial matrix covers no fresh semantic change, visible failure, blocked
fingerprint, unrelated app button, absent task/application anchor, ambiguous
controls, commit controls, count overflow, generic fourth taps, and A-B cycles.
Default non-v2.2 controller tests remain unchanged and pass.

## Boundary

The next safe action is to prepare an r58-specific wrapper and manifest, freeze
the exact source hashes, and run a zero-call preflight. A live H01/B3 smoke may
be considered only after that preflight passes. r57 remains an immutable failed
non-scored result; no formal Gate-F run is authorized.

Machine-readable evidence:
`reports/protocol_v2_2_r58_local_validation.json`.

