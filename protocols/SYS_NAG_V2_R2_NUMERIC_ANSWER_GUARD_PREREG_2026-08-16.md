# SYS-NAG V2: R2 + deterministic numeric-answer consistency guard

## Version boundary

SYS-NAG V1 produced four valid successes. On `SportsTrackerTotalDurationForCategoryThisWeek`, the model proposed `165`, the guard executed `180`, and reward was 1. The runner then locked task five because it applied the six-task report at the four-task release boundary. V1 is sealed as `VALID_GATE4_COMPLETE_ORCHESTRATION_LOCKED`; it is not a scientific failure.

V2 has a new system/experiment identity. Its intervention semantics, model, seed, sampling, task instances, R2 memory, regexes, thresholds, and task order are byte-semantically unchanged. V2 changes only:

1. the generic runner recognizes SYS-NAG as a six-task-gated arm, so tasks five and six run before the remaining 13 are released;
2. the audit stores an immutable copy of the model-proposed action before mutating the separate executed-action copy.

## Identity

- System ID: `sys_r2_numeric_answer_consistency_guard_v2`
- Experiment ID: `SYS_NAG_V2_R2_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`
- Parent evidence commit: `603d4088a7b3448df3472e8bfc6fa8bd1bba0e97`
- This is a composite-system intervention, not a memory-mechanism improvement.
- All tasks are previously observed matched diagnostics, not held out.

## Frozen guard

After normal response parsing and before action execution, the guard acts only on a single-integer `answer` whose final model-authored Action-summary clause contains an additive cue and at least two explicit durations. Supported forms are `H hour(s) M minute(s)` or `H:MM[:SS]`; word forms take precedence. A leading `MEMORY[...] |` prefix is excluded. If the proposed integer differs from the bounded deterministic sum, only answer text is replaced.

The guard uses no task name, package/activity, screenshot/OCR, UI tree, evaluator, reward, future trace, database, or model call. It cannot recommend navigation, block ordinary actions, or terminate an episode. Every proposal, duration list, computed sum, and executed answer is retained. Overrides are declared non-memory action interventions.

## Gates

Fixed order:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

Any valid failure among these six seals V2. Passing all six releases the other 13 without rerunning the gate. Infrastructure-invalid attempts follow existing retained-artifact replacement limits.

Offline replay must scan the exact 19 valid A1-R2 episodes, reproduce the V1/V2 observed `165 -> 180` regression, run focused tests, and freeze every executable dependency. Live generation is forbidden until zero-generation preflight and a fresh same-process receipt pass.

Accuracy, guard activation, and cost are separate verdicts. A silent success is not attributed to the guard. The observed override-success chain is mechanism support but remains ablation-unresolved. No post-live semantic change is permitted under V2.
