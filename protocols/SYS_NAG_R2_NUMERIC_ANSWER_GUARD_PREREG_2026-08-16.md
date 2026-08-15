# SYS-NAG: R2 + deterministic numeric-answer consistency guard

## Identity and evidence boundary

- System ID: `sys_r2_numeric_answer_consistency_guard_v1`
- Experiment ID: `SYS_NAG_R2_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`
- Parent evidence: SYS-TRRC V2 terminal report at source commit `2649c61891cdfa53b8dba823d778a509bb642f33`.
- This is a composite-system intervention, not a new memory mechanism and not evidence that R2 memory improved.
- All 19 seed-20260806 tasks were previously observed; results are matched prospective diagnostics, not held-out evidence.

## Frozen intervention

The memory path is exact prospective A1-R2 compact verified-pending memory. The only new intervention is an episode-local deterministic guard after the normal executor response is parsed and before its action is executed.

The guard may act only when all conditions hold:

1. the proposed canonical action is `answer` and its text is one signed base-10 integer;
2. the final operation clause of the model-authored Action summary contains an additive cue (`total`, `sum`, `calculate`, `combined`, or `altogether`);
3. that same clause contains at least two explicit durations, either `H hour(s) M minute(s)` or `H:MM[:SS]`;
4. every minute field is 0--59 and the recomputed total is within 0--1,000,000.

Word-form durations take precedence over colon-form durations in the same operation clause. A leading `MEMORY[...] |` clause is excluded so repeated evidence is not double-counted. If the proposed integer differs from the deterministic sum, only the answer text is replaced. Otherwise the proposal is byte-semantically unchanged.

The guard has zero model calls, no OCR, no screenshot parsing, no hidden UI, no evaluator, no task name, no app/package/activity, no future trace, no action recommendation, and no forced termination. Every review and override is serialized. An override is counted openly as a non-memory action intervention.

## Motivation frozen before SYS-NAG live generation

SYS-TRRC V2 stopped after three valid successes when `SportsTrackerTotalDurationForCategoryThisWeek` failed. Its recovery detector and auxiliary path were silent. The executor explicitly represented `1:45` and `1:15` but answered `165`; the deterministic sum is `180`. The new guard addresses only this observed arithmetic-consistency failure and does not widen the unsuccessful recurrence detector.

## Offline and live gates

Zero-generation replay must:

- reproduce the V2 failing proposal and deterministically map `165 -> 180`;
- scan all valid A1-R2 episode actions and report every eligible/override event;
- prove ordinary non-answer and non-explicit-duration actions unchanged;
- execute the focused tests and freeze exact source bytes.

Live order is the six-task capability gate used by the vertical R2 series:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

Any valid scientific failure in these six seals this identity. Infrastructure-invalid attempts may be replaced only under the existing runner limits and with retained artifacts. Passing 6/6 releases the remaining 13 tasks without rerunning the first six.

Accuracy, guard activation, and cost are separate conclusions. A success with zero guard override is not attributed to the guard. A guard override followed by success is trace-grounded mechanism support but, without an exact matched no-guard branch, is not a robust causal claim. Full-suite accuracy improvement requires more than the frozen R2 result while preserving its successful tasks; equal accuracy with lower cost is only a Pareto diagnostic.

## Failure taxonomy

- `CAPABILITY_GATE_FAILURE`
- `GUARD_NOT_ELIGIBLE`
- `ELIGIBLE_ALREADY_CONSISTENT`
- `OVERRIDE_SUCCESS_ABLATION_UNRESOLVED`
- `OVERRIDE_FAILED`
- `INFRASTRUCTURE_INVALID`

No live threshold, regex, operation cue, or task order may be modified under this identity. Any semantic change creates a new system identity.
