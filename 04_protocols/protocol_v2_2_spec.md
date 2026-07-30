# AndroidWorld protocol v2.2 exploratory specification

Protocol ID: `androidworld_protocol_v2_2_exploratory`

Protocol v2.2 inherits the paired non-Hard Gate-E design, task instances,
model identity, action budgets, model-call budgets, and acceptance thresholds
from v2.1. It changes only generic readiness, infrastructure classification,
memory authority, and Critic enforcement.

## Readiness

- `open_app` remains one policy action.
- Bounded post-launch observations do not consume policy actions or model
  calls.
- The readiness audit records every observation and whether accessibility was
  reached.
- The bound is twelve observations with a 0.75-second retry delay.
- Readiness requires an accessibility package matching the foreground package;
  a stale tree from the previous app does not satisfy the bound.
- The same foreground/tree consistency check runs after every action, because
  chooser and resolver overlays can temporarily change the foreground
  activity even when the main app remains open.
- Same-package agreement is not sufficient when an action materially changes
  the screenshot but the accessibility semantic hash remains exactly equal to
  the preceding state. Such a cross-modal mismatch is treated as a stale tree
  and retried inside the existing twelve-observation readiness bound without
  consuming a policy step or model call. The threshold is a one-percent ratio
  of pixels with at least one changed channel; no image content or coordinate
  is inserted into the model prompt.
- Coordinate normalization examples distinguish layout regions: on the
  standard 2400-pixel portrait screen, `y=192` maps to `0.08` and is a typical
  top-app-bar icon center, while `y=438` maps to about `0.1826` and is content.
  Search/menu actions must not copy the content-row example.
- Every observation repeats the action fields whose omission would consume the
  only bounded repair before semantic validation: `long_press` requires
  `x`, `y`, and `duration_ms`; `swipe` requires both endpoints and
  `duration_ms`; `wait` requires `duration_ms`. The strict schemas are not
  weakened and no missing value is silently inserted.
- A coordinate-bearing `type_text` causes AndroidWorld to click before typing.
  If an empty text field visibly already has a caret, the model must preserve
  that focus by omitting `x,y` and setting `clear_text=false`. Coordinates are
  reserved for a visible text field that is not already focused; the controller
  does not silently strip or retarget them.
- The focused-input guard derives only `present`, `focused_count`, and `empty`
  from current visible `is_editable`/`is_focused` accessibility flags. When a
  focused input exists, coordinate-bearing `type_text` is validation-blocked;
  clearing a focused empty field is also blocked. The one bounded repair must
  explicitly preserve text provenance, omit coordinates, and avoid clearing
  the empty field. No accessibility bbox enters the model prompt.
- After three consecutive mismatched or missing accessibility observations,
  the controller performs at most one audited AndroidWorld accessibility
  refresh, then continues within the original twelve-observation bound.
- A fourth consecutive identical `tap`, `long_press`, or canonical `swipe`
  coordinate action is rejected even if screenshot-only state hashes change;
  the bounded repair must recalculate the coordinate or choose a different
  recovery action.
- Android copy/move destination pickers treat `No items` as a stable empty
  folder, not a loading signal; one wait is the maximum before navigating to
  the exact storage root and destination.
- Persistent bottom `CANCEL` and `COPY`/`MOVE` controls identify the
  destination-picker state. Navigation must use the picker's drawer directly;
  Back is not a folder-navigation action because it exits the picker and loses
  the pending operation.
- The controller deterministically rejects `press_back` on that state before
  execution. The bounded same-screen repair must choose the picker drawer or
  another non-exit action, and the rejection is recorded in the guard audit.
- Before a Files long-press, the nearest full accessibility filename must
  exactly equal the task-literal filename. A different same-extension name,
  a same-prefix variant, or an off-screen exact target is rejected before
  execution and must recover through Search, list, detail, or a corrected
  exact coordinate.
- The one bounded repair distinguishes a structural response error from a
  semantic action rejection. A structural error retains the format-repair
  contract. A guard or binding-constraint rejection requires a materially
  different GUI action on the same screenshot; repeating the rejected action
  type and coordinates is invalid.
