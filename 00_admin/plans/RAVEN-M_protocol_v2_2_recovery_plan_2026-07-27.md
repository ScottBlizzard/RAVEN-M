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

The focused r8 replay proved that the post-commit state prevents a second
filesystem transaction, but the official evaluator remained zero. The Music
grid contained multiple full accessibility filenames rendered as the same
truncated `nature_sounds_...` prefix, and the executor long-pressed a tile
without exact-name evidence. The destination likewise showed only a truncated
label, so the completion critic rejected the claim. r9 therefore adjudicates
each Files long-press against the task-literal filename and the nearest full
accessibility filename before execution. It also narrows the post-commit rule:
reversible exact-item inspection is permitted, while a second `Move to`,
`Copy to`, or bottom commit is rejected.

The focused r9 replay proved the exact-target invariant: both the initial and
repaired long-press were blocked before execution. Current accessibility
showed eight same-extension candidates, the exact `nature_sounds.mp3` target
was off-screen, and the proposed coordinate was nearest to
`nature_sounds_2023_02_11.mp3`. The generic repair prompt nevertheless opened
with "correct its format only", so the executor repeated the same structurally
valid but semantically rejected action and the run stopped safely. r10 makes
the one-repair contract error-class-aware: semantic action rejection requires
a materially different action, and the validation message exposes the
task-literal visibility result plus the nearest full filename. It does not add
a repair call, rewrite an action, or expose evaluator state.

The first r9 invocation also found a Windows recovery defect before episode
creation: a stale ADB descendant could retain captured PowerShell pipes after
the stop command timed out. r10 redirects both emulator stop and start
lifecycle output to recovery files, so the existing subprocess timeouts remain
observable and bounded. This changes infrastructure handling only and does not
alter model inputs, task instances, or scoring.

The focused r10 replay confirmed that the semantic-repair branch changed model
behavior: the repair did not repeat the first coordinate. It still chose a
second `long_press` on the unchanged truncated grid and targeted another
same-prefix distractor. Both actions were blocked, so no filesystem mutation
occurred. r11 removes the remaining ambiguity in the repair contract. After an
exact-target rejection, the one same-screen repair may not use `long_press`;
it must change the information state through Search, view change, or scrolling.
Selection can be attempted only by a later policy step after observing the new
screen. r11 does not expose a target coordinate or silently retarget an action.

The focused r11 replay enforced the non-`long_press` contract, but its three
Search attempts used `y` near 0.18, opened content rather than the top app bar,
and were eventually stopped by the semantic loop guard. That value closely
matches the bare coordinate-normalization example repeated in every prompt:
pixel `y=438` becomes normalized `y=0.1826`. r12 replaces the ambiguous worked
example with an explicit layout contrast: a typical top-app-bar center at
pixel `y=192` is normalized `y=0.08`, while pixel `y=438` is content and must
not be used for Search/menu icons. The exact-target repair repeats the same
generic top-app-bar range without injecting a current accessibility bbox.

The focused r12 replay confirmed the coordinate correction: the model used
`(0.07, 0.078)` for the top menu, reached the Music folder, and did not repeat
the r11 content-row Search tap. It then proposed `long_press` without the
schema-required `duration_ms`. The single bounded repair was consumed adding
that field; only then could the exact-target guard identify the wrong nearby
file and reject it. r13 adds a generic required-action-field reminder to the
normal observation prompt so schema completion does not hide semantic guard
feedback. The schema, one-repair budget, and exact-target guard are unchanged.

The focused r13 replay then validated that chain: the first wrong target was
blocked, the single repair tapped Search at `(0.82, 0.075)`, and the exact task
literal was sent to `type_text`. Search was visibly focused before typing, but
the action also supplied `x,y` and `clear_text=true`. AndroidWorld clicks any
supplied coordinate before input, so the extra click moved focus and Ctrl+A
selected 14 files. r14 makes this execution semantic explicit: when an empty
field visibly has a caret, omit `x,y` and use `clear_text=false`. No controller
rewrite or hidden UI coordinate is introduced.

The focused r14 replay showed that prompt-only compliance was insufficient:
the model described Search as active yet still emitted coordinate-bearing
`type_text` with `clear_text=true`, then repeated the failure to the step
limit. r15 therefore adds an audited focused-input validation. It derives only
`present` and `empty` facts from visible editable/focused accessibility flags,
without exposing an element bbox. A conflicting `type_text` is rejected before
execution; the existing single repair must preserve its exact text and
provenance while removing `x,y` and disabling clearing for an empty field.

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

## r16 focused-input evidence extension

