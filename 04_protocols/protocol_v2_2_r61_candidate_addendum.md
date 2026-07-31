# Protocol v2.2 r61 Candidate Addendum

## Status and motivation

r61 is a new local candidate derived from the immutable r60 formal Gate-F
stop. The r60 Batch-1 checkpoint contains two valid scored cells: H01/B3
succeeded, while H17/M0 failed and stopped the preregistered batch at 2/4.
That formal namespace must not be resumed, overwritten, relabelled, or used to
start another batch.

The H17 trace exposed an asynchronous observation error. After two actions,
the immediate post-action accessibility snapshot still represented the old
screen, while the next decision began on the new screen. Each visual delta was
below the frozen one-percent material-pixel threshold, so the old snapshot was
accepted as a no-progress outcome. A critic constraint based on that false
outcome then survived onto a different page and routed the agent into an
unproductive loop.

r61 addresses only that delayed semantic-transition boundary. It does not
change the task, seed, variant, prompt templates, model, evaluator, action or
model-call budget, answer channel, loop threshold, one-repair limit, pairing,
batch isolation, or formal acceptance criteria.

## Bounded post-action settling

For protocol v2.2 only, when the first post-action semantic snapshot still
matches the pre-action snapshot, readiness takes at least three observations
unless a semantic change appears earlier. This bounded settling window also
applies when the pixel delta is below one percent. It does not require semantic
progress, manufacture progress, or spend a policy/model step.

The existing readiness maximum remains the hard ceiling. Infrastructure-failure
text, accessibility freshness, foreground-app checks, and cross-modal stale-tree
rejection remain authoritative.

## Inter-step semantic reconciliation

If the bounded post-action window still records no change but the next
decision observation has a different semantic hash, r61 records a late
transition reconciliation before constructing the next planner context. The
reconciliation:

1. corrects the preceding history outcome from semantic no-change to delayed
   semantic progress;
2. updates the working-memory page signature and invalidates only active
   memories whose validity explicitly requires the same page;
3. expires a critic constraint only when it was created on the just-completed
   step whose no-progress premise is now contradicted;
4. corrects the latest transition fingerprint and removes its provisional
   no-effect count; and
5. emits structured episode and guard audit records.

Cross-page facts without a `same_page` precondition are preserved. Constraints
from older steps are preserved. No hidden task parameters, evaluator values,
expected answer, task ID, application name, control label, or coordinate is
used by the mechanism.

## Loop-guard boundary

A fingerprint already blocked by the loop guard remains blocked after
reconciliation. r61 may correct the evidentiary record that an earlier action
eventually changed the page, but it cannot retroactively execute a blocked
action, reopen a rejected repair, increase the repair budget, or authorize the
same state/action loop. The r60 terminal `press_back` rejection therefore
remains valid.

## Validation and launch boundary

Before any live r61 action:

- replay-shaped tests must cover a sub-threshold transition inside the settle
  window and a transition that completes only after that window;
- policy tests must prove that only the just-created stale critic constraint
  expires;
- memory tests must prove that page-local evidence becomes stale while
  non-page-local facts are not broadly invalidated;
- guard tests must prove that an already-blocked fingerprint stays blocked;
- complete project tests, Python compilation, `git diff --check`, and the
  unchanged 197-file protocol-v1 breadth seal must pass;
- the r60 formal stop and execution hashes must remain reproducible from their
  historical tag; and
- an exact source commit/tag, a fresh wrapper and namespace, and a zero-model-
  call preflight are required.

After those conditions pass, at most one isolated, non-scored H17/M0
development smoke is allowed. Its purpose is to test the generic delayed-
transition mechanism, not to establish formal performance. No new formal
Gate-F cell is authorized by this addendum alone.