- Exact-target rejection states whether the task-literal filename is visible
  and names the full accessibility filename nearest to the proposed
  coordinate. The one same-screen repair may not use `long_press`, regardless
  of whether the exact target is in the visible accessibility candidate set.
  It must change the information state through Search, view change, or
  scrolling. Selection may be attempted only on a later policy step after the
  resulting screen is observed. No accessibility-derived target coordinate is
  exposed, and this evidence never comes from evaluator state.
- An executed tap inside the enabled bottom `COPY`/`MOVE` control creates an
  auditable post-destination-commit state. Reversible inspection of the exact
  item remains available, but a second `Move to`, `Copy to`, or bottom commit
  is rejected before execution.
- A visible focused editable node or a visible Android Latin input-method
  package is current-screen evidence that text input is already active.
  A coordinate-bearing `type_text` that does not match a visible, enabled,
  editable accessibility element is rejected before AndroidWorld can click
  away from that input. The bounded repair preserves the exact text and
  provenance while removing `x,y`; keyboard presence alone does not imply an
  empty field or disclose any input coordinate. A coordinate that does match
  a visible editable is an explicit field switch and remains executable even
  while the soft keyboard is present.
- When neither focused-editable nor soft-keyboard evidence shows active text
  input, a coordinate-bearing `type_text` must hit a visible, enabled,
  editable accessibility element. A miss is rejected before execution. Its
  bounded repair must first activate or reopen an input with a non-text
  reversible action and observe the next screen; no editable bbox or target
  coordinate is disclosed.
- Even when that inactive-input coordinate matches a visible editable,
  `clear_text=true` is rejected. AndroidWorld would click and immediately send
  Ctrl+A, which can race focus activation and select surrounding UI content.
  The bounded repair must first tap the same visibly supported input and
  observe the next screen. After a focused editable or soft keyboard proves
  readiness, a later empty-field edit omits coordinates and uses
  `clear_text=false`. Keyboard-active explicit field switching is unchanged.
- When input is active and the coordinate matches the sole visible editable,
  the coordinate is redundant rather than a field switch and is rejected.
  The focused-input repair removes `x,y`; if the matched editable is empty it
  also sets `clear_text=false`. A coordinate may still switch fields when
  multiple visible editables support a genuine target change. This assessment
  exposes only editable counts, a matched boolean, and matched emptiness.
- While a soft keyboard is visible, a swipe whose start point hits a visible
  keyboard accessibility element is rejected before execution. Its bounded
  repair must dismiss the keyboard with `press_back` and observe a later
  screen before attempting navigation. A field-role repair may instead type
  the exact requested value directly into a visibly supported compatible
  field, but it may not swipe while the keyboard is active. The assessment and
  audit expose only booleans, package names, and counts, never keyboard bboxes,
  coordinates, text, field labels, or evaluator state.
- When bottom Cancel and Copy/Move controls prove that the Android destination
  picker is active and a visible marker shows that the current directory is
  empty, `wait` and `swipe` are rejected. Neither action can reveal a sibling
  folder. The bounded repair must tap a visible control: bottom Copy/Move when
  the current directory is the TASK destination, otherwise the top-left
  navigation drawer. It may not press back or guess a content coordinate. The
  assessment exposes only the action type, booleans, and an empty-marker count,
  never directory text, geometry, TASK values, or evaluator state.
- Text declared as `task_literal` must be a case-insensitive,
  whitespace-normalized substring of TASK. Text declared as `current_screen`
  must similarly match a visible accessibility text, content description,
  hint, or tooltip on the current turn. A mismatch is rejected before
  execution, and the repaired action is checked again so changing only the
  provenance label cannot authorize invented text. The assessment exposes
  only the declared origin, source-value count, and a matched boolean.
- Accessibility absence alone is not sufficient to reject a terminal
  information-return answer that declares `current_screen`. When exact
  accessibility matching fails, one same-turn visual-source Critic may accept
  the unchanged candidate only if its full text is readable in the screenshot
  and visibly bound to the TASK target. The Critic cannot rewrite the answer,
  cite memory, inspect evaluator state, authorize `type_text`, or use another
  screenshot. Rejection requires a reversible detail/re-observation action in
  the existing single repair; the same answer may not be repeated. Candidate
  hashes, verdicts, and model-call IDs are audited, and a repeated candidate in
  the same turn reuses the cached verdict.
