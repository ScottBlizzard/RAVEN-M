# Protocol-v2.2 r44 development-candidate addendum

Status: locally qualified; fresh M0 Expense smoke pending

This addendum follows the invalid, infrastructure-contaminated r43 M0
attempt. It preserves the r43 policy candidate and all prior raw evidence.
It does not reinterpret that attempt as a method result.

## Retry-idempotent clear-and-type execution

AndroidEnv retries a device-specific ADB command after a timeout. Its former
text path issued clear and type as separate calls, so a timed-out
non-idempotent `input text` call could partially mutate the field before its
retry appended the full value.

r44 changes only a non-empty model action with `clear_text=true`:

1. if the model supplied a visible target coordinate, execute that focus
   click first, preserving AndroidWorld's ordering;
2. issue select-all, delete, a one-second settling interval, and every
   model-authored input token in one compound ADB shell request;
3. press Enter only after that compound request returns successfully; and
4. propagate a final compound-request error through the existing episode and
   runner infrastructure path.

Every AndroidEnv retry of the compound request therefore begins by clearing
any prefix left by the preceding attempt. Text remains tokenized with
AndroidWorld's own formatter, including explicit newline key events. The
request timeout remains 10 seconds for short values and scales with the
number of input operations to a hard ceiling of 120 seconds for long text.

`clear_text=false`, empty text, and every non-text action keep their existing
execution paths. r44 adds no text, coordinate, policy action, model call,
memory item, evaluator signal, or recovery decision.

## Historical compatibility boundary

The audit parsed 6,492 executed steps across 404 trajectory files with no
parse failures. It found 913 executed text actions:

- 739 explicitly used `clear_text=true` and would take the retry-idempotent
  executor path;
- 174 used `clear_text=false` or omitted it and remain unchanged;
- among the 739 applicable actions, 736 supplied coordinates and three used
  the already-focused control; and
- 423 contained one input token, 303 contained 2-9, 12 contained 10-49, and
  one contained 181.

The single 181-token historical value motivated the bounded adaptive timeout.
One applicable historical value contained a newline; the compound builder
preserves it as an Enter key event between token groups.

## Frozen invariants and qualification boundary

r44 inherits r43's locally qualified progress-conditioned swipe rule. It
changes no model, seed, task instance, evaluator, action or model-call budget,
schema, memory behavior, controller guard, or Protocol-v1 artifact.

The only authorized live action is one fresh, non-scored M0 Expense smoke.
That smoke must first demonstrate exact, uncorrupted entry of `Educational`
and then reach the r43 swipe boundary. It cannot be pooled with prior
development cells or authorize Gate D or formal execution by itself.

## Live disposition

The r44 M0 smoke was a valid task failure at the 12-action budget. A compound
Note request timed out on its first internal attempt, and the retry produced
the exact text once with no duplicated prefix, qualifying r44's executor
repair under the target failure mode. The run executed only three swipes, so
r43's fourth-swipe boundary was not reached. Donation was selected on the
final action, leaving Save unexecuted after an earlier no-effect tap on a
horizontally clipped option row. See
`reports/protocol_v2_2_r44_m0_expense_smoke.md`.
