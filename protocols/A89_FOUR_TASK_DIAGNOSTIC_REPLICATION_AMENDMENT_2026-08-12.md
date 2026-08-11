# A8-v2/A9 Four-Task Diagnostic Replication Amendment — 2026-08-12

## Purpose

The original prospective A8-v2 and A9 suites remain terminal scientific gate
failures. They are not resumed, deleted, relabelled, or overwritten. This
amendment authorizes one fresh diagnostic replication per arm over all four
tasks that A0 solved at task seed `20260806`.

The purpose is descriptive: obtain a complete four-task profile even when an
early task fails. The replication cannot repair the original gate, cannot be
used as a pristine prospective claim, and cannot release the remaining fifteen
Hard tasks.

## Frozen comparison

- Arms: `a8v2` and `a9`, run sequentially on one emulator.
- Task seed `20260806`; generation seed `3407`.
- Model, revision, vLLM BF16 backend, sampling, official system prompt,
  screenshot-only observation, native step limits, action protocol and
  evaluator are unchanged from A0 and the original A8-v2/A9 suites.
- Memory mechanisms are byte-identical to the source-frozen implementations.
  This amendment changes only scheduling and claim status.
- Extra model calls, hidden UI input, evaluator input, guard, action override,
  planner, critic and verifier are forbidden.

## Schedule

Each fresh suite runs exactly these seed-`20260806` instances in order:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

Reward failure is nonblocking diagnostic data. An infrastructure-invalid
episode stops the suite and may be resumed only under the same-task
infrastructure policy. A scientifically valid failed episode is not rerun
within the same diagnostic suite.

## Evidence and claim boundary

The runner records `diagnostic=true`, `remaining_15_released=false`,
`reward_fail_fast=false`, and the claim boundary
`diagnostic_replication_only_not_gate_repair_not_full19_release_original_terminal_gate_suites_remain_authoritative`.

The original terminal suites remain first-run prospective evidence. The new
four-task aggregate becomes the current descriptive diagnostic table, not a
replacement for provenance. Any report must show both.

## Interpretation rule

The replication can support statements about observed association, such as
frequent memory exposure coinciding with repeated ineffective actions. It
cannot by itself prove causality. A claim that a standalone memory layer is
insufficient must be presented as a mechanism hypothesis supported by
activation timing, prompt divergence, action repetition and evaluator outcome.
