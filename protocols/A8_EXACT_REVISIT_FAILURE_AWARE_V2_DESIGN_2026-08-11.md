# A8-v2 exact-revisit failure-aware memory

## Status and version boundary

This is a prospective successor produced after inspecting A3-A7 traces and is
now integrated as runner arm `a8v2`. It is not the preregistered A8-v1 and must
never overwrite, resume, or relabel an A8-v1 suite. It has passed repository
zero-generation qualification but has never made a scored generation call.

## Why A8-v1 is not sufficient

A8-v1 keeps the latest 12 raw transition entries and retrieves the latest two
entries with the same exact visible-screen fingerprint.  In a repeated-action
loop, duplicate entries displace action diversity and retrieval says only that
the same action previously produced a visible outcome.  It does not aggregate
how many times an action failed to move the screen and does not state that a
navigation route returned to the same page.

The observed A3-A7 traces make these weaknesses material:

- A3/A4/A5 each spent 34 steps on their first failed preservation task and
  revisited an exact visible screen 17, 17, and 21 times respectively.
- A6 had 274 exact-screen revisit steps across 628 recorded steps.  There were
  182 repeated exact-screen/action pairs; 117 of those repeated actions again
  produced no or negligible visible change.
- In the inspected A7 traces, individual failures included 51, 34, 25, and 56
  repeated exact-screen/action no-progress steps in a single episode.

These counts were computed from the stored model-visible PNGs with the same
middle-92-percent exact RGB fingerprint used by A8-v1.  Evaluator, UI tree,
activity, and foreground package were not used.

## Proposed intervention

The controller maintains bounded per-exact-screen evidence:

1. Exact model-visible screen fingerprint; no perceptual or UI-tree near match.
2. Action families derived only from the executed canonical action. Coordinates
   are rounded to 0.01 to merge tiny policy jitter; text is represented by an
   exact digest.
3. Counts of attempts and visible-pixel outcomes for each action family.
4. A bounded exact-fingerprint transition chain. When a chain begins at the
   current exact screen and later returns to it, retrieval reports the route
   length and its first action.

On an exact revisit, retrieval renders the highest no-progress action families
once with counts, plus any most recent closed-route fact. It explicitly says
that current pixels are authoritative, visible change is not completion
evidence, and no action is blocked or replaced.

## Causal and safety boundary

- Controller-authored only; no additional model call.
- Inputs: task-independent model-visible RGB pixels, the policy's own executed
  canonical action/prose, and visible-pixel transition.
- No evaluator, UI tree, activity/package, hidden task state, donor trace, or
  guard output.
- No action veto, repair, replacement, forced navigation, or early stopping.
- Exact-screen retrieval only. The 0.01 coordinate grouping applies only after
  an exact screen match and cannot cause a screen match.
- It never claims task success or item completion.

## What must be frozen before execution

The implementation is connected to the shared runner and A6-A9 contract under
the new experiment/mechanism IDs. The module, config, tests and this protocol
are source-frozen by the zero-generation preflight. A fresh live receipt is
still mandatory before generation. The four A0 preservation tasks run first;
all four must pass before the remaining 15 tasks are released. A8-v1 artifacts
remain unchanged for auditability.

Suggested compatible instantiation:

```python
FailureAwareExactRevisitMemory(
    max_states=12,
    max_actions_per_state=4,
    max_transitions=24,
    max_rendered_actions=3,
    max_chars=360,
)
```

## Interpretation

This intervention tests whether binding memory specifically to exact recurrent
decision states and aggregating failed action evidence reduces loops. Memory
activation or fewer repeated actions alone is not proof of improved task
ability; the primary comparison remains success on the same 19 task/seed
pairs, with steps, tokens, wall time, and per-task loop counts as secondary
outcomes.