The r15 focused FilesMoveFile diagnostic showed that DocumentsUI can open
Search and expose the visible Latin input-method package without preserving
the parent Search field in AndroidWorld's leaf-only accessibility projection.
The focused-editable-only guard therefore missed coordinate-bearing
`type_text`, and AndroidWorld's pre-input click selected 14 filesystem items.

r16 keeps all r15 controls and adds one secondary, current-screen-only signal:
the visible `com.google.android.inputmethod.latin` or
`com.android.inputmethod.latin` package proves that text input is already
active. When that signal or a focused editable node is present,
coordinate-bearing `type_text` is rejected before execution and repaired
within the existing one-repair budget by preserving text and provenance while
removing `x,y`. Keyboard presence alone does not infer that the field is empty,
does not expose a coordinate, and does not authorize a silent action rewrite.

## r17 coordinate-to-editable binding

The r16 diagnostic validated the soft-keyboard fallback but exposed an earlier
state: Search was tapped without a semantic transition, so neither a focused
editable node nor the keyboard was present. The next coordinate-bearing
`type_text` clicked a non-editable top-bar location and selected 14 items
before the r16 signal could become active.

r17 adds a pre-execution binding check for that inactive-input state. A
coordinate-bearing `type_text` is allowed only when its point is inside a
current visible, enabled, editable accessibility element. Otherwise the
existing one bounded repair must return a non-`type_text` reversible action
that activates or reopens an input and leaves typing to a later observed
screen. The assessment records only counts and a matched boolean; it exposes
no bbox, injects no coordinate, and uses no evaluator state.

## r18 editable-target switch correction

The first r17 formal cell received native reward 1.0, but its controller audit
found a semantic error before the second cell began. With the soft keyboard
visible, the model proposed explicit coordinates for other visible editable
fields. The focused-input guard removed those coordinates without consulting
the already-computed target binding, and the phone number was consequently
entered into Company before it was also entered into Phone. Native task reward
did not detect the redundant wrong-field edit.

r18 treats current accessibility target binding as the deciding evidence. If
a coordinate-bearing `type_text` point matches a visible, enabled, editable
element, the explicit field switch is allowed even while an input method is
active. If it does not match, the r17 focused-input rejection and bounded
coordinate-removal repair remain in force. The failed r17 formal directory is
diagnostic only; r18 must pass focused Contacts and Files diagnostics, receive
a new source tag and freeze, and rerun all eight formal cells from scratch.

## r19 declared text-source binding

The r18 Contacts diagnostic validated all three keyboard-active editable-field
switches without a focused-input false positive. It also exposed a separate
provenance gap: the model inserted the unrequested Company value
`Tech Solutions` and declared it as `task_literal`. The existing provenance
check verified the label and memory-ID shape, but did not bind the proposed
text content to the declared source. Native reward remained 1.0 because the
requested name and number were also present.

r19 binds `task_literal` text to the task string and `current_screen` text to
visible current accessibility text, content descriptions, hints, or tooltips.
Matching is case-insensitive with whitespace normalization and records only
the origin, source-value count, and matched boolean. A mismatch is rejected
before execution, and the same check applies to the single repair so a model
cannot launder invented text by changing only its provenance label. Values
from verified memory and deterministic calculations retain their existing
separate authority checks. r19 must rerun focused Contacts and Files
diagnostics before any fresh eight-cell formal attempt.

## r20 task-value to field-role binding

The r19 Contacts diagnostic eliminated the fabricated Company text, but the
model next entered the valid task-literal phone number into Company and then
repeated it in Phone. Source provenance and editable-target existence were
both correct, yet the value and field had conflicting semantic roles. Native
reward again remained 1.0.

r20 derives coarse roles from the task sentence or line that contains the
literal and from the visible metadata of the editable hit by its coordinate.
The role vocabulary covers generic GUI concepts such as person name, phone,
company, amount, category, note, title, date/time, file, and folder. Search,
Filter, and Query fields remain generic query targets. A coordinate-bearing
task-literal edit is rejected only when both sides are adjudicable and their
roles are disjoint. The repair keeps the exact requested value and provenance
but must select a visibly supported role-compatible field. The audit records
role groups and counts, not task values, field labels, bboxes, coordinates, or
evaluator state.

## r21 bounded navigation recovery

The r20 Contacts diagnostic safely blocked the fabricated optional Company
value and prevented the task phone number from entering Company. The bounded
repair then chose an upward swipe instead of filling the visible empty Phone
field and repeated the same swipe through the remaining policy steps. Because
the cross-state coordinate streak covered only `tap` and `long_press`, the
episode exhausted its twelve-step budget without an unsafe mutation but also
without completing the requested field.

