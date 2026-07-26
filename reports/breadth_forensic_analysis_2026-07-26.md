# Frozen breadth forensic analysis

Date: 2026-07-26  
Scope: 95 completed `hard_v1_breadth` episodes plus protocol/source audit  
Decision: **do not start the remaining protocol-v1 cells**

## Executive diagnosis

The breadth run is operationally complete, but it cannot be treated as a
clean confirmatory comparison.  The low score is caused by a combination of:

1. one definite task-interface incompatibility;
2. a severe GUI action-loop problem shared by all variants;
3. an over-conservative and delayed M0 completion contract;
4. a Hard-task capability floor that was not covered by the non-Hard
   engineering gates.

The correct next move is a separately labelled exploratory protocol v2, not a
semantic "hotfix" to frozen protocol v1 and not another automatic 269-cell
run.

## P0: fifteen breadth cells were structurally unable to score

`SportsTrackerActivitiesOnDate`,
`SportsTrackerTotalDistanceForCategoryOverInterval`, and
`SportsTrackerTotalDurationForCategoryThisWeek` inherit AndroidWorld's
`InformationRetrieval` evaluator.  Its success check reads:

```python
proto_utils.check_agent_answer(env.interaction_cache, self.task)
```

AndroidWorld fills `interaction_cache` only when the agent executes an
upstream `answer` action.

Neither frozen RAVEN action schema contains `answer`, the executor prompts do
not teach it, and `AndroidWorldAdapter` cannot map or execute it.  A model
could calculate the exact answer and say `status=done`, but
`interaction_cache` would remain empty and the evaluator would return zero.

Consequences:

- 15 of the 95 breadth cells were guaranteed zero by protocol capability;
- 36 of the complete 364-cell schedule have this incompatibility;
- 21 still-unrun cells would waste compute for the same reason;
- the existing protocol audit checked hashes, resets, schemas, and logging,
  but not task-required action coverage.

This is a semantic protocol defect.  It must not be repaired inside frozen
v1 while retaining confirmatory status.

## The floor remains after excluding the unsupported tasks

Removing the 15 structurally unsupported cells leaves:

| Supported-cell result | Count |
|---|---:|
| Success | 1 |
| Budget exhausted | 50 |
| Model declared infeasible | 14 |
| Premature completion | 14 |
| Invalid output after repair | 1 |
| Total | 80 |

Thus supported-task success is still only 1/80 (1.25%).  Only one of the 16
supported task instances had any successful variant.  The missing `answer`
action explains an important part of the audit failure, but not the general
performance floor.

## P1: GUI control repeatedly enters action loops

Among the 80 supported cells:

- 59 repeated an identical action at least three consecutive times;
- 32 repeated an identical action at least ten consecutive times;
- 477 executed actions produced no screenshot change.

Representative cases include:

- B1 `OsmAndTrack`: 98 identical consecutive actions within 120 steps;
- B2 `OsmAndTrack`: 100 identical consecutive actions;
- B2 `RecipeAddMultipleRecipesFromImage`: 58;
- B3 `ExpenseAddMultipleFromGallery`: 58;
- M0 `RecipeAddMultipleRecipesFromMarkor2`: 57.

Some repeated swipes are legitimate list traversal, but runs of tens of
identical actions, repeated state-action pairs, and repeated no-change
transitions are not.  The controller currently reports only pixel change;
it does not enforce a recovery policy when the same action has already failed.

M0 detected 46 loops and invoked the critic 46 times.  Every critic response
was `reobserve`.  Of 44 cases with a following action, 14 (31.8%) immediately
repeated the identical action.  Therefore loop detection is instrumented but
not behaviorally binding.

## P1: M0 is active but cannot terminate efficiently

M0 is not an empty or broken code path:

- 758 decisions received memory bundles;
- 457 decisions cited memory;
- 270 history/planner/critic model calls were made;
- all 19 memory audits passed;
- routing produced 150 FACT, 2,777 HYPOTHESIS, 105 ALERT, and 5,684 SUPPRESS
  decisions.

However, M0 finished 0/19 tasks and all 19 reached the task budget.  It used
approximately 33% more model calls, 53% more tokens, and 52% more wall time
than B3.

The completion contract requires a currently routed FACT citation before
`status=done`.  Across five M0 episodes the model attempted to finish 13
times, but validation rejected each attempt and converted it into another
action.  This delayed handshake is brittle:

- completion evidence written on one step may not route as FACT on the next;
- the executor may cite an older HYPOTHESIS instead of the new evidence;
- the critic may say `proceed` while the validator still rejects completion;
- near the budget, repeated wait-and-repair cycles cannot converge.

