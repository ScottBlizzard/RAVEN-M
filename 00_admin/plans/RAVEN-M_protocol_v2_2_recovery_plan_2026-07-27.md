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

The r3 replay again reached 3/4, and the Files episode recovered from the
chooser. Its accessibility stream then remained unavailable and the executor
toggled the same content coordinate eleven times while calling it a toolbar
menu. r4 therefore performs one audited accessibility refresh, adds app-bar
coordinate and single-selection checks, and supports a frozen single-sequence
development diagnostic so the three passing cells need not be rerun.

The focused r4 replay removed every screenshot fallback and toolbar-coordinate
loop, but spent four waits because it interpreted an empty Downloads
destination as unfinished loading. r5 is prompt-only: `No items` is a stable
empty destination, one wait is the maximum, and the next action must navigate
to the named storage root and destination folder.

The first complete focused r5 replay correctly treated `No items` as stable,
but pressed Back before opening the drawer. This exited the destination picker,
discarded the pending move context, and led to a max-steps failure in an
ordinary empty Ringtones folder. r6 remains prompt-only: bottom `CANCEL` plus
`COPY`/`MOVE` controls explicitly identify the picker, Back is forbidden for
folder navigation while those controls are present, and the drawer must be
opened without leaving the pending operation.

The complete r6 replay violated that prompt twice, exited the picker twice,
and exhausted the budget before reaching Ringtones. Prompt compliance is
therefore not an adequate invariant. r7 detects bottom-anchored `CANCEL` plus
`COPY`/`MOVE` controls from the current accessibility state and rejects
`press_back` before execution. The existing one-repair contract must replace
it on the same screenshot, so the rejection uses a model call but no policy
action or environment transition.

The focused r7 replay proved that guard effective and executed the final
`MOVE` in the exact Ringtones destination. The executor then waited once but
long-pressed another source item and started a second move transaction instead
of verifying or terminating. r8 records a successful bottom `COPY`/`MOVE` tap
as post-commit state and rejects later long-press selection or a duplicate
bottom commit before execution. Ordinary taps and one bounded wait remain
available so the destination can be inspected without forcing an unsupported
completion claim.

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
