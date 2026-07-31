# Protocol-v2.2 r60 Gate-F preflight

Date: 2026-07-31  
Decision: **passed; Batch 1 prepared but not started**

## Frozen identities

- Method source: `5ef66de358423f9940191d8dfde0e74002ccdcec`
- Method tag: `protocol-v2-2-r60-local-candidate`
- Gate-F execution commit:
  `b63b76aa2969fc97c0696642d9c7114ee5d6ab43`
- Gate-F execution tag: `protocol-v2-2-gate-f-r60-preflight`
- Suite: `hard_micro_v2_2_seed20260730_r60`
- Model: `Qwen/Qwen3-VL-32B-Instruct`
- Model revision:
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`

## Local validation

- Focused Gate-F tests: **25/25 passed**.
- Complete project suite: **456/456 passed**.
- Protocol-v1 breadth seal: **197/197 files**, zero failures.
- Python compilation and `git diff --check`: passed.

## Live zero-call preflight

The successful preflight completed at
`2026-07-31T13:26:15.516871+00:00`.

- Frozen method and execution files: **28/28 matched**.
- Immutable r56 Gate-E prerequisite: passed and exact hash matched.
- r60 candidate report: semantic prerequisite passed and exact hash matched.
- Raw r60 candidate artifacts: **13/13 matched**.
- Hard task families: **6/6 registered**.
- Restart-stable task instances: **6/6**.
- B3/M0 goal-and-parameter pairs: **6/6 identical**.
- Exact model backend and revision: healthy and loaded.
- AndroidWorld emulator: connected.
- Formal scored suite directory: absent before and after preflight.
- Model generation calls: **0**.
- GPU experiment cells: **0**.
- Automatic Batch-1 launch: **false**.
- Automatic next-batch transition: **false**.
- Automatic Gate-G transition: **false**.

The machine-readable record is
`reports/protocol_v2_2_r60_gate_f_preflight.json`, SHA-256
`01d597c54701e7fb0b78c2ed26afa4a80441004d5fdc25a45479a3145e037ddc`.
The generated full manifest has SHA-256
`35914b055620a58294475b57dbe6e00f0b1e3583fd4e5f09c3928f6f762fdf62`.

## Excluded infrastructure attempts

Two preflight invocations failed before an experiment or generation call:

1. the existing ADB daemon did not answer its server-version check; and
2. after ADB recovery, one model-health connection encountered transient
   Windows socket error 10048.

ADB was restarted without restarting the emulator. The model tunnel then
returned the exact healthy backend and revision, and the complete preflight was
rerun from the beginning. These attempts created no scored suite, episode,
checkpoint, or model output and are infrastructure diagnostics only.

## Frozen Batch 1

Batch 1 contains exactly four cells:

1. H01 `BrowserMultiply`, B3, 22 steps;
2. H17 `SportsTrackerActivitiesOnDate`, M0, 20 steps;
3. H03 `ExpenseAddMultipleFromMarkor`, B3, 60 steps; and
4. H16 `SimpleCalendarAddOneEvent`, M0, 34 steps.

Starting Batch 1 requires a separate explicit launch. Completion or an
immediate stop writes a checkpoint and never launches Batch 2 automatically.

## Evidence boundary

This preflight proves that the exact r60 method, execution layer, model,
emulator, task instances, and prerequisites are ready for one bounded formal
batch. It is not a scored Hard-task result and does not support a comparative
performance claim.
