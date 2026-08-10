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
- The controller stores one compact state. It adds only whether the executed action caused an observable pixel/activity/UI-tree transition. Observable transition is not task success.
- The structured prefix is stored once in A2 memory and removed from ordinary action-history prose. The imperative remains in the official action history.
- Memory is episode-local and cannot read hidden evaluator state or cross-episode data.

## Separately audited cost guard

The guard is not a memory success mechanism. It is allowed to save runtime only.

- State key: a coarse perceptual signature of the same screenshot supplied to the model. Hidden activity and UI-tree records remain audit-only and never control the guard.
- Action key: action type and conservative coordinate/text signature.
- The first two equivalent executions on the same state are allowed.
- Only when both produce no observable change may the next equivalent proposal be blocked.
- The model receives a visible warning and may choose another route on its next normal call.
- Two consecutive ignored block warnings end interaction as `a2_cost_guard_stop` and invoke the normal hidden evaluator. The evaluator remains the final label; a resulting success cannot be credited to the guard.
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
