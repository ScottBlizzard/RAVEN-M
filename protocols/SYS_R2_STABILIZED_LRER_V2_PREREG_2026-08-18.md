# SYS-R2-SLRER V2: Stabilized Late Raw-Evidence Rehydration

Status: prospective exploratory composite-system preregistration. No V2 model
generation may occur before the implementation, config, replay, source freeze,
tests, and zero-generation preflight are committed and validated.

## 1. Claim boundary and parent

The immutable memory parent is A1-R2
`a1r2_compact_verified_pending_v1`. V2 is not a new pure-memory arm. It is a
composite of the frozen LRER V1 evidence sidecar and a deterministic visible
frame-settling transport policy. Any benefit is a system result; it must not be
reported as proof that R15 EVR, R2 memory, or LRER alone caused success.

The seven diagnostic tasks and seed have already been observed. Results are
matched exploratory diagnostics, not held-out or generalization evidence.

## 2. Development evidence

The sealed SYS-R2-LRER V1 Browser episode is a valid failure with zero LRER
opportunity. It reached the number page at request 15 rather than request 12 in
R2/R15. It then observed `1, 8, 10, 7, 2`, but R2 stripped those observations
from ordinary history and the final request guessed `3840`.

Two transitions captured a visibly stale post-action frame:

- after request 3 the foreground activity changed to Files while the UI hash
  stayed unchanged and changed-pixel fraction was about `0.000106`;
- after request 7 the foreground activity changed to Chrome first-run while
  the screenshot was byte-equivalent to the preceding resolver frame.

The next model requests repeated the already correct actions. The task page was
therefore reached three requests later than the prior R2/R15 trajectories. At
request 21 the first `type_text` proposal had zero remaining decision slots, so
V1 correctly did not defer it. This is `VALID_FAILURE_COMPONENT_SILENT_ZERO_OPPORTUNITY`.

These observations motivate V2 but do not constitute a causal counterfactual.

## 3. Frozen system identity

- system: `sys_r2_stabilized_late_raw_evidence_rehydration_v2`
- experiment: `SYS_R2_SLRER_QWEN3VL32B_S20260806_G3407_V2`
- task seed: `20260806`
- generation seed: `3407`
- model/revision, system prompt, sampling, action schema, task instances, reset,
  native step budgets, transport retry policy, and R2 parent are unchanged.

The only V2 additions are sections 4 and 5.

## 4. Visible-frame settle policy

After every successfully executed canonical non-terminate action (including an
`answer` interaction-cache write) and before the controller's single
post-action state capture, request one fixed `1.0`-second sleep. Then
call the existing `env.get_state(wait_to_stabilize=True)` exactly once. That
returned RGB image is both the audited `after` state and the pending current
state for the next model request.

The policy:

- makes zero model calls and executes zero Android actions;
- takes no extra screenshot or UI-tree capture;
- does not branch on pixels, activity, package, UI tree, task, goal, reward, or
  evaluator;
- does not retry or replay the preceding action;
- has a requested-delay budget of at most `native_max_steps × 1.0 s` per
  episode; operating-system scheduling may make the separately recorded
  observed wall time slightly larger;
- records requested and observed sleep duration for every executed action.

The fixed delay is preferred to a hidden-UI conditional rule. It uses no audit
side channel for runtime decisions and gives every task/action the same settle
opportunity.

## 5. Frozen LRER state machine

LRER V1 semantics are byte/semantic inherited:

1. Maintain no always-on extra prompt.
2. At or after `executed_actions / native_max_steps >= 0.70`, review the first
   `type_text`, `answer`, or successful terminal proposal.
3. Require at least one later normal request, unused one-shot state, and no
   pending ticket.
4. Defer that proposal without mapping, executing, writing R2, or committing it
   to history.
5. On exactly the next normal request, inject the most recent eight previously
   executed raw model-authored Thought+Action records, each bound to source step
   and response SHA. The deferred proposal and future state are excluded.
6. The fixed text requires step-ordered fact reconstruction, coverage checking,
   and independent arithmetic/logical verification. The current screenshot is
   authoritative.
7. Injection is committed only after successful single transport and expires
   after that request. Maximum one deferral and one committed injection per
   episode. Auxiliary model calls are zero.