- When declared-source repair can see an empty editable whose semantic role
  matches a remaining TASK value, it asks the model to fill that value now
  rather than perform generic navigation. If no such field is visible, the
  repair remains a single non-commit action and may not repeat navigation that
  already produced no semantic progress. No field coordinate is injected and
  no action is silently rewritten.
- If a declared-source mismatch occurs while the current accessibility state
  proves that a soft keyboard is visible, the same bounded repair must return
  `press_back` exactly. It may not swipe within the keyboard, type a different
  value, tap, or commit. Only the keyboard-present boolean is carried into the
  validation audit; keyboard geometry and field coordinates remain hidden.
- For a coordinate-bearing `task_literal` edit, the controller derives coarse
  semantic roles from the task sentence/line containing that literal and the
  visible label metadata of the editable hit by the coordinate. When both
  sides are adjudicable, their roles must intersect; Search, Filter, and Query
  fields are generic query targets. A disjoint value/field pairing is rejected
  before execution, and its repair must keep the exact value and provenance
  while choosing a visibly supported role-compatible field. Only role groups
  and counts enter the audit.

## Visible infrastructure failures

- ANR, app-crash, and system-process failure text is separate from ordinary
  form validation.
- Such a screen terminates the current attempt with typed infrastructure code
  `INFRA_EMULATOR_ANR`.
- The attempt is archived and the emulator is cold recovered.
- Two consecutive failures of the same class stop the gate.
- On Windows, emulator stop/start subprocess output is redirected to
  file-backed recovery logs. This prevents long-lived emulator or ADB
  descendants from retaining captured pipes and preserves the existing
  bounded recovery timeouts.
- AndroidWorld's exact `Could not get a11y tree.` runtime error is typed as
  `INFRA_EMULATOR_LOST` for Gate-E orchestration. The failed attempt is
  archived and consumes the same bounded emulator-recovery allowance; it is
  not converted into a policy or model failure.

## Memory authority

- One model-authored direct-screen state delta is observed evidence routed at
  most as HYPOTHESIS.
- Repeating the same model-authored claim on a later screenshot remains
  HYPOTHESIS. Model agreement with itself is not independent verification.
- FACT promotion requires non-model independent evidence; deterministic
  failures retain their explicit controller provenance.
- Page/screen identity and page hypotheses default to `same_page` and expire
  after semantic page change.
- Current-screen evidence outranks contradictory memory.

## Planner and Critic

- Planner required variables and current subgoal are frozen anchors.
- Protocol-v2.2 freezes the task object's natural-language goal before
  `initialize_task` and uses that same goal for live policy prompts,
  provenance/adjudication, and the episode summary. This prevents environment
  setup from silently replacing an already concrete absolute target with
  relative calendar language. The audit records both forms when they differ.
  The frozen goal comes only from the task's existing user-facing `goal`; it
  is not reconstructed from task parameters, evaluator state, or answers.
- Relative dates are not re-resolved after navigation.
- Relative calendar language is grounded before day selection. The next named
  weekday is its first strictly future occurrence and that weekday after next
  is the following occurrence; when the visible reference date already has
  that weekday, the offsets are +7 and +14 days. The policy should use a
  visible month grid or date picker to select the computed date directly and
  verify the absolute date before answering. In a month grid, `weekday after
  next` is one row lower in the same weekday column than the first future
  occurrence; the day number must be verified before the tap.
- Date-wheel movement is directional progress only when the next visible
  selected date is closer to the computed target. A swipe that moves the value
  farther away must be reversed on the next step and may not be repeated.
- When the identical-coordinate guard rejects repeated stepwise navigation,
  the bounded repair must use a materially different visible control or a
  higher-level selector. Perturbing or repeating the same arrow, swipe, or
  target remains forbidden; the three-action cross-state cap is unchanged.
  The loop-specific repair contract precedes the original prompt so it remains
  the highest-salience instruction in the sole bounded repair.
