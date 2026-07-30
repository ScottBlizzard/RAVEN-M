# r39 Expense-M0 failure diagnostic

Status: **valid agent/method failure; not infrastructure**  
Episode:
`nonhard_capability_v2_2_seed20260729_r39_07_M0_ExpenseAddSingle_seed20260729_a1`

## Outcome

M0 correctly enters `Educational`, `259.57`, and
`Remember to transfer funds`, but finishes with `Housing` selected instead of
`Donation` and never saves the row. The native evaluator returns 0.0, the
final screenshot shows the same failure, and the protocol audit remains valid.

The paired B3 cell solves the identical task and seed within the same
12-action budget: it horizontally swipes the category strip at steps 7-9,
selects Donation at step 10, and presses Save at step 11. This rules out a
missing UI capability or an impossible frozen budget.

## Causal trace

At step 7, M0 treats the visible horizontal category chips as a control that
should open a popup menu. The tap produces no semantic UI change, but the
executor state delta still writes memory `m_0006`: “The category selection
menu has been initiated.” It is not routed as FACT, which is correct, but its
HYPOTHESIS reliability is still 0.7526 despite zero independent confirmation.

At step 8, the identical tap again has no semantic effect. The deterministic
loop detector writes `f_0007`, an observed FAILURE routed as ALERT with
reliability 0.8295. The lifecycle gap is that `f_0007` does not contradict or
supersede `m_0006`. At step 9, the prompt therefore contains both:

- ALERT: the repeated action had no effect;
- HYPOTHESIS: the category menu has been initiated.

The Critic correctly asks for re-observation, but the Planner keeps the same
incorrect affordance model and proposes selecting Donation “from the category
menu.” Step 9 long-presses the same chip area and again produces no semantic
change.

At steps 10 and 11, the decision summaries explicitly say “swiping left,” but
the canonical actions keep `x=x2=0.5` and change `y` from 0.34 to 0.15. Those
are upward swipes, not left swipes. The schema validates each field but does
not check the semantic consistency between the sentence and the coordinates.
Both actions have no semantic effect and the budget expires.

## Root cause

The primary defect is not simply “the model chose a bad action.” It is a
missing causal lifecycle operation:

1. a zero-confirmation action-linked hypothesis is created;
2. deterministic action-outcome evidence later falsifies that hypothesis;
3. the failure and hypothesis coexist without a contradiction or supersession
   edge;
4. the stale hypothesis retains prompt authority while recovery is planned.

This is exactly the distinction the reliability-aware memory proposal needs
to make operational: labeling records as FACT/HYPOTHESIS/FAILURE is
insufficient unless later evidence can reduce or revoke the authority of the
specific earlier assumption it disproves.

The independent contributing defect is a language/geometry mismatch for
swipes. It wastes the final two actions even after the model verbally identifies
the correct recovery direction.

## Generic repair specification

### R1: action-outcome causal supersession

Persist `delta_kind` and the canonical `action_signature` with executor state
deltas. When the deterministic loop detector observes the same action twice
on the same semantic page with no effect:

- create the existing observed FAILURE/ALERT;
- find zero-confirmation `progress` or `page_hypothesis` records created by
  the immediately preceding identical action on that page;
- supersede those records with the new failure;
- preserve both records in the append-only event log, but do not route the
  superseded claim as HYPOTHESIS.

This rule is action- and evidence-based. It does not mention Pro Expense,
categories, Donation, or a particular coordinate.

### R2: swipe language-geometry consistency

When `decision_summary` explicitly says swipe left, right, up, or down, derive
the dominant direction from `(x, y) -> (x2, y2)`. If the two disagree, reject
the proposal before execution and use the existing one-repair budget. Ambiguous
sentences without an explicit swipe direction remain unaffected.

This guard catches r39 steps 10-11 deterministically and generalizes to any
GUI task.

## Regression and evidence boundary

Before any new formal run:

1. reproduce the `m_0006`/`f_0007` sequence in a unit fixture and verify that
   the hypothesis is superseded while the failure remains ALERT;
2. test accepted left/right/up/down swipes and rejected language/coordinate
   mismatches;
3. rerun memory replay, contradiction, semantic-loop, protocol-v1 seal, and
   the full local suite;
4. only then run one development-only paired Expense smoke;
5. if source changes are retained, create a new commit/tag, Gate-D freeze,
   preflight, and suite ID.

The r39 8-cell result remains immutable. No revised-source result may be mixed
with it, and this diagnosis does not retroactively change Gate E from pass.