Caps remain: 700 characters per source record, 4,000 source characters, eight
records, and 5,400 rendered characters.

## 6. Information boundary

Runtime decisions may use only the goal already visible to the executor,
current RGB screenshot, past executed canonical actions, R2 state, and the
model's own prior executed responses. No evaluator/reward, hidden UI tree,
activity/package, future frame, task/app branch, Browser name, known sequence,
`1120`, coordinates, or task-specific regex may enter V2 decisions or prompts.

Audit-only UI/activity artifacts may be recorded after the fact but never
passed to the model or settle/LRER decision.

## 7. Zero-generation G0

G0 must establish, with `generation_calls=0`:

- exact identity/config/source closure and committed implementation ancestry;
- v1 R2/R15 Browser LRER opportunity reproduction;
- sealed V1 live Browser route: page-at-15, exact five observations,
  first result proposal at 21, zero remaining slots, zero LRER opportunity;
- exact two stale-transition audit markers as development evidence;
- six R2 historical success tasks with zero LRER opportunities;
- controller fake-environment test proving one 1.0-second sleep after each
  executed action, before exactly one after-state capture, and zero additional
  model/action/state calls;
- no-policy/default controller byte/behavior compatibility at settle=0;
- exact tokenizer delta, render caps, ticket/transport/hash closure;
- non-fail-fast seven-task runner and 7/7-only release of the remaining twelve;
- valid scientific failure non-retry and retained hash-bound infra replacement;
- fresh model receipt, single transport, no retry, and fixed localhost tunnel.

Historical replay cannot prove that sleeping would have changed a historical
frame. It only proves the observed failure pattern and the absence of LRER
activation on the six protection traces. The settle mechanism itself is tested
as a deterministic controller invariant and judged prospectively in live.

## 8. Live order and stopping

Fixed non-fail-fast seven-task order:

1. BrowserMultiply
2. ExpenseDeleteMultiple2
3. RetroSavePlaylist
4. SimpleCalendarAddOneEvent
5. SportsTrackerTotalDurationForCategoryThisWeek
6. RecipeDeleteMultipleRecipesWithConstraint
7. OsmAndMarker

All seven valid episodes run even after an early scientific failure. Valid
scientific outcomes are never rerun under the same identity. Only retained,
hash-bound infrastructure-invalid attempts may be replaced under the existing
per-task and suite caps.

Only exact 7/7 releases the remaining twelve tasks in official manifest order;
the first seven are not rerun. Less than 7/7 seals a seven-task diagnostic and
marks the remaining twelve `NOT_RUN_BY_PROTOCOL`.

## 9. Reporting and attribution

Every task records reward, calls, executed actions, token usage, elapsed time,
settle events/time, LRER eligibility/deferral/injection, exact injected text and
sources, first divergence when comparable, and one of:

- `MECHANISM_CONSISTENT_CANDIDATE_SUPPORT`
- `SUCCESS_COMPONENT_USED_PRESERVED_ABLATION_UNRESOLVED`
- `SUCCESS_COMPONENT_SILENT_OR_UNUSED`
- `ACTIVATED_NO_GAIN`
- `REGRESSION`
- `NO_OPPORTUNITY`
- `INFRA_INVALID`

Browser success with no committed LRER injection is not evidence for LRER; it
may be consistent with frame settling or trajectory variance. Browser success
after injection is still single-arm candidate support, not proof of causality.
For an R2-success protection task, a success after LRER injection is active
preservation with unresolved attribution, never a new gain. Any loss among the
six R2 success tasks is a system regression. `component silent` refers only to
LRER because frame settling is active after every executed action. The frozen
A1-R2 19-task result supplies the exact per-task prior outcome rather than an
inferred task list. Accuracy, mechanism, and cost verdicts are reported
separately. Each task also reports LRER counters/state and either the first
same-ordinal response-hash divergence from its tracked R2 trace or an explicit
not-comparable reason.

## 10. Identity invalidation

After the first V2 generation, changing the settle duration, LRER threshold,
families, renderer, caps, prompt, budget, task order, or runner semantics creates
a new identity. No live-result-driven hot fix is permitted.
