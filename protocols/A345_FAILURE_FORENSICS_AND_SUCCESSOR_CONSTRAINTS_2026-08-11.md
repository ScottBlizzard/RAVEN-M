# A3-A7 failure forensics and A8/A9 successor constraints

Date: 2026-08-11
Status: evidence-grounded design basis; no generation calls

## Finding

The poor A3-A7 results are not adequately explained by infrastructure. The
valid trajectories show that the mechanisms usually failed to close the chain
`write -> relevant retrieval -> leave the repeated action/state -> task
success`. The A3-A5 labels denote lightweight representation ports, not full
inheritance of the cited systems' learned models, planners, critics or action
repair components.

## Quantitative evidence

- A3: 1 valid gate episode, 0 success; 12/34 structured writes and 33/34
  non-empty reads.
- A4: 1 valid gate episode, 0 success; the same weak donor was injected on all
  34 steps.
- A5: 1 valid gate episode, 0 success; 0/34 compliant graph writes, so the
  proposed memory never activated.
- A6: 19 valid episodes, 0 success, versus A0's 4 successes. A6 used 625
  actions and 2,674,422 tokens, about 1.98x and 2.10x A0 respectively. Of 625
  writes, 250 followed a transition with changed-pixel fraction below 0.001.
  Among 243 such positions followed by a non-empty read, 131 repeated the same
  canonical action.
- A7's transparent 19-task control is 19/19 infrastructure-valid with 4
  successes and reward sum 4.0. Its retrospective preservation gate is 3/4.
  Several gains, including OsmAndMarker and the read-only Sports success,
  occurred while the ledger was inactive; activity alone therefore cannot be
  credited as the cause.

Canonical A7 closure evidence:
`evidence/a678/A7_TRANSPARENT_19_TASK_CONTROL.json`.

## Frozen successor constraints

1. Do not require the policy model to emit an auxiliary memory syntax.
2. Normal steps should be silent; never write and replay every transition.
3. Visible pixel change is not semantic progress or task completion.
4. Record exact recurrence and failed action evidence, not only positive model
   prose.
5. No evaluator, hidden UI tree, package/activity or future frame may affect a
   memory decision.
6. No added model call, action guard or action override in A8-v2/A9; those are
   separate causal interventions if studied later.
7. Activation is exposure, not benefit. Report post-activation loop escape and
   task reward separately.
8. Run Expense, Retro, Calendar and Sports-Duration first. A8-v2/A9 must pass
   4/4 before their remaining 15 tasks are released.

## Successor mapping

- A8-v2 aggregates canonical action families on an exact visible screen,
  counts no/negligible-change outcomes and reports exact routes returning to
  the same screen.
- A9 remains empty on ordinary steps and emits a one-shot canary only for
  repeated text entry, a stationary exact screen or an exact period-2/3 route.

Neither successor retroactively changes A3-A8-v1. Every version keeps a new
experiment ID and requires a fresh zero-generation preflight and live receipt.
