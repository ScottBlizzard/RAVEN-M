# Protocol-v2.2 r56 Gate-F preflight

Date: 2026-07-31  
Decision: **passed; Batch 1 prepared but not started**

## Frozen identities

- Method source: `24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`
- Method tag: `protocol-v2-2-gate-e-r56`
- Gate-F execution commit:
  `693a4b6ac967cbf2beeb8b59d29d20b93b53f5df`
- Gate-F execution tag: `protocol-v2-2-gate-f-r56-preflight`
- Protocol: `androidworld_protocol_v2_2_exploratory`
- Suite: `hard_micro_v2_2_seed20260730_r56`
- Model: `Qwen/Qwen3-VL-32B-Instruct`
- Model revision:
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`

## Compatibility decision

The legacy Gate-F runner was not safe to launch unchanged. It treated every
protocol-v2 guard validation block as a loop-recovery obligation, but r56 also
uses validation blocks for expected input-focus, field-role, exact-target,
and consequential-action checks. A correct r56 trajectory could therefore
have been falsely rejected.

The compatibility layer preserves the original Hard experiment exactly:
six task families, twelve B3/M0 cells, seed `20260730`, blocked order,
three four-cell batches, native step budgets, prompts, schemas, acceptance
thresholds, and the 3.5-hour cumulative cap are unchanged. Only startup,
failure typing, protocol-v2.2 controller wiring, and semantic evidence
accounting were brought forward from the r56 Gate-E runner.

The r56 loop criterion now uses the per-episode semantic-progress audit:
every executed step must contain semantic before/after evidence, a previously
blocked unchanged-screen action may not execute, and no bounded guard repair
may remain unresolved. Raw validation/recovery counters remain in the result
as diagnostics.

## Validation

- Complete local suite: **411/411 passed**.
- New and legacy Gate-F tests: **15/15 passed**.
- Protocol-v1 breadth seal: **197/197 files**, zero failures.
- Python compilation and `git diff --check`: passed.
- The legacy runner's original nine tests remained green.

## Live zero-call preflight

The preflight completed at `2026-07-31T08:47:10.299478+00:00`.

- Gate-E prerequisite report: exact SHA-256 match and Gate-E pass for the
  same method source.
- Frozen execution and method files: **28/28 matched**.
- Hard task families: **6/6 registered**.
- Restart-stable task instances: **6/6**.
- B3/M0 goal-and-parameter pair hashes: **6/6 identical**.
- Exact model backend and revision: healthy and loaded.
- AndroidWorld emulator: connected.
- Formal scored suite directory: absent before and after preflight.
- Model calls: **0**.
- GPU experiment cells: **0**.
- Automatic Batch-1 launch: **false**.
- Automatic next-batch transition: **false**.
- Automatic Gate-G transition: **false**.

The machine-readable evidence is
`reports/protocol_v2_2_r56_gate_f_preflight.json` with SHA-256
`267df032ba194ae70b599058b0768b3199bec3abaf378bd38dbedf2a44cad92f`.

## Frozen Batch 1

Batch 1 contains exactly four cells:

1. H01 `BrowserMultiply`, B3, 22 steps;
2. H17 `SportsTrackerActivitiesOnDate`, M0, 20 steps;
3. H03 `ExpenseAddMultipleFromMarkor`, B3, 60 steps; and
4. H16 `SimpleCalendarAddOneEvent`, M0, 34 steps.

Starting Batch 1 requires a separate explicit user request. Its completion
will produce a checkpoint and stop. No result can authorize Batch 2
automatically.

## Evidence boundary

This preflight demonstrates that the exact r56 method and Gate-F execution
layer are internally consistent and ready for one bounded Hard batch. It is
not a Hard-task result, does not add a scored cell, and is not evidence that
M0 outperforms B3.
