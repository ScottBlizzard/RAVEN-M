# Protocol-v2.2 r44 M0 Expense development smoke

Status: **VALID DEVELOPMENT SMOKE; r44 executor qualified; task unsuccessful**

Candidate source:
`e9f903b95320164930456bff598c99bfe7c458be`

## Recorded outcome

The runner recorded native reward 0.0 after 12 actions and 19 model calls.
The episode reached the exact requested Name, Amount, Note, and selected
Donation, but the fixed action budget ended before Save could be executed.
This is a valid task failure at budget, not an infrastructure-invalidated
attempt.

## r44 live qualification

The Name and Amount values were entered exactly. More importantly, the
compound clear-and-type command for `Remember to transfer funds` timed out
after 10 seconds on its first AndroidEnv attempt. The internal retry returned
success, and the retained step-6 screenshot shows the exact Note value once,
with no repeated prefix, duplicated word, or truncation.

This is the failure mode r44 was designed to make idempotent. Every replay of
the compound request began with select-all and delete before typing the
model-authored tokens. The episode then continued normally.

An app-start command also timed out once before the first policy action. That
idempotent launch retry recovered before the initial observed state; the
startup audit was clean and the task instance was correct.

## Action-budget cause

The successful r40 B3 cell and this r44 M0 cell used the same task instance
and both spent actions 0-6 opening the app, activating the form, and entering
the three requested values.

At action 7:

- r40 B3 immediately swiped the horizontally clipped option row, used three
  swipes, selected Donation at action 10, and saved at action 11;
- r44 M0 tapped the middle of the option row while Donation was absent. The
  tap produced no semantic change. Its repaired action and actions 8-10 were
  three left swipes, and action 11 selected Donation, leaving no Save action.

The complete event log therefore contains only three executed swipes. It does
not exercise r43's fourth-swipe exception; r43 remains locally qualified but
not newly adjudicated by this smoke.

Across 37 retained Expense trajectories, the first post-text navigation
action was a swipe in all 14 successful episodes. It was a tap in 20 failed
episodes; two failed episodes began with a swipe and one with a long-press.
For the 21 Donation instances specifically, the counts were 12 successful
swipes, two failed swipes, six failed taps, and one failed long-press. This is
development evidence for a generic horizontally clipped-row instruction, not
a causal performance estimate.

## Next bounded change

r45 may add the same task-agnostic instruction to both executor variants:
when requested text is absent from a visibly side-by-side, clipped row or
carousel, swipe along that row toward hidden options; do not tap a different
visible option or the row center to hypothesize a popup. Tap only after the
requested label itself is visible.

The instruction must contain no app, task, category, or target label and must
pass full local tests, prompt parity checks, historical audit, and the
Protocol-v1 seal before any further live action. It does not authorize Gate D
or formal execution.
