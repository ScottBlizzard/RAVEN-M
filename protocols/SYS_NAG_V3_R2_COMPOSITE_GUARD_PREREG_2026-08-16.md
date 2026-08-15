# SYS-NAG V3: R2 + Numeric and Pending-Terminal Guards

Status: prospective, pre-live specification. This is a composite controller
system, not a claim that the A1-R2 memory itself improved.

## Identity and evidence boundary

- System: `sys_r2_numeric_and_pending_terminal_guard_v3`
- Experiment: `SYS_NAG_V3_R2_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`
- Parent evidence commit: `0c0ad59b231119f4b15c28e093da8ebbabef3967`
- Task seed 20260806; generation seed 3407; exact official Qwen3-VL-32B
  model, sampling, prompt, 19 instances, ordering, and native budgets are held.
- The parent SYS-NAG V2 validly failed RetroSavePlaylist with reward 0.5.
  Its numeric guard was silent. The model terminated one request after `wait`
  while the exact R2 text injected into that request still said that export was
  pending. V3 is a new identity; V2 is not rerun or repaired.

## Frozen system

The memory component is the exact prospective A1-R2 compact verified-pending
memory. The V2 numeric rule is unchanged: only an integer `answer` whose same
model-authored Action clause contains an additive cue and at least two explicit
durations can be corrected to their deterministic minute sum.

V3 adds one rule. After parsing a model success termination, block it if and
only if all conditions hold:

1. the exact R2 text actually transported in that same request contains a
   non-empty literal `PENDING:` line;
2. the immediately preceding executed canonical Android action was `wait`;
3. this episode has not previously blocked a termination.
4. at least one later native decision slot remains.

The rejected terminal proposal consumes its ordinary decision slot. No Android
action is executed and no auxiliary model call is made. If the guard blocks,
the system may consequently make one additional normal executor request within
the unchanged native decision budget; this guard-induced continuation call,
its tokens, and latency are reported separately and are not described as zero
extra computation. The next ordinary history
entry is exactly:

```text
TERMINAL CONSISTENCY CHECK: The exact task ledger injected for the rejected request still had a pending item, and the last executed action was only wait. Inspect the current screenshot and complete any visible confirmation before terminating.
```

The normal executor then receives the current authoritative screenshot, exact
R2 memory, and this message on its next native request. A second termination is
never blocked. The guard may not read pixels, UI trees, app/activity identity,
task name, evaluator output, reward, future state, or cross-episode evidence.

## Why this is minimal

The rule addresses one observed failure transition and adds only a one-bit
episode cap plus audit counters. It does not add OCR, a planner, critic, model
call, semantic parser, app rule, action generator, or task-specific constant.
It does not claim that `wait` means failure; it only refuses to equate waiting
with completing a still-explicit pending item without one more normal decision.

## Zero-generation gate

Before live generation, replay must prove:

- all 19 valid A1-R2 episodes are loaded;
- the committed minimal replay fixture binds each projected source episode by
  SHA-256, so a fresh clone can recompute the replay without gitignored runs;
- the numeric regression maps 165 to 180;
- the new terminal rule blocks the frozen SYS-NAG V2 Retro failure;
- it blocks zero historical A1-R2 terminal decisions;
- source freeze, identities, exact config, tests, single transport, zero extra
  calls, and runtime bounds pass.

## Live order and stopping

Run, without repetition: ExpenseDeleteMultiple2, RetroSavePlaylist,
SimpleCalendarAddOneEvent, SportsTrackerTotalDurationForCategoryThisWeek,
RecipeDeleteMultipleRecipesWithConstraint, OsmAndMarker, then the remaining 13
in frozen order. Any valid scientific failure in the first six terminates V3.
Infrastructure-invalid episodes are linked and may be replaced only under the
existing fail-closed contract. If six pass, release the remaining 13.

Report performance, cost, and mechanism evidence separately. Numeric correction
or terminal blocking counts as an intervention only when the exact proposal,
guard decision, executed/non-executed action, next request, and evaluator trace
are linked. A success with both guards silent is not attributed to them. Any
post-live semantic or threshold change requires V4.