r21 extends the existing three-action cross-state streak limit to canonical
`swipe` actions. A fourth identical swipe is rejected even when incidental
screenshot state changes, and its bounded repair must choose a materially
different action. The declared-source repair also states a generic priority:
when a visible empty editable corresponds to a remaining TASK value, fill that
requested value in its matching field now; otherwise choose one non-commit
action and do not repeat navigation that produced no semantic progress. The
controller does not inject a field coordinate, rewrite an action, add model
calls, change the twelve-step budget, or use evaluator state.

## r22 inactive-input clear race

The r21 Contacts diagnostic passed natively and semantically: reward was 1.0,
only the requested name and phone rows existed in the contacts provider, and
there was no organization row. The focused Files diagnostic then exposed a
different boundary condition. Search had opened asynchronously and exposed a
visible editable control, but neither a focused editable nor the soft keyboard
yet proved input readiness. A coordinate-bearing `type_text` correctly matched
that control, yet `clear_text=true` made AndroidWorld click and immediately
send Ctrl+A. Focus activation raced with that key chord, and DocumentsUI
selected all fourteen surrounding items. The run was stopped before any file
operation commit.

r22 rejects this specific combination before execution: input is not visibly
active, the coordinate matches an editable, and `clear_text=true`. Its single
bounded repair must be a reversible tap on the same visibly supported input;
typing occurs only on a later observed screen after a focused editable or soft
keyboard proves readiness. Existing keyboard-active field switching remains
valid, and no coordinate, focus state, or task action is injected.

## r23 unique active input binding

The r22 Files replay proved the new inactive-input guard: the dangerous first
`type_text` was blocked, the bounded repair tapped the visible Search input,
and the next screenshot showed a caret and soft keyboard with zero selected
items. On the following policy step, however, the model again supplied the
same input coordinate with `clear_text=true`. Because the keyboard made input
ready and the coordinate matched an editable, the r18 multi-field exception
treated this redundant same-field click as a valid switch. DocumentsUI again
handled Ctrl+A as select-all. The run was stopped before any file commit.

r23 distinguishes an actual multi-field switch from a redundant coordinate on
the sole visible editable. With active input and exactly one visible editable
matched by the coordinate, the existing focused-input guard removes `x,y`; if
that matched input is visibly empty, the bounded repair also requires
`clear_text=false`. Multiple visible editables continue to allow explicit
field switching. The assessment records only counts and an emptiness boolean,
never text, labels, bboxes, coordinates, or evaluator state.

## r24 soft-keyboard gesture containment

The r23 Files diagnostic passed with native reward 1.0 and a clean semantic
audit. The Contacts diagnostic also correctly blocked the task phone number
from entering the Company field, but its bounded repair proposed a downward
swipe whose start point lay inside the visible Gboard surface. Android
interpreted that action as gesture typing instead of page navigation, inserted
`By` into Company, and repeated navigation consumed the remaining step budget.
No contact was saved, so the run ended at native reward 0.0.

r24 treats a swipe that starts on a visible soft-keyboard accessibility element
as unsafe while the keyboard is present. It is rejected before execution and
the bounded repair must dismiss the keyboard with `press_back`, then observe a
fresh screen before navigating. A field-role repair may still directly type
the exact requested value into a visibly supported role-compatible field; if
that is not possible, it must dismiss the keyboard rather than swipe. The
assessment and audit expose only booleans, package names, and counts—never
keyboard geometry, task text, field labels, or evaluator state.

## r25 empty destination-picker progress

The r24 Contacts diagnostic passed natively and semantically. It entered only
the requested first name, last name, and phone number, saved the contact, and
left no organization row. The r24 Files replay also preserved exact-file
selection and safe focused search input, but it spent six policy steps waiting
and swiping in an already rendered empty Downloads destination. It eventually
opened the navigation drawer and reached Ringtones on the final step, leaving
no budget to execute the bottom Move control. Native reward was 0.0.

r25 recognizes a visible empty-directory marker while the bottom Cancel and
Copy/Move controls prove that the Android destination picker is active. A
`wait` or `swipe` in that state is rejected: neither can reveal a sibling
folder. The bounded repair must tap a visibly supported control—bottom
Copy/Move if the current directory is the requested destination, otherwise the
top-left navigation drawer. It may not wait, swipe, press back, or guess a
content coordinate. The assessment exposes only the action type, booleans, and
an empty-marker count, never directory text, geometry, task literals, or
evaluator state.

## r26 screenshot-visible terminal-answer provenance

