# A1-R3-v3 one-shot controller nonprogress receipt preregistration

## Identity and evidence boundary

- Mechanism: `a1r3v3_one_shot_controller_nonprogress_receipt_v1`
- Primary experiment: `A1R3V3_OSCNR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- Parent: `a1r2_compact_verified_pending_v1`
- Parent evidence commit: `83c0de5bed18740719b46b5bdd1fccf7904ba0cb`
- Task seed: `20260806`; generation seed: `3407`
- Model and controller: exact A1-R2 Qwen3-VL-32B environment

A1-R3-v2 is a closed pre-live negative.  The full A1-R2 trace is explicitly a
development/calibration set for v3, not held-out evidence.  The future live run
is a matched prospective diagnostic on already observed task instances.

## Single intervention

A1-R2's parser, latest verified/pending ledger, ordinary-history prefix
deduplication, TTL=8, and exact base renderer remain unchanged.

The controller observes only:

- the already executed canonical action;
- `same_shape` from the existing RGB transition;
- `changed_pixel_fraction_gt_5` from the existing RGB transition.

If two consecutive supported actions have the same task-agnostic family and
both transitions satisfy `same_shape=true` and
`0 <= changed_pixel_fraction_gt_5 <= 0.001`, one transient receipt is created.
At most one receipt may ever be created and committed in an episode.  It is
eligible on the next request and expires after the following request.

The primary renderer is strictly factual and appends to, rather than replaces,
the exact A1-R2 renderer:

```text
RECENT OBSERVATION: The last two {renderer_label} actions produced no detectable screen change.
```

It does not say progress, failure, success, completed, choose, avoid, try, or
continue.  The memory supplies a temporal observation and leaves action choice
to the unchanged executor.

## Frozen action families

- tap and long-press: integer half-up buckets
  `q(u)=min(20,max(0,floor(20*clip(u,0,1)+0.5)))`; action types remain distinct;
- swipe: dominant-axis `left/right/up/down`, horizontal on an exact tie;
- type-text: whitespace collapse, casefold, full SHA-256; raw text is not
  retained in CNR state or rendered;
- `press_back`, `press_home`, `press_enter`, `press_recents`, and `wait` are
  discrete families;
- malformed, non-finite, zero-length, terminal, or unknown actions are
  unsupported and clear the current support.

Task name, goal parsing, app/package/activity, accessibility/UI tree, reward,
evaluator, database state, future screenshots, screen hashes, and cross-episode
state cannot affect trigger or renderer.  Screenshot hashes are audit-only.

## Development replay freeze

The zero-generation replay must bind exact raw artifacts and reproduce:

- 19 valid episodes, 603 model calls, and 595 executed actions;
- one preserved infrastructure-invalid attempt linked to its replacement;
- all six A1-R2 successful tasks: exactly 0 receipt creations and 0 CNR reads;
- exactly eight failed tasks with one receipt each and eight committed reads;
- no episode with more than one creation or committed CNR read;
- the exact per-episode creation/read-step manifest;
- deterministic repeated replay and zero generation calls.

The expected eight development exposures are not an efficacy result.  They
only establish that the frozen intervention is sparse, cross-task, and
reachable.  Any semantic change after source freeze requires a new v4 identity.

The factual payload may add at most 1,024 characters and 256 exact tokenizer
tokens across the complete replay relative to A1-R2.  This small overhead is
reported rather than hidden by deleting baseline text.  Live call, total-token,
and elapsed costs remain independent result gates.

## Live capability gate

Fixed first-six order:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

Any valid scientific failure stops the arm permanently.  It is not rerun or
hot-fixed.  Only a recorded infrastructure-invalid attempt may be replaced,
at most once per task and at most twice across the suite.  After 6/6, the
remaining thirteen tasks run in the frozen A1-R2 manifest order; completed
episodes are retained and not rerun.

Every episode starts with fresh memory.  Native action budgets, sampling,
screenshots, action schema, system prompt, and model revision are unchanged.
There are zero auxiliary model calls, extra screenshots, action blocks,
overrides, retries, or forced terminations.

## Independent result verdicts

Accuracy passes only with at least 7/19 full successes, reward greater than
6.5, and zero losses among the six A1-R2 successes.

Cost is reported as three separate gates:

- executor calls `<= 603`;
- total tokens `< 2,685,730`;
- valid elapsed seconds `< 11,230.182856`.

Primary mechanism attribution remains pending until the fixed matched
neutralized ablation.  A primary episode is classified as one of:

- `NO_OPPORTUNITY`
- `CREATED_NOT_COMMITTED`
- `COMMITTED_NO_ACTION_DIVERGENCE`
- `DIVERGENCE_NO_VISIBLE_CHANGE`
- `VISIBLE_CHANGE_RELAPSED`
- `VISIBLE_CHANGE_NO_SUCCESS`
- `QUALIFYING_NEW_WIN_ABLATION_UNRESOLVED`
- `CAUSAL_SUPPORT`
- `CAUSAL_REFUTATION`
- `INFRA_INVALID`

Pixel change is called visible screen change, never semantic progress.  A live
success without a committed CNR is unattributed.  A live loss without a
committed CNR is `PRESERVATION_FAILURE_UNATTRIBUTED`, not evidence of memory
harm.

## Matched neutralized ablation

The neutralized arm uses the same class, detector, receipt lifecycle, cap,
parent ledger, controller, model, seeds, task budgets, and audit.  It omits only
the appended factual sentence and sends the exact A1-R2 renderer.  It is run
only if the primary achieves an accuracy gain supported by a committed CNR,
and only through the first qualifying new-win task in fixed task order.

If any prompt, response, action, screenshot, transition, ledger, or receipt
state differs before the first eligible receipt request, the opportunity is
`UNRESOLVED`.  The factual version does not require the next action to change
family; it asks only whether the exact post-read action hash diverges and
whether the primary succeeds while the matched neutralized task does not.

## Infrastructure and evidence discipline

Source freeze binds the core, A1-R2 parent, controller, protocol/system prompt,
runner, config, tests, replay/preflight/qualification scripts, task manifest,
client/adapter, and environment/model manifests.  Generated evidence is bound
by content hashes but excluded from the source closure to avoid self-reference.

Read tickets are prepared before prompt construction, committed only after the
model request returns successfully, and cancelled on prompt-build or transport
failure.  Parse failure after a successful response still commits the ticket,
because the model received the memory.  Every valid step requires exactly one
transport attempt.
