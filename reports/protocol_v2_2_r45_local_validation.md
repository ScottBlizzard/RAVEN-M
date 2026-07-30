# Protocol-v2.2 r45 local validation

Status: **PASS locally; fresh M0 Expense smoke pending**

Parent commit:
`d323351b476e6c259851364cd7e12b89246b6be5`

## Change

r45 gives both executor variants the same task-agnostic instruction for a
visibly side-by-side, horizontally clipped option row: swipe while the exact
requested label is absent and tap only once that label is visible. The shared
Protocol-v2.2 turn prompt repeats the same contract.

The text contains no app, task, category, target label, coordinate, or swipe
distance. It does not force an action or weaken a guard.

## Local evidence

- 357 tests collected and 357 passed.
- Sixteen prompt and repair-contract tests passed.
- Prompt parity tests require the same clipped-row behavior in both executor
  system prompts and in the shared Protocol-v2.2 turn prompt.
- The guidance paragraph occurs exactly once in each executor prompt.
- `compileall` and `git diff --check` passed.
- The Protocol-v1 breadth seal verified 197 files with zero failures.

## Historical compatibility audit

The focused audit found 37 retained Expense episodes with an executed action
after the final text input:

- immediate swipe: 14 successes and two failures;
- immediate tap: 20 failures and zero successes; and
- immediate long-press: one failure.

For the 21 Donation instances, immediate swipe accounted for 12 successes
and two failures; immediate tap accounted for six failures, and immediate
long-press for one failure.

The audit motivates a generic affordance instruction but does not establish a
causal success-rate claim. All prior trajectories remain immutable.

## Evidence boundary

No server/GPU result has been produced with r45 source. r44 remains a valid
task failure and live executor qualification. r43 remains locally qualified
without a new live fourth-swipe adjudication. The next admissible action is
one fresh, non-scored M0 Expense smoke after candidate freeze and preflight.
Gate D and formal execution remain unauthorized.
