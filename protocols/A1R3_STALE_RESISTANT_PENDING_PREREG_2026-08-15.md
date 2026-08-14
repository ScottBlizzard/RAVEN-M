# A1-R3 Stale-Resistant Pending Ledger Preregistration

Date: 2026-08-15 (Asia/Hong_Kong)

Status: prospective design. Live generation is forbidden until this version's
real-trace replay, tests, source freeze, zero-generation preflight, and fresh
server receipt all pass.

## Evidence-derived motivation

A1-R2 was the first vertical arm to exceed A1: 6/19 and reward 6.5, with all
five A1 successes retained and `OsmAndMarker` added. It reduced total tokens
and elapsed time but tied A1 at 603 calls, so its strict cost verdict failed.
Its 19 valid traces contain 130 identical-state refreshes. Long failures
included 78 actions on `MarkorMergeNotes`, 120 on `OsmAndTrack`, and several
60-action episodes. The A1-R2 memory repeatedly renewed unchanged pending text.

A1-R3 tests one narrow hypothesis: explicit pending memory remains useful, but
unchanged pending state must not renew itself, and repeated visible failure may
be remembered as one negative fact. It is not a new planner or verifier.

## Frozen identity and parent

- parent evidence commit: `f7368bcb3628112e497045c398128ad383811a7c`
- mechanism: `a1r3_stale_resistant_pending_v1`
- experiment: `A1R3_SRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- task seed: `20260806`
- generation seed: `3407`
- model/revision, sampling, screenshots, action schema, task instances, native
  step budgets, evaluator, and A1 system prompt remain identical to A1-R2.

## Exact intervention

The model still writes A1's exact form:

`MEMORY[observed=...; verified=...; pending=...] | <ordinary Action imperative>`

Storage keeps one latest `verified + pending` pair and removes the MEMORY
prefix from ordinary action history. `observed` remains discarded because the
current screenshot is authoritative.

The following rules are frozen:

1. A distinct normalized `verified + pending` pair creates or replaces the
   single ledger and starts an eight-request TTL.
2. An identical pair never changes source step, provenance, or TTL.
3. On expiry, the exact state hash becomes the single tombstone. The identical
   state cannot reactivate until a distinct valid non-none state is accepted.
4. `pending=none` explicitly clears ledger, tombstone, and failed-attempt fact.
5. Visible no-progress means same RGB shape and
   `changed_pixel_fraction_gt_5 <= 0.001`. No activity/package/UI-tree signal
   is used.
6. Under the same active ledger, two consecutive no-progress actions in the
   same canonical family create one failed-attempt fact. Tap/long-press
   coordinates use fixed 0.05 bins; swipes use direction; identical typed text
   uses a hash; system buttons and wait use action type.
7. Any material RGB change, distinct ledger, clear, or expiry removes the
   failed-attempt fact. It never refreshes ledger TTL.

Without a failed-attempt fact, the renderer is byte-identical to A1-R2. With
one fact it appends:

`AVOID REPEATING: {action label} produced no visible progress twice for this pending item. Use the current screenshot before choosing a different route.`

This text reports past visible evidence only. It does not select an action.

## Capacity and decision boundary

- one active ledger;
- one state-hash tombstone;
- one failed-attempt fact;
- one pending atomic read ticket;
- at most 1,100 rendered characters;
- zero additional model calls;
- no guard, block, override, repair, retry, planner, critic, verifier, forced
  termination, extra screenshot, OCR, UI tree, evaluator, task name, app
  whitelist, cross-episode state, retrieval, training, or step-budget change.

The memory may affect behavior only through exact text appended to the next
ordinary executor request. Current RGB is always authoritative.

## Zero-generation replay gate

Replay the 19 valid A1-R2 episodes selected by its checkpoint, verifying every
summary and episode JSON hash. Required conditions:

- exactly 19 valid episodes, 603 model calls, and 595 executed actions;
- all six A1-R2 success sentinels receive at least one projected non-empty read;
- none of those six sentinels creates failed-attempt evidence;
- at least 100 identical or retired-state writes are non-reinforcing;
- failed-attempt evidence is actually read in at least two failed episodes;
- projected rendered characters are at most 75% of A1-R2's actual 108,423;
- zero generation calls and no forbidden input.

Replay is feasibility and intervention-opportunity evidence, never a reward
prediction.

## Prospective live order and stopping

The first six tasks are fixed and blocking:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

They must be 6/6 with reward 1.0. Any valid scientific failure terminates the
arm and is never rerun. Only infrastructure-invalid attempts may be replaced
by the same task with bidirectional linkage. After 6/6, the remaining thirteen
frozen tasks run once in manifest order; the first six are not repeated.

## Independent verdicts

- Accuracy PASS: at least 7/19 full successes, reward greater than 6.5, and no
  loss on the six A1-R2 successes.
- Cost PASS: calls below 603, total tokens below 2,685,730, and valid elapsed
  time below 11,230.182856 seconds.
- Mechanism signal: at least two exact failed-attempt injections are followed
  by a different action family and material RGB progress within four executed
  actions without the same-family failure recurring within four more actions.
  This is a trace-grounded mechanism signal, not proof from a matched ablation.

The three verdicts remain separate. All 19 tasks at this seed have been
observed, so any result is a matched prospective paired diagnostic, not
pristine held-out generalization.

## Falsification and version boundary

A gate-six loss, fewer than seven full successes, or increased looping rejects
the corresponding claim. Thresholds, state fields, parser, renderer, or
trigger rules cannot change after the first valid live generation. Any such
change creates a new mechanism and experiment version.
