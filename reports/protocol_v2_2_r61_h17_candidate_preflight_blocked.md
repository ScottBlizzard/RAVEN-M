# Protocol v2.2 r61 H17 Candidate Preflight Block

## Decision

**Blocked online, before any model call or experiment cell.** The r61 H17/M0
candidate package is statically complete and frozen at
`1af8d1ca4c724f54e4c45501fa5df556a14ed322`, but the zero-call preflight cannot
verify the model endpoint while MotionPro is disconnected.

## What passed

- Complete project tests: **478/478**
- Candidate-package tests: **11/11**
- Exact source freeze: **28/28** files reproduced from `baa398b`
- Frozen schedule: 12 cells, 6 task pairs, 3 batches
- Gate-E prerequisite, r60 formal-stop prerequisite, and r61 local-validation
  prerequisite: exact and valid
- Protocol-v1 breadth seal: **197/197**
- Python compilation and `git diff --check`: passed
- Emulator: `emulator-5554 device`

The wrapper rejects formal `--batch` launches and every live development
sequence except sequence 2, the frozen H17/M0 cell.

## Exact block

The official wrapper reached its model-health check and received
`WinError 10061` from `127.0.0.1:18000`. An independent SSH probe to
`10.10.217.244:22` timed out after ten seconds, and the MotionPro window showed
`已断开`. A single tunnel watchdog remains running and retrying.

No successful-preflight report or r61 suite directory was created. Model calls,
GPU experiment cells, formal scored cells, and development cells all remain
zero.

## Resume boundary

After the VPN route returns, rerun the same zero-call preflight. It must verify
the exact Qwen3-VL backend and revision and write a success report before the
single isolated, non-scored H17/M0 smoke can start. No formal r61 Gate-F batch
is authorized.

Machine-readable evidence:
`reports/protocol_v2_2_r61_h17_candidate_preflight_blocked.json`.
