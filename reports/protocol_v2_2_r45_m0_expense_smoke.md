# Protocol-v2.2 r45 M0 Expense development smoke

Status: **VALID DEVELOPMENT SMOKE; r45 guidance and r43 boundary qualified;
task unsuccessful**

Candidate source:
`3d0d719bfccac5934c62d3ab8be902a0ef66d7e9`

## Recorded outcome

The runner recorded native reward 0.0 after 12 actions and 19 model calls.
The final screenshot visibly contains the exact requested Name, Amount, Note,
and selected Donation category, but Save was never executed. This is a valid
task failure at the frozen action budget, not an infrastructure-invalidated
attempt.

An app-start request timed out once inside AndroidWorld before the first
policy observation. Its idempotent retry recovered, the startup audit was
clean, and no scored task action was duplicated.

## r45 live qualification

The new clipped-row instruction changed the relevant behavior without forcing
an action. After Name and Amount were entered, the first category-navigation
proposal was a model-authored horizontal swipe. It passed on the first model
response with no controller repair. The model did not tap another visible
category or the middle of the row while Donation was absent.

Actions 6, 7, and 8 were the same left swipe and each changed the semantic UI.
Action 9 proposed the same swipe a fourth time. The r43 progress-conditioned
rule admitted it on the first response because every prior transition in the
exact streak had changed semantic state. That fourth transition produced no
semantic change, while its screenshot exposed Donation. The guard therefore
recorded a four-action streak with one no-effect transition; another exact
swipe would be rejected under the retained no-progress rule.

This is the first valid live adjudication of r43. It demonstrates the intended
boundary: permit a fourth exact swipe after three observed semantic
transitions, then retain protection once the repeated gesture stalls. It does
not establish that semantic change alone proves task progress or success.

## Budget failure

The exact executed sequence was:

1. open Pro Expense and enter the add-expense form;
2. activate Name using two bounded input-guard repairs;
3. type `Educational` and `259.57`;
4. execute four left swipes in the clipped category row;
5. tap the now-visible Donation button;
6. type `Remember to transfer funds`.

The model navigated the category row before filling Note. Donation became
visible only after the fourth shorter swipe, was selected at action 10, and
the Note was filled at action 11. No action remained for Save. The final
screenshot is visually complete but uncommitted, so the native evaluator
correctly returned zero.

r45 therefore fixes the recurrent speculative row-center tap but does not
guarantee optimal field ordering or completion within every 12-step episode.
Those remaining behaviors are ordinary model planning/efficiency variance,
not evidence for another task-specific controller or prompt patch.

## Scientific disposition

r45 is retained without an r46 source change. Repeatedly modifying the method
against this one development instance would create a larger overfitting risk
than the remaining failure justifies. The prior r39 eight-cell Gate E already
passed its frozen engineering criteria with 7/8 native successes; Gate E does
not require every Expense cell to succeed.

The combined local suite, Protocol-v1 seal, r44 live executor qualification,
r45 live behavior, and r43 live boundary authorize preparation of a new
Gate-D freeze for the exact r45 source. They do not by themselves constitute
a new formal Gate-E result. Formal execution remains disabled until the new
manifest, source hashes, task instances, model identity, emulator state, and
zero-call preflight are frozen and pass.