The r25 formal suite stopped correctly after its first successful Contacts
cell. In the second Calendar cell, the frozen screenshot clearly showed
`October 25 (Wed)`, the full title `Board meeting`, and `16:00 - 16:05`.
The executor returned that exact title with `text_origin=current_screen`, but
the accessibility tree omitted the title. The deterministic declared-source
guard therefore rejected a visually supported answer twice and stopped the
suite before any incorrect answer was executed.

r26 does not weaken general text provenance. It adds one bounded, same-turn
visual-source adjudication only for a terminal `answer` that declares
`current_screen` when accessibility cannot match the exact candidate. The
Critic receives the unchanged screenshot, task, exact candidate, completion
evidence, and a count-only accessibility assessment. It may return `proceed`
only when the exact candidate is fully readable and the visible context binds
it to the requested task target. It cannot rewrite the answer, use evaluator
state, cite memory, or authorize `type_text`. A rejection invokes the existing
single repair and requires one reversible action to open a relevant detail or
obtain a clearer view; repeating the answer is forbidden. The adjudication is
cached by candidate hash within the turn, recorded in the completion audit,
and M0 still undergoes its separate completion Critic after source acceptance.

## r27 accessibility-loss infrastructure typing

Both r26 policy diagnostics passed with native reward 1.0. Before the
successful Contacts retry, one attempt lost AndroidWorld's accessibility tree
immediately after task initialization. No task action executed, but the shared
infrastructure classifier did not recognize the exact
`Could not get a11y tree.` error and conservatively stopped the development
suite as unclassified instead of using its bounded emulator-recovery attempt.

r27 changes only Gate-E orchestration. It preserves the shared classifier and
adds one exact fallback mapping from that AndroidWorld error to
`INFRA_EMULATOR_LOST`. The existing retry cap, attempt archive, cold recovery,
two-consecutive-failure stop, and startup audit remain authoritative. No
controller, prompt, schema, task, seed, step/model budget, evaluator, or
acceptance threshold changes.

## r28 declared-source keyboard-aware repair

The first r27 formal cell entered the requested first and last names safely.
It then proposed the unrequested Company value `Tech Solutions`, which the
declared-source guard correctly rejected. Although the same frozen screenshot
showed the soft keyboard, that state was not carried into the source-repair
error. The bounded repair attempted to swipe from inside the keyboard and was
correctly rejected by the later keyboard guard, leaving no second repair.
No blocked action or contact commit executed.

r28 passes only a boolean `soft_keyboard_present` from the already computed
current-screen assessment into declared-source validation. On a source
mismatch with that boolean true, the existing one-repair contract must return
exactly `press_back`, dismissing the keyboard and deferring field navigation
to a later observed step. It does not expose keyboard geometry, authorize the
invalid text, select a field, inject a coordinate, rewrite a task value, or add
a model call.

## r29 critic-rejected destination renavigation

The r28 formal suite completed Contacts, Calendar, and Expense with native
reward 1.0 in all three cells. In Files, the exact-target guard first prevented
selection of the similarly named `nature_sounds_SvQQ.mp3`; Search then exposed
and selected the requested `nature_sounds.mp3`. After Move to opened the
destination picker, the model proposed the bottom Move control while the
visible title was still Downloads rather than the requested Ringtones. The
consequential-action Critic correctly rejected that commit. Its rejection
string was not routed to a semantic destination-repair branch, so the single
generic repair proposed `press_back`; the destination-picker guard correctly
blocked that action because it would discard the pending move. Neither unsafe
action executed.

r29 marks this exact boundary when a Critic rejects a bottom Copy/Move commit
while the Android destination picker is visibly active. The one bounded repair
must be a tap that hits the visible, enabled, top-left `Show roots` or
navigation-drawer accessibility element. A deterministic hit test validates
the repaired tap before execution; Copy/Move, Cancel, `press_back`, waiting,
swiping, typing, and unbound content coordinates remain forbidden. Selecting
Ringtones and submitting Move stay separate later policy steps, and the final
commit still requires a fresh consequential-action Critic verdict. No target
coordinate, evaluator state, extra repair, task, seed, budget, or threshold is
introduced.

## r30 post-destination-commit convergence

The r29 Files diagnostic selected Ringtones, received a `proceed` verdict from
the consequential-action Critic, executed Move exactly once, and obtained
native reward 1.0. The next screen returned to a stale source/search view.
Because later prompts did not carry the guard's already-audited commit state,
the model selected a visually similar item and opened `Move to...` again. The
post-commit guard blocked three repeat transfers. Two generic repairs waited
without semantic progress; the third identical wait conflicted with the active
Critic constraint and stopped the diagnostic as invalid even though the native
task had succeeded. No second transaction executed.