- For Android Files source navigation, an initial empty Downloads view is not
  a reason to exit and reopen the app. The policy uses the visible top-left
  roots drawer to reach the requested storage. If an `open_app` action is
  nevertheless rejected as one half of an `open_app`/`press_back` loop, its
  sole repair may neither reopen nor go back. On the launcher it must tap an
  already visible target-app icon or swipe upward to reveal the app drawer,
  then wait for a later observed step before selecting the app. No icon
  coordinate is injected and the guard does not rewrite the action.
- A Critic `reobserve` or `recover` verdict creates a binding constraint that
  blocks the same action until a materially different action changes semantic
  state.
- An information-return completion is rejected when the answer is only a
  clipped prefix in a dense cell/list; the full text must be readable in a
  detail or second view.
- A screenshot-visible answer missed by accessibility first requires the
  bounded visual-source verdict above. M0 then still requires its independent
  completion-candidate verdict; source acceptance is not completion
  acceptance.
- A same-turn Critic adjudicates consequential commits. Save/Send/Delete and
  final Move/Copy confirmation require the exact task target and
  destination/value to be visibly bound on the current screen.
- If that Critic rejects a bottom Copy/Move commit while an Android
  destination picker is visibly active, the sole repair must tap the visible,
  enabled top-left `Show roots`/navigation-drawer element. A deterministic
  accessibility hit test rejects `press_back`, Cancel, another commit, or an
  unbound coordinate before execution. Destination selection and a later
  Critic-adjudicated commit remain separate policy steps.
- After one audited bottom Copy/Move commit executes, later policy prompts
  receive only a controller-owned `post_destination_commit_active` boolean,
  never evaluator state. They may reversibly navigate to inspect the requested
  destination or complete from current-screen evidence, but may not
  select/long-press an item, start another Move/Copy, or wait on stale source
  state. Any such blocked action has one exact `press_back` repair to dismiss
  the menu, selection, or unintended second picker before re-observation.
- If the M0 completion Critic rejects a terminal response while that
  post-commit state is active, the same single repair is exact `press_back`.
  It leaves the stale search/menu/picker state for later reversible
  destination verification; wait, mutation, selection, a second transfer, and
  immediate completion are not valid repairs.
- Within an active Android Files destination picker, consequential-action
  classification uses an accessibility hit on the enabled bottom Copy/Move
  control rather than action-summary prose. In a rendered empty current
  directory, wait, swipe, and taps that hit neither Copy/Move nor the enabled
  top-left roots drawer are rejected before execution. The sole repair must
  choose one of those visible controls without receiving a target coordinate.
- For same-turn review of the actual Copy/Move commit, an exact task
  destination visible as the current title or final breadcrumb component plus
  the enabled bottom commit control is sufficient destination binding.
  `No items` and the native empty-folder illustration indicate a valid empty
  directory and are not, by themselves, evidence of loading or an unbound
  destination.
- An open Android Files roots drawer is detected only from multiple standard
  visible root/category rows with usable accessibility bounds, including at
  least four distinct vertical row bands. This excludes horizontal category
  chips, storage breadcrumbs, and two-column folder grids that reuse the same
  labels. If a storage row is already visible, the next action must tap a
  visible enabled drawer row; wait, swipe, back, non-tap actions, and unbound
  title/menu taps are rejected before execution. The bounded repair receives
  no row text, bounds, target choice, or coordinate and must independently
  produce a tap that passes the same visible-row hit test.
- Planner completion evidence IDs may cite routed FACT only. HYPOTHESIS can
  guide verification but cannot satisfy completion.

## Baseline fairness

B3 summary prompt, schema, trigger schedule, context, and model-call budget are
unchanged. Unsupported B3 summary claims are analyzed as baseline behavior,
not repaired using task-specific logic.

## Gate sequence

The first four cells may be run only as a separate non-scored development
smoke. The scored eight-cell Gate E starts from empty directories after a
frozen source tag and clean preflight. No evidence is pooled across protocol
versions or development/scored runs.
