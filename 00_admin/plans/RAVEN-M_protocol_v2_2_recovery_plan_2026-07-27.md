# RAVEN-M protocol-v2.2 recovery plan

Date: 2026-07-27

Trigger: protocol-v2.1 Gate E stopped after four cells. The checkpoint is
retained as immutable diagnostic evidence and must never be resumed or pooled
with later evidence.

## Evidence-based diagnosis

- App launch readiness was charged to the policy step budget and caused blank
  or splash observations.
- Android ANR text was visible but was not classified as infrastructure.
- One model-authored direct-screen claim was routed as FACT after a single
  observation and survived as a cross-page hypothesis.
- Critic reobserve/recover verdicts were advisory and could be ignored.
- B3 converted a visible but unselected category into a completed selection.
  This remains a baseline weakness and is not tuned away.

## Generic repair

1. After `open_app`, collect bounded readiness observations without spending a
   policy action until accessibility is available or the bound is reached.
2. Detect ANR/crash text separately from task validation failures and retry the
   cell through typed infrastructure recovery.
3. Route a model-authored direct-screen claim as HYPOTHESIS. Repetition by the
   same model is recorded but is not independent verification and cannot
   promote the claim to FACT.
4. Make page/screen identity claims page-local and stale them after semantic
   page change.
5. Treat Critic `reobserve` and `recover` verdicts as binding against repeating
   the blocked action.
6. Keep Planner required variables as frozen episode anchors, including
   resolved relative dates.
7. Reject terminal answers copied from width-limited or clipped overview text;
   require a full detail or second view.
8. Adjudicate consequential commits on the same screenshot and require visible
   binding of the exact target/destination before execution.

## r1 development replay and r2 decision

The four-cell r1 development replay finished cleanly with no infrastructure or
protocol audit failure. Contacts-B3 and Expense-B3 succeeded. Calendar-M0
submitted the clipped visible prefix `Board me`; Files-M0 confirmed a move
without visibly selecting the required destination and then repeated false
model-authored observations. These are generic epistemic-authority gaps, so r1
is retained as diagnostic evidence and a separate r2 source tag/suite is used.

The r2 replay fixed Calendar and reached 3/4 successes, but Files stopped
correctly when the model repeated Back on an `Open with` overlay after the
guard blocked that semantic fingerprint. The screenshot had changed while the
captured accessibility tree still belonged to the previous foreground
activity. r3 therefore applies the foreground/tree consistency wait after
every action, not only after `open_app`, and makes tap-to-view versus
long-press-to-select recovery explicit.

## Qualification order

1. Targeted unit and integration tests.
2. Full local regression and protocol-v1 isolation seal.
3. Zero-model-call emulator/readiness/ANR smoke.
4. Four-cell non-scored development replay in a separate output root.
5. Freeze and preflight a fresh eight-cell Gate E.
6. Start Gate E only if the development replay has no controller error,
   unresolved guard repair, or unclassified infrastructure failure.

## Evidence policy

- `runs/protocol_v2_1/nonhard_capability_v2_1_seed20260729_r1` is diagnostic
  only.
- v2.2 uses a new protocol ID, source tag, suite ID, and output root.
- B3 prompt and summary schema remain unchanged.
- No v2.1 or development-smoke cell is a v2.2 scored cell.
