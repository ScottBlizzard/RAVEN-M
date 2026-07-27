# AndroidWorld protocol v2.1 exploratory specification

Status: implementation candidate; Gate D requalification required
Protocol ID: `androidworld_protocol_v2_1_exploratory`
Parent evidence: protocol-v2 Gate-F batch-1 diagnostic checkpoint

## Scope

Protocol v2.1 repairs generic reliability blind spots found in the first
four-cell Hard checkpoint. It does not reinterpret, delete, or pool the
protocol-v2 episodes. All future v2.1 experiments require new suite IDs,
manifests, instance snapshots, commits, and tags.

The frozen v2 Gate-F runner is diagnostically paused. Its batch 2 and Gate G
transitions remain forbidden.

## Semantic progress

The controller constructs a deterministic digest from visible Android
accessibility elements. It excludes:

- elements explicitly marked invisible;
- Android system-UI elements such as the status-bar clock;
- newly visible validation-error overlays from the progress digest.

Validation-error text is retained separately as visible evidence. The digest
uses no evaluator state, application database, hidden package state, task
answer, or cross-episode information. It is shared by B3 and M0 and is used
only for enforcement and audit; it is not an action-selection oracle.

If accessibility elements are unavailable, the controller fails back to the
screenshot hash and records that source.

## Enforced recovery

A page/action fingerprint is blocked when:

1. the same action produces no semantic UI change twice;
2. the action produces a newly visible validation failure; or
3. semantic transitions form a repeated A-B-A-B cycle.

A blocked decision receives one bounded repair opportunity. The repair must
choose a materially different recovery class. A recovery is complete only
after a non-blocked action changes the semantic UI without producing another
visible failure.

Legitimate repeated actions remain allowed when task-relevant visible content
changes, such as a counter or newly revealed list item.

## Failure memory

For RAVEN-M variants, a newly visible validation failure creates an observed,
episode-scoped `failure` memory item with:

- the action that produced it;
- the visible failure message;
- after-action screenshot provenance;
- semantic page scope;
- expiry on semantic page change or successful recovery.

It is routed as `ALERT`, not `FACT`. The event-triggered Critic receives a
`visible_validation_failure` trigger. Baselines receive the same deterministic
block and previous-outcome signal but no RAVEN memory.

## Startup infrastructure

Every v2.1 runner must use the startup environment audit helper:

1. attempt normal AndroidWorld construction once;
2. persist a typed infrastructure failure if it fails;
3. cold-restart, smoke-test, and reconstruct once;
4. persist recovery success or a second failure;
5. stop after the second failure.

Startup failures occur before any scored cell and cannot be silently omitted
from the suite audit.

## Gates

Gate D requires:

- 197/197 protocol-v1 sealed hashes;
- 19/19 selected-task action coverage;
- all local tests, including semantic-progress and startup recovery fixtures;
- live Android answer/reset isolation;
- live visible-only accessibility digest with zero model calls;
- no experimental Gate-E or Hard cell.

After Gate D passes, Gate E must restart all eight non-Hard cells under a new
v2.1 suite ID. Gate F may restart from batch 1 only after Gate E passes.
Protocol-v2 and v2.1 cells must never be combined in one gate decision.
