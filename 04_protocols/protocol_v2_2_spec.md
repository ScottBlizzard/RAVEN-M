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
- Text declared as `task_literal` must be a case-insensitive,
  whitespace-normalized substring of TASK. Text declared as `current_screen`
  must similarly match a visible accessibility text, content description,
  hint, or tooltip on the current turn. A mismatch is rejected before
  execution, and the repaired action is checked again so changing only the
  provenance label cannot authorize invented text. The assessment exposes
  only the declared origin, source-value count, and a matched boolean.
- When declared-source repair can see an empty editable whose semantic role
  matches a remaining TASK value, it asks the model to fill that value now
  rather than perform generic navigation. If no such field is visible, the
  repair remains a single non-commit action and may not repeat navigation that
  already produced no semantic progress. No field coordinate is injected and
  no action is silently rewritten.
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
- Relative dates are not re-resolved after navigation.
- A Critic `reobserve` or `recover` verdict creates a binding constraint that
  blocks the same action until a materially different action changes semantic
  state.
- An information-return completion is rejected when the answer is only a
  clipped prefix in a dense cell/list; the full text must be readable in a
  detail or second view.
- A same-turn Critic adjudicates consequential commits. Save/Send/Delete and
  final Move/Copy confirmation require the exact task target and
  destination/value to be visibly bound on the current screen.
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
