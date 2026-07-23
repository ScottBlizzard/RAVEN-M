# RAVEN-M experiment protocol v1 — pre-freeze draft

Status: `draft_pending_G4_G7`
Scored Hard runs permitted: **no**

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
- Primary effect: paired absolute TSR difference M0 minus B3.
- Secondary: M0 minus B0; steps, calls, tokens, wall time, loops,
  premature completion, recovery, stale-memory use, and memory-induced errors.
- Ablation subset: H01, H03, H04, H06, H09, H12, H14, H16 at two seeds.

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

Transport retries reuse the identical payload and idempotency key, at most two
attempts. A schema failure permits exactly one model repair and counts both
calls. The evaluator is never queried mid-episode.

## Statistics

Report numerator and denominator for every TSR. Use paired task-instance
outcomes, clustered bootstrap resampling of task IDs with seeds retained inside
each sampled cluster, Wilson intervals for individual proportions, and exact
McNemar tests as secondary paired tests. Report point estimates and 95%
intervals without upgrading exploratory low-power results to universal claims.

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
