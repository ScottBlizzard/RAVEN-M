# Protocol-v2.2 r41 local validation

Status: **PASS locally; M0 Expense smoke pending**

Parent commit:
`bcd75f88d948a05294e871a205453fc69aa1613f`

## What changed after r40

r41 closes the live boundary exposed by `m_0008`: the deterministic failure
now supersedes action-linked zero-confirmation hypotheses written in both the
current failure transition and the immediately preceding identical
transition.

Two narrow action-efficiency guards are also added:

- an exact immediate repeat is rejected when the preceding unchanged action
  asserted only unverified progress/page identity;
- a tap on the same already-focused empty editable is rejected.

Both use the existing one-repair allowance and require the model to return a
different valid action. No action, coordinate, task value, or evaluator state
is injected.

## Local evidence

- 345 tests collected and 345 passed.
- Controller integration tests exercise both new pre-execution guards through
  initial response, validation rejection, repair prompt, repaired response,
  and final schema validation.
- The memory regression reproduces two progress claims—one from the prior
  action and one written in the failure transition—and verifies that both are
  superseded by the deterministic failure and absent from active retrieval.
- `compileall` and `git diff --check` passed.
- The protocol-v1 breadth seal verified 197 files with 0 failures.

## Compatibility audit

Across 377 existing trajectory files, a blanket first-repeat rule would affect
78 actions. The r41 evidence condition narrows this to 20: 13 repeated actions
still produced no semantic change, while 7 were followed by a later semantic
update.

Those seven cases are retained as compatibility risk rather than hidden. The
rule does not declare the first action failed, does not change the global
threshold, and permits a materially different same-turn recovery. Its purpose
is to prevent a model-authored, unverified progress claim from authorizing the
exact action again.

## Evidence boundary

No live server/GPU result has been produced with r41 source. The r40 B3 pass
and M0 failure remain immutable development evidence. The next admissible step
is one fresh, non-scored M0 Expense smoke. Gate D and formal execution remain
unauthorized.
