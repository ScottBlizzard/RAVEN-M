# RAVEN-M experiment protocol v1 — frozen

Status: `frozen`
Scored Hard runs permitted: **yes, only under protocol-v1**

## Fixed benchmark and model

- AndroidWorld commit:
  `3e50888527ef9f29b9157ecd537e408008bb1c85`
- Operational Hard definition: all 19 task classes whose frozen official
  task-list row has `difficulty=hard`.
- Task-list snapshot SHA-256:
  `34e72b16bc2d09bbe0634ec9db8ab8709447593ee02bc6b3e5682a8e7f425d7f`
- Model: exact `Qwen/Qwen3-VL-32B-Instruct` revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`; GPUs 0–3;
  Transformers BF16; SDPA; deterministic generation.
- Total context cap: 8192; maximum new tokens: 256.

## Task instances and budgets

The task manifest is
`05_project/configs/task_manifests/androidworld_hard_v1.json`. The three paired
instance seeds are 20260720, 20260721, and 20260722. Python and NumPy are seeded
immediately before task parameter generation; the generated natural-language
goal and JSON-safe parameters are persisted for every variant.

The native AndroidWorld budget is `int(10 * task.complexity)`, as implemented
by the frozen `android_world.suite_utils._allocate_step_budget`. It is fixed per
task and shared by all variants. Optimal steps are used only for stratification.

## Variants and primary comparisons

- Breadth seed: B0, B1, B2, B3, and M0 on all 19 tasks.
- Confirmatory seeds: B0, B3, and M0 on all 19 tasks and all three seeds.
- Strict control: S0 on all 19 tasks at the breadth seed, plus the frozen
  eight-task subset at seed 20260721.
- Ablations on the frozen eight-task subset at two seeds: MREL, MNO_WM,
  MNO_VEL, MNO_FRM, MNO_PSI, and MNO_CRITIC.
- Budget controls on the same paired subset: B3_CTX and B3_CALL.
- Primary effect: paired absolute TSR difference M0 minus B3.
- Secondary: M0 minus B0; steps, calls, tokens, wall time, loops,
  premature completion, recovery, stale-memory use, and memory-induced errors.
- Ablation subset: H01, H03, H04, H06, H09, H12, H14, H16 at two seeds.

The materialized blocked schedule contains 364 unique episodes: 95 breadth,
114 additional confirmatory, 19 full-set S0 controls, and 136 ablation/control
episodes. Its ordered-record hash is
`06149ad4baa5339600f1c5f6fc4f8d6c02241c7f8c22dfb54bcce7486dc443c3`.
Paired M0 results are reused for ablation comparisons and are never rerun only
to improve an estimate.

The same model, weights, backend, task instances, screenshot processing,
action adapter, system skeleton, temperature, step budget, timeout, retry
policy, context cap, evaluator, and leakage policy apply to direct comparisons.

## Reset, evaluation, and leakage

Each episode initializes from reset, waits for a stable first observation,
starts with empty episode-local history/memory, executes within frozen budgets,
calls the evaluator only after termination, tears down task state, and resets
home. No evaluator state, package/activity metadata, accessibility tree,
ground-truth task state, or prior Hard trajectory is placed in prompts.

Hard trajectories never enter cross-episode memory. Once protocol v1 is tagged,
Hard observations may be inspected for analysis but cannot change v1 prompts,
thresholds, task selection, budgets, or claims.

## Invalidity and retries

Only infrastructure failures in `failure_codebook.md` are invalid. Agent JSON
errors, wrong actions, loops, false done, model fail, and budget exhaustion
remain failures. An infrastructure-invalid seed may be retried at most twice;
all attempts remain archived.

After `INFRA_EMULATOR_LOST`, and only before an allowed identical retry, the
runner closes AndroidWorld, cold-restarts the same no-snapshot AVD, and requires
a no-LLM initialization/state smoke with the locked 116-task registry and
2400-by-1080 screen. Recovery logs and screenshots remain inside that schedule
cell. This operational recovery cannot change the variant, generated instance,
seed, prompt, payload, budget, evaluator, or success label.

Transport retries reuse the identical payload, call ID, and idempotency key, at
most two attempts. After the first connection/timeout error, the client waits
45 seconds for the operational SSH watchdog before the one permitted retry.
If both transport attempts fail and the episode is classified
`INFRA_MODEL_UNAVAILABLE`, the runner persists that invalid attempt before
waiting for the exact locked model ID, revision, and backend to become healthy.
Health polls are archived, and no new episode attempt is created during this
barrier. The frozen pipeline waits at most 21,600 seconds per barrier; a
process restart resumes from the next persisted attempt number and can never
reset or exceed the three-attempt cell cap. A different healthy model identity
is a hard protocol failure.
A schema failure permits exactly one model repair and counts both calls. The
evaluator is never queried mid-episode.

## Statistics

Report numerator and denominator for every TSR. Use paired task-instance
outcomes, clustered bootstrap resampling of task IDs with seeds retained inside
each sampled cluster, Wilson intervals for individual proportions, and exact
McNemar tests as secondary paired tests. Report point estimates and 95%
intervals without upgrading exploratory low-power results to universal claims.

## Frozen G7 retrieval-audit rubric

The deterministic seed-20260724 sample contains exactly 50 non-suppressed
non-Hard retrieval events. Review uses only the task, routed item, route,
contemporaneous decision, source-provenance screenshot, current decision
screenshot, and source metadata; the evaluator result is hidden.

- `relevant=yes` when the item applies to the current task or subgoal.
- `route_appropriate=yes` when FACT is visibly supported and current,
  HYPOTHESIS is plausible but requires verification, or ALERT correctly marks
  a conflict/failure.
- `fact_supported=yes` is required only for FACT and means its content is
  directly supported by the displayed provenance screenshot.
- `useful=yes` when the item reduces decision uncertainty or supports a
  concrete action, check, recovery, or rejection.
- `harmful=yes` when accepting the routed item could plausibly cause a wrong
  action, loop, or premature completion.
- `utility=yes` is derived, not discretionary: relevant, route-appropriate,
  and useful must all be yes; harmful must be no; and a FACT must also be
  screenshot-supported.

G7 requires every component label, exact utility consistency, zero stale FACT
routes, all role/memory invariants, and at least 40/50 utility-positive events.

## Freeze procedure

This draft becomes protocol v1 only after:

1. G4 confirms B0/B3 reproducibility and history-cap enforcement;
2. G7 confirms the frozen M0 configuration on non-Hard development tasks;
3. the protocol auditor validates all 19 registry names, native budgets,
   hashes, seeds, variant locks, and invalidity rules;
4. a preregistration JSON records hashes of every protocol, prompt, config,
   schema, runner, and source snapshot;
5. Git tag `protocol-v1` is created.

No scored Hard task may run before all five steps complete.
