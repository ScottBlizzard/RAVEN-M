# Protocol-v2.2 r41 development-candidate addendum

Status: rejected by M0 Expense development smoke

This addendum follows the rejected r40 paired smoke. It does not modify r39
or r40 evidence.

## Complete causal supersession

When the repeated-action/no-effect detector writes a deterministic failure,
it supersedes every same-page, same-action, zero-confirmation
`progress`/`page_hypothesis` record created either:

- by the immediately preceding identical action; or
- earlier in the current failure transition.

All records and every supersession event remain append-only. Independent
facts and action-unrelated hypotheses are unaffected.

## Unverified-progress exact-repeat guard

If an executed action:

1. produces no semantic UI change; and
2. its own state delta asserts unverified `progress` or `page_hypothesis`,

then an immediately following exact repetition on the same semantic page is
rejected before execution. The existing single repair must choose a
materially different action. Any intervening executed action disarms this
narrow condition. The global two-no-effect threshold is unchanged.

This rule treats a model-authored progress claim as insufficient authority to
repeat the same action when deterministic semantic evidence did not confirm
that claim. It does not declare the first action an infrastructure failure or
silently rewrite it.

## Focused empty editable guard

A tap that hits the same visible, enabled, focused, empty editable control is
rejected before execution. An empty field has no cursor-position ambiguity,
so another tap adds no value. The bounded repair may type an exact remaining
task-bound value without coordinates and with `clear_text=false`, or choose a
different non-commit action. The controller supplies neither text nor
coordinates.

## Qualification boundary

- Protocol v1 remains isolated.
- Historical replay is compatibility evidence only, not scored evidence.
- The next live action is one fresh, non-scored M0 Expense smoke.
- A passing M0 smoke closes only the paired development check because the r40
  B3 cell already passed. It may authorize Gate-D preparation but cannot be
  pooled into a formal result.
- Any formal Gate E still requires a new freeze, preflight, and all eight
  fresh cells.

## Live disposition

The M0 Expense smoke rejected r41. The exact category tap repeat was blocked,
but its repair stayed on an unsupported vertical axis. Accessibility also
failed to expose the visibly focused empty input soon enough for the
focused-empty tap guard. See
`reports/protocol_v2_2_r41_m0_expense_smoke.md`. Gate D remains unauthorized.