This gate does not alone explain every evaluator failure—the evaluator still
runs at budget exhaustion—but it adds cost, consumes steps, and can continue
acting after the model believes the task is complete.

## P2: selective trust is not yet calibrated by action risk

Of 462 M0 cited memory items:

| Route cited | Count | Share |
|---|---:|---:|
| FACT | 63 | 13.6% |
| HYPOTHESIS | 388 | 84.0% |
| ALERT | 11 | 2.4% |

All 16 memory-citing `type_text` decisions cited HYPOTHESIS rather than FACT.
This is not automatically wrong if the current screen independently verifies
the value, but the implementation does not record whether memory merely
suggested an inspection or directly authorized a state-changing action.

At the same time, completion is subject to a strict binary FACT gate.  The
system is therefore permissive in some state-changing intermediate actions
and excessively conservative at termination.  This is the more useful
research finding: authority should be calibrated to action risk, rather than
controlled by one global trust threshold.

## Why the pre-Hard gates did not catch this

The development gates successfully established parsing, logging, reset
behavior, context limits, and memory invariants.  They were not a sufficient
task-capability gate:

- G3 passed on schema validity with 2/5 easy/medium successes;
- G4 used Contacts, Markor, Clock, Expense, and Files tasks;
- G7 M0 achieved 4/8 on non-Hard development tasks;
- none required the AndroidWorld `answer` action;
- none reproduced the long multi-app, visual extraction, aggregation, and
  60–120-step control demands that dominate the Hard manifest.

The project passed an engineering smoke test and then jumped directly to a
scientifically much harder distribution.

## Recommended protocol v2

Protocol v1 should remain immutable as a documented diagnostic pilot.
Protocol v2 should make the following semantic changes and receive a new
preregistration/tag.

### 1. Complete the task-action interface

- Add canonical `answer{text}` support to both action schemas.
- Map it to AndroidWorld `JSONAction(action_type="answer", text=...)`.
- Teach the executor when a goal asks for a returned answer.
- Add a manifest audit that maps every selected task class to its required
  action capabilities and fails before scheduling if any are unsupported.

### 2. Replace the contradictory text rule

The current prompt says `type_text` may contain only a value explicitly
requested by the task.  Several selected tasks require typing values read or
computed from the GUI: products, expenses, recipes, note contents, and video
transcriptions.

Protocol v2 should permit a value when it is either explicitly given by the
task or directly observed/derived as a required task variable, while still
forbidding invented optional data.

### 3. Make loop recovery enforceable

- Detect repeated `(page signature, action)` pairs.
- After two no-effect repetitions, temporarily block the same action on the
  same page.
- Require the critic to select a concrete alternative class: re-open app,
  navigate back, change scroll direction, change target, or safely fail.
- Log whether the next action obeyed the recovery constraint.

### 4. Use risk-sensitive authority

Use different evidence thresholds for:

- observation/navigation;
- reversible edits;
- irreversible save/send/delete actions;
- terminal completion.

HYPOTHESIS may guide inspection.  A state-changing or irreversible action
should require either current-screen evidence or a valid FACT.  Completion
should accept same-turn verified screen evidence after critic validation,
rather than relying on a one-step delayed FACT citation that can disappear
from routing.

### 5. Add a capability-focused development gate

Before another Hard breadth run, test:

- one information-retrieval task using `answer`;
- one derived-text/arithmetic task;
- one file operation;
- one long multi-app task;
- one known-solvable calendar task;
- one memory-intensive extraction task.

The gate should require:

- every task's required action type is executable;
- 100% correct `answer` propagation to `interaction_cache`;
- no unsupported task classes;
- no three consecutive identical no-effect actions;
- M0 can complete without a FACT-handshake deadlock;
- at least 20% overall task success before a larger run.

## Efficient experiment plan

Do not rerun 364 cells immediately.

1. Unit and integration fixes locally; no GPU run.
2. Six-task capability smoke with B3 and M0: 12 episodes.
3. If it passes, exploratory pilot with B0, B3, M0, and MREL on the same six
   tasks: 24 episodes.
4. Inspect paired traces and compute floors before expansion.
5. Only if at least several task pairs are solvable, expand to a 48–64 episode
   focused study.  Add strict controls and full ablations only after a
   non-floor M0-versus-B3 or M0-versus-MREL signal appears.

This sequence should produce a stronger summer-camp submission than spending
another roughly 60 serial hours on a known-incompatible schedule.  It also
turns the failure into a coherent result: reliable memory requires both
protection against over-trust and protection against verification deadlock.
