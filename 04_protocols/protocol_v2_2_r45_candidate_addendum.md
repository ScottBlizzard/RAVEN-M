# Protocol-v2.2 r45 development-candidate addendum

Status: live-qualified development candidate; new Gate-D freeze preparation
authorized

This addendum follows the valid r44 M0 budget failure. It preserves r44's
live-qualified retry-idempotent executor and r43's locally qualified swipe
streak rule. It does not reinterpret any prior task failure as success.

## Task-agnostic horizontal clipped-row navigation

r45 adds the same instruction to both executor system prompts and the shared
Protocol-v2.2 turn prompt:

- when options are visibly side by side in a horizontally clipped row or
  carousel and the exact requested label is absent, swipe along that row
  toward hidden options;
- keep the gesture wholly within the row and above any soft keyboard;
- do not tap a different visible option or the row center to hypothesize that
  a menu will open; and
- tap only after the exact requested label is visible.

The instruction names no app, task, category, target label, coordinate, or
swipe distance. It remains model-authored action selection from the current
screenshot. It does not deterministically force a swipe or bypass any action
guard.

## Development evidence

The r44 M0 cell matched the successful r40 B3 cell through the three required
text values. r40 B3 then swiped immediately, selected the target, and saved
within 12 actions. r44 M0 first tapped the clipped row with the requested
label absent, received no semantic change, then used the same three swipes
and selected the target on its final action without budget for Save.

Across 37 retained Expense trajectories with a post-text navigation action,
all 14 successful episodes began that stage with a swipe. The corresponding
counts were 20 failed taps, two failed swipes, and one failed long-press. For
the 21 Donation instances, 12 successful and two failed episodes began with
a swipe, while six failed episodes began with a tap and one with a
long-press. These are development associations used to identify a recurrent
affordance error, not a causal estimate or formal result.

## Frozen invariants and qualification boundary

r45 changes no model, seed, task instance, evaluator, schema, action or model
call budget, memory policy, guard threshold, executor command, or Protocol-v1
artifact. The instruction is identical across B3 and M0 executor prompts.

The only authorized live action after source freeze and zero-call preflight
is one fresh, non-scored M0 Expense smoke. It is not pooled with earlier
development cells and cannot authorize Gate D or formal execution by itself.

## Live disposition

The fresh M0 smoke was valid but unsuccessful at the 12-action budget. r45
changed the first category-navigation action from the previously observed
speculative row-center tap to a first-pass horizontal swipe. Three exact
swipes changed semantic state; r43 then admitted a fourth exact swipe, which
stalled after making Donation visible. The model selected Donation and filled
the exact Note, but had no remaining action for Save.

This run live-qualifies both r45's task-agnostic guidance and r43's
progress-conditioned fourth-swipe boundary. It does not qualify the task as a
success or support a method-superiority claim. The candidate is retained
without an r46 source change: another task-instance-specific efficiency patch
would create disproportionate development overfitting risk.

Together with the complete local validation, Protocol-v1 seal, and r44 live
executor qualification, this disposition authorizes preparation of a new
Gate-D freeze for the exact r45 source. Formal Gate E remains disabled until
that manifest and a fresh zero-call preflight pass.