r30 carries only the controller-owned boolean
`post_destination_commit_active` into later protocol-v2.2 policy prompts. It
does not expose native evaluator state or infer success. While active, the
policy may use reversible navigation to inspect the requested destination or
return terminal status with current-screen completion evidence, but it may not
select/long-press an item, open Move/Copy again, or wait on a stale source
screen. The deterministic guard enforces the long-press and wait restrictions.
If a repeat transfer, reselection, or wait is rejected, the sole bounded repair
must be exactly `press_back`, dismissing the current menu, selection mode, or
unintended second picker before a fresh observation. No automatic completion,
extra repair, task, seed, budget, evaluator, or threshold change is allowed.

## r31 empty-destination action semantics

The r30 formal suite again completed Contacts, Calendar, and Expense with
native reward 1.0. In Files, the requested file was selected safely and the
destination picker visibly showed `Ringtones` both as its title and as the
final breadcrumb component, with `No items` and an enabled bottom `MOVE`
control. The executor proposed a tap in an unbound title-bar area while its
summary used the word `confirm`. The prose-based consequential classifier
therefore sent this reversible, non-control tap to the commit Critic. The
Critic reasoned about a commit that had not been proposed and mistook the
native empty-folder illustration for a loading spinner. Its repair proposed
`wait`; the existing empty-picker guard correctly blocked the stall. No
incorrect commit or blocked action executed.

r31 makes the actual accessibility control hit authoritative inside an active
Android Files destination picker. Only a tap that hits the enabled bottom
Copy/Move control is a consequential commit; navigation and unbound taps are
not classified from planner prose. In a fully rendered empty directory, the
guard now rejects wait, swipe, and any tap that hits neither Copy/Move nor the
visible top-left roots drawer. The single repair must choose one of those two
visible controls according to whether the current directory matches the task
destination. The Critic prompt also records the native UI semantics: an exact
title or final breadcrumb plus the enabled commit control is sufficient
current-destination binding, while `No items` and the empty-folder
illustration are not loading evidence. The real commit still receives a fresh
same-turn Critic verdict; no coordinate, target decision, evaluator state,
extra repair, task, seed, budget, or acceptance change is introduced.

## r32 open-roots-drawer progress binding

The r31 Files diagnostic was protocol-valid: its exact-target, text-focus,
destination-back, bounded-repair, and semantic-progress audits all passed.
However, it exhausted all 20 steps with native reward 0. After the destination
roots drawer opened, the screen already showed the usable
`sdk_gphone64_x86_64` row. The model nevertheless tapped the drawer title area
twice and swiped the already complete list twice. These actions produced no
semantic progress and consumed the steps needed to enter storage, choose
Ringtones, and commit Move. No blocked action or incorrect commit executed.

r32 detects the open Android Files roots drawer from the co-occurrence of
standard visible root/category rows and their accessibility bounds. When a
usable storage row is already visible, wait, swipe, back, non-tap actions, and
taps that hit no visible enabled drawer row are rejected before execution.
The sole bounded repair must be a tap that passes an accessibility hit test
against a visible enabled row selected by the model from the unchanged
screenshot and task. The assessment exposes only booleans and counts, not row
text, bounds, or coordinates. It does not inject the storage choice, increase
the 20-step budget, add a repair, or change the task, seed, model, evaluator,
schedule, or acceptance threshold.

## r33 roots-drawer geometry discrimination

The r32 real Files diagnostic confirmed that its positive drawer path could
reject an unbound tap and repair to the visible storage row. Immediately
after entering that storage, however, the ordinary Files content page was
falsely classified as the roots drawer: horizontal category chips, a storage
breadcrumb, and two-column folder tiles repeated enough labels to satisfy the
coarse co-occurrence predicate. A bounded repair then hit the visible
Notifications tile while describing it as the storage row. The development
run was stopped after five actions, before evaluation or any destination
commit.

r33 keeps every r32 visibility, enabled-state, left-panel, storage-row, and
hit-test requirement, and adds the missing geometric discriminator. Standard
root/category controls must occupy at least four distinct vertical row bands
before the drawer is considered open. Horizontal chips and two-column content
grids therefore remain ordinary content even when their labels overlap with
drawer labels. The assessment exports only the band count and other existing
counts/booleans, never geometry, text, or coordinates. A matched negative
regression fixture reproduces the storage breadcrumb, same-row chips, and
folder grid. No task choice, coordinate, extra repair, budget, model, seed,
evaluator, schedule, or threshold changes.
