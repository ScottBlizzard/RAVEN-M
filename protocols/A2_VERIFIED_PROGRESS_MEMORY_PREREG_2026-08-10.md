# A2 Verified Progress Memory — Frozen Preregistration

Date frozen: 2026-08-10, before any A2 generation call.

## Question

Can a smaller, outcome-aware episode memory improve the official Qwen3-VL-32B AndroidWorld Hard arm beyond A1 while reducing A1's large token and runtime overhead?

## Why A2 follows A1

A1 improved full success from 4/19 to 5/19, but increased steps from 329 to 603 and tokens from 1,273,361 to 3,464,267. Its six raw records also repeated the same structured payload inside ordinary action history. Three long failed episodes account for roughly 71% of the extra steps. A2 therefore changes only the representation and use of progress memory needed to address these observed weaknesses.

## Frozen arm

- Model, revision, decoding, backend, 19 task instances, seed 20260806, task order, native step budgets, screenshot-only observation, evaluator, and action protocol are identical to A0/A1.
- One ordinary model call per step; no planner, critic, retrieval model, or repair call.
- The model writes `PROGRESS[observed=...; verified=...; pending=...; expected=...]` in its Action sentence.
- The controller stores one compact state. `verified` is explicitly a model-authored assertion that a requirement is screenshot-visible, not a controller/evaluator confirmation. It adds a three-way outcome from the model-visible pixels only: exact no change, material visible change, or minor/ambiguous visible change. Hidden activity/UI-tree evidence is audit-only and cannot affect memory or guard decisions.
- The structured prefix is stored once in A2 memory and removed from ordinary action-history prose. The imperative remains in the official action history.
- Memory is episode-local and cannot read hidden evaluator state or cross-episode data.

## Separately audited cost guard

The guard is not a memory success mechanism. It is allowed to save runtime only.

- State key: an exact domain-separated hash of the full model-visible pixel array, including shape and dtype. Missing exact pixels is an infrastructure error in a scored run.
- Action key: the exact mapped physical tap, long-press, or swipe, including integer pixel coordinates and duration. Text, wait, key, app-open, answer, and terminate actions are never guard-eligible.
- Action key: action type and conservative coordinate/text signature.
- The first two equivalent executions on the same state are allowed.
- Only when both executions yield byte-identical before/after screenshots may the third exact proposal be blocked.
- The first and second blocked proposals deliver warning 1 and warning 2 through ordinary history only; there is no pre-proposal warning and no warning inside the memory block.
- Repeating the exact proposal after warning 2 produces block 3 and ends interaction as `a2_cost_guard_stop`; the normal hidden evaluator remains the only success authority.
- Every assessment, no-progress observation, block, and cost stop is logged separately from memory read/write.

## Frozen hypotheses and decision rules

Primary accuracy target: A2 must exceed A1's 5/19 full successes to claim an accuracy improvement.

Primary cost target: A2 must use fewer total tokens and less wall-clock time than A1. Step count, model calls, prompt tokens per call, and completion tokens are reported as secondary cost measures.

Attribution rules:

1. A task-level gain can be attributed to memory only if a nonempty A2 read precedes a changed useful decision and the stored visible evidence is relevant to that decision.
2. A task affected only by a guard block cannot establish that memory improved success.
3. A guard benefit may be reported only as avoided repeated execution/cost, never as a success.
4. Evaluator reward remains the only final success label.
5. One seed is a paired diagnostic, not a generalization claim.

If either primary target fails, the result remains a valid frozen negative result. No threshold or prompt tuning after seeing A2 outcomes may be relabeled as this A2 run.

## Stop and validity rules

- Before GPU use, the zero-generation preflight and source freeze must pass.
- The first valid task must show a successful memory write followed by a nonempty read; otherwise stop before task 2.
- Controller, transport, reset, teardown, or missing-evaluator errors invalidate the current task and stop the suite. Resume reruns only that invalid task.
- Model parse errors, wrong actions, guard cost stops, max-step exhaustion, and evaluator outcomes remain scientific records rather than infrastructure-invalid attempts.

## Required outputs

Per step: request/response audit, screenshot and UI audit hashes, L0–L5 layers, parsed/executed action, transition evidence, memory read/write, and cost-guard records.

Per suite: paired task table against A0/A1; successes; partial rewards; steps; calls; tokens; wall time; memory activation; guard triggers/blocks/stops; and qualitative trace attribution for every gain or loss.

## A2-v1r1 qualification amendment (frozen before scored generation)

- Experiment ID: `A2_VERIFIED_PROGRESS_MEMORY_QWEN3VL32B_AW_HARD_S20260806_V1R1`.
- Memory ID: `a2_verified_progress_memory_v1r1`; guard ID: `a2_repeated_no_progress_cost_guard_v1r1`.
- Scored HTTP transport makes exactly one request attempt. Timeout or connection failure is infrastructure-invalid because remote token consumption is unknowable.
- The frozen A0/A1 ledger, corrected A1 guard replay, model-file receipt, AndroidWorld/emulator receipt, live server launch receipt, source freeze, exact ordered 19-task digest, ports, timeout, and model manifest are bound into the run signature.
- Checkpoints contain immutable episode references and hashes, never embedded mutable summaries. Resume revalidates every reference and excludes/reports orphan directories.
- A completed suite requires exactly the 19 ordered unique keys, one transport attempt per call, non-null evaluator results, no episode/suite lifecycle errors, no invalid attempts, and matching run signatures.
- A2-v1r1 is reported as a compound package (one-state outcome-aware memory, history deduplication, and separately logged guard). Trace exposure is not counterfactual component causality.
