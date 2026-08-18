# SYS-R2-LRER: Late Raw-Evidence Rehydration

Status: prospective design freeze; no SYS-R2-LRER generation has occurred.

Parent evidence commit: `46d9248fdc96721862ba4d919381846d250d960c`.
Design-development evidence: the sealed A1-R15 Browser forensic report at
`evidence/r15_browser_forensics/`.  All tasks use task seed `20260806`, Qwen
generation seed `3407`, the frozen Qwen3-VL-32B snapshot and native budgets.

## Identity and claim

- System ID: `sys_r2_late_raw_evidence_rehydration_v1`
- Experiment ID: `SYS_R2_LRER_QWEN3VL32B_S20260806_G3407_V1`
- Parent memory is byte/semantics-frozen A1-R2.
- This is a composite system, not R15, not EVR, and not a claim that R15's
  intervention caused its success.

The direct forensic observation is that R15's malformed memory prose stayed in
ordinary history and cumulatively preserved `1,8,10,7,2`; R2/R13D/R14 stripped
the same model-authored observations and later guessed wrong products.  The
prospective hypothesis is that rehydrating prior raw model-authored evidence
immediately before a late result decision can recover this useful mediator.

## Runtime mechanism

The controller privately retains the most recent eight *executed* normal
responses' raw Action summaries, each bound to source step and response hash.
This bounded sidecar is normally silent and is not written to ordinary history
or R2.  The current unexecuted proposal is never added to the buffer.

At most once per episode, the following exact rule defers a proposal:

1. executed actions are at least `ceil(0.70 * native_max_steps)`;
2. at least one later native request slot remains;
3. the proposed canonical family is `type_text`, `answer`, or
   `terminate(success)`;
4. the slot has not previously been used.

The trigger does not inspect task/app name, coordinates, proposed payload,
goal text, UI tree, activity/package, evaluator/reward, known values/answer or
future state.  There is no fallback trigger.

The deferred proposal is not mapped, executed, stored in history, or written
to R2.  On the immediately following normal request, the controller injects
the last eight already-executed raw model Thought+Action records (max 700
characters each, 4000 total) plus
the fixed instruction to reconstruct exact facts in step order, verify coverage
and independently recompute arithmetic/logical constraints without assuming
common/default/example values.  Current screenshot remains authoritative.
The final rendered envelope is capped at 5400 characters so the bounded raw
evidence, eight source-step/hash provenance headers and fixed instruction fit
without provenance-free truncation.
The injection is committed to exactly one normal request and expires; the
executor independently chooses the next action.  There is no auxiliary model
call, action payload override, automatic calculation, forced termination,
extra native budget, persistent advice or cross-episode state.

## Zero-generation design audit

Before live, replay must bind the sealed R15 episode and frozen R2 seven-task
panel.  It must show R15/R2 Browser opportunity before the late `type_text`,
with the eight-source window containing all five observations but excluding
the deferred response.  It must report exact opportunities for all six R2
successes.  The frozen historical expectation is Browser one and six successes
zero.  These already-observed tasks are development diagnostics, not held out.

## Fixed non-fail-fast seven and release

Run all seven valid episodes in this order regardless of scientific failures:

1. BrowserMultiply
2. ExpenseDeleteMultiple2
3. RetroSavePlaylist
4. SimpleCalendarAddOneEvent
5. SportsTrackerTotalDurationForCategoryThisWeek
6. RecipeDeleteMultipleRecipesWithConstraint
7. OsmAndMarker

Only exact 7/7 releases the remaining twelve official tasks in manifest order;
the seven are not rerun.  Less than 7/7 is a complete diagnostic result with
twelve `NOT_RUN_BY_PROTOCOL`.  Valid scientific failures are never rerun.
Only retained, hash-bound infrastructure-invalid episodes may be replaced.

## Validity, attribution and cost

All normal calls must have one transport attempt; retries are disabled.  The
result separately records deferral/injection, exact text/hash/source steps,
normal calls, executed actions, input/output/total tokens and elapsed time.
Success without a committed LRER injection is `SUCCESS_COMPONENT_SILENT` and
gets no LRER causal credit.  Browser success after exact injection is only
`MECHANISM_CONSISTENT_CANDIDATE_SUPPORT`, because no exact-prefix neutralized
counterfactual exists.  Any loss on a historically successful task is a
system-level regression; historical replay silence does not erase the live
result.

No live code, prompt, threshold, capacity, task order or budget may change
after the first model request under this identity.
