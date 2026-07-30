# Protocol-v2.2 r42 M0 Expense development smoke

Status: **REJECTED; Gate D not authorized**

Candidate source:
`cb6cda50a6423c1e5292e9beb75958880f9e819e`

## Outcome

The fresh, non-scored M0 cell returned native reward 0.0 after 12 actions and
18 model calls. It correctly entered the name, amount, and note, but exhausted
the action budget while scrolling the category row. Donation was not selected
and Save was not executed.

This was a valid agent/controller failure. There were no infrastructure
attempts, invalid final model outputs, executed blocked actions, memory-audit
errors, or semantic-audit errors.

## What r42 proved

The one-step input-activation proof fired exactly once and was consumed
exactly once. Step 2 executed only the supported Name-field activation tap.
At step 3, the coordinate-bearing text proposal was rejected and repaired to
the same task-bound `Educational` value without coordinates. Text entry then
changed semantic state. The proof did not affect the later Amount action.

The category behavior also stayed on the correct horizontal axis. Steps 6-8
executed three identical left swipes, and every transition changed semantic
state. This removes both r41 defects: there was no duplicate activation tap
and no vertical category motion.

## Newly isolated boundary

The pre-existing coordinate-streak guard rejects a fourth identical action
after three executions even when all three have verified semantic changes.
At step 9 it therefore blocked the fourth left swipe and the bounded repair
reversed direction.

The step-8 screenshot already showed `Transportation`, `Clothes`,
`Health Care`, and part of `Education`. The retained r40 B3 success shows that
one further left swipe can expose `Donation`, after which the remaining two
actions can select it and Save. r42 instead moved right at step 9, left at
step 10, and right at step 11.

This is not evidence for deleting loop protection. In the r40 B3 success, the
third identical swipe had no semantic change; blocking its fourth proposal
correctly prompted a direct Donation tap. The necessary distinction is
whether the current identical-action streak contains verified no-progress
evidence.

## r43 scope

r43 should retain the three-action check but condition its rejection:

1. allow another exact coordinate action when every transition in the current
   streak changed semantic state;
2. retain rejection when any transition in the streak had no semantic change;
3. evaluate the immediate unverified-progress/no-effect rule before the
   generic streak rule, so a newly stalled productive streak must re-read the
   current layout and tap a now-visible target rather than arbitrarily reverse;
4. preserve the existing no-effect threshold, A-B-A-B detector, one-repair
   limit, budgets, schemas, and model.

Across 403 historical trajectory files, only three model proposals triggered
the coordinate-streak guard. Two followed three semantic-changing
transitions, including r42, and both episodes failed. The retained r40 B3 case
contained a no-effect transition and remains blocked under r43.

## Evidence boundary

The raw directory and hashes are retained. This smoke is not pooled with r40,
r41, or the immutable r39 Gate-E result. Gate D and formal execution remain
unauthorized.
