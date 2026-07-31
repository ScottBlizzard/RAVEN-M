# Protocol v2.2 r59 Local Validation

## Decision

**PASS locally.** r59 may advance to exact-source wrapper preparation and a
zero-model-call H01 preflight. This report does not authorize a live smoke or
any formal Gate-F cell.

Candidate source:

- commit: `868c1ffa39c6d1415f3b3831ed295e61672c87af`
- tag: `protocol-v2-2-r59-local-candidate`
- tag resolves exactly to the candidate commit

## What r59 changes

r58 proved that the delayed-DOM reconciliation and repeated-tap exception work:
the five requested taps executed, their visible values were `2, 3, 9, 10, 10`,
and a sixth target tap was denied. The episode still failed because the lossy
summary retained only the first value and incorrectly told the planner that four
more taps remained.

r59 adds a narrow verified repeat-progress ledger. It advances only after an
eligible task-bound tap actually executes and the resulting observation contains
exactly one visible pure numeric result in the same application. Equal values
remain distinct ordinal observations. The ledger is injected on every planning
step and explicitly outranks conflicting summary memory. Once the requested
count is complete, another target tap is rejected with a specialized repair;
the product is emitted only after every operand is verified.

This is evidence reconciliation, not a task solver: the ledger neither invents
actions nor infers unobserved values.

## Validation result

- Complete project tests: **439/439**
- Focused guard/controller tests: **126/126**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Historical r56, r57, and r58 execution-freeze tests: passed
- Real model health: `ok`, exact Qwen3-VL revision/backend matched
- Emulator: `device`, cold boot completed
- Real model calls: 0
- GPU experiment cells: 0

The local ADB daemon, project AVD, SSH model tunnel, and tunnel watchdog were
restored before the live zero-call health check. No model call or experiment
cell was consumed during recovery.

## Boundary

The next safe action is to prepare an r59-specific wrapper and manifest, freeze
the exact source hashes, and run a zero-call preflight. A single non-scored
H01/B3 smoke may be considered only after that preflight passes. r58 remains an
immutable failed non-scored result; no formal Gate-F run is authorized.

Machine-readable evidence:
`reports/protocol_v2_2_r59_local_validation.json`.

