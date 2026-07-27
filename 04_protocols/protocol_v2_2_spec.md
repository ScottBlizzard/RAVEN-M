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
- After three consecutive mismatched or missing accessibility observations,
  the controller performs at most one audited AndroidWorld accessibility
  refresh, then continues within the original twelve-observation bound.
- A fourth consecutive identical `tap` or `long_press` coordinate is rejected
  even if screenshot-only state hashes change; the bounded repair must
  recalculate the coordinate or choose a different recovery action.
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
- An executed tap inside the enabled bottom `COPY`/`MOVE` control creates an
  auditable post-destination-commit state. Later long-press selection or a
  second bottom commit is rejected before execution; bounded waiting and
  ordinary navigation remain available for visible destination verification.

## Visible infrastructure failures

- ANR, app-crash, and system-process failure text is separate from ordinary
  form validation.
- Such a screen terminates the current attempt with typed infrastructure code
  `INFRA_EMULATOR_ANR`.
- The attempt is archived and the emulator is cold recovered.
- Two consecutive failures of the same class stop the gate.

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
