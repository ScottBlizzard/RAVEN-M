# Protocol-v2.2 r42 development-candidate addendum

Status: locally qualified; fresh M0 Expense smoke pending

This addendum follows the rejected r41 M0 development smoke. It preserves all
r39-r41 raw evidence and does not amend any frozen formal result.

## One-step input-activation proof

When the bounded repair for `UNFOCUSED_CLEAR_TEXT_GUARD` executes the exact
visible editable activation tap, the controller records that executed action
as proof for one subsequent policy action.

While that proof is live:

- the exact activation tap may not be repeated;
- a task-bound `type_text` action must omit `x` and `y`;
- if the visible target was empty, `clear_text` must be false; otherwise the
  model's proposed value is preserved; and
- the model must still provide the task text and its provenance.

The proof is consumed by the next executed action regardless of its type. It
does not infer focus from pixels, supply a coordinate or value, survive an
intervening action, or change AndroidWorld execution semantics.

## Visible-layout recovery contract

When an exact action repeat is rejected because the preceding unchanged
transition asserted only unverified progress or a page hypothesis, the single
repair must discard that hypothesis and re-read the visible layout:

- side-by-side options or a carousel require navigation along the horizontal
  axis, changing x while holding y approximately fixed;
- vertically stacked options require the vertical axis; and
- an arbitrary axis reversal is not a valid recovery merely because it
  differs from the blocked action.

This is repair-prompt guidance, not a controller-authored gesture. The model
still chooses every coordinate and direction from the current screenshot.

## Frozen invariants

r42 changes no model, seed, task instance, evaluator, action or model-call
budget, output schema, memory schema, memory threshold, readiness bound, or
global no-effect threshold. The existing one-repair limit remains in force,
and Protocol v1 remains isolated.

## Qualification boundary

The only authorized live action after local qualification is one fresh,
non-scored M0 Expense smoke. A pass may close the retained paired development
check with the earlier r40 B3 pass, but those cells are not pooled into a
formal result. Gate D requires a separate decision and freeze.

## Live disposition

The M0 Expense smoke rejected r42 at the action budget. The one-step input
proof worked and category navigation stayed horizontal, but the unconditional
three-identical-coordinate-action guard blocked a fourth productive left
swipe after three verified semantic changes. See
`reports/protocol_v2_2_r42_m0_expense_smoke.md`. Gate D remains unauthorized.
