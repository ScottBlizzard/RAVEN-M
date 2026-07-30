# Protocol-v2.2 r53 development-candidate addendum

Status: live Files smoke passed; eligible for Gate-D preparation

This addendum follows the invalid r52 development smoke. It preserves r52's
post-activation clear-text guard, r51's exact destination-label binding,
r50's live-qualified source-exit behavior, the one-commit boundary, and all
prior protocol artifacts.

## Before-decision cross-modal freshness

The r52 attempt exposed an observation-order race after closing the Android
Files roots drawer. The screenshot had already changed from the open drawer
to the storage root, while the accessibility snapshot still described the
old drawer. Because the controller previously requested cross-modal
freshness only after an executed action, the next policy decision consumed
that mismatched pair and an otherwise valid tap was rejected by a stale
drawer guard.

r53 applies the existing Protocol-v2.2 readiness contract to every
before-decision observation. After an executed action, the controller retains
only:

- a copy of the accepted after-action pixels; and
- the SHA-256 of the accepted after-action semantic snapshot.

The next before-decision observation requires foreground-matching
accessibility. If the pixels changed materially while the semantic hash is
unchanged, the pair is not delivered to the policy and readiness observation
continues under the already frozen retry and one-refresh limits. A fresh
semantic snapshot or a non-material visual transition remains admissible
under the pre-existing contract.

Every step now persists `before_readiness_observations`, including a step
whose initial and repair outputs both fail validation. This makes a stale
tree diagnosis auditable even when no action is executed.

## Preserved boundary

r53 does not change an action schema, action or model-call budget, readiness
threshold, retry count, repair contract, prompt, memory policy, destination
commit rule, source-exit rule, or task success definition. It introduces no
new action and grants no additional coordinate authority. Protocol-v1 does
not request the Protocol-v2.2 before-decision accessibility contract.

## Required evidence

The deterministic integration regression reproduces the r52 order:

1. the roots drawer is accepted as the after-action state;
2. the next screenshot changes to the storage root while accessibility still
   describes the drawer;
3. that mismatched pair is rejected before any model call;
4. a fresh storage-root semantic tree is accepted; and
5. the next policy action executes without a stale drawer block.

The exact candidate passed 393/393 project tests, 143/143 focused guard,
controller, and full-memory-policy tests, compilation, diff validation, and
the unchanged 197/197 Protocol-v1 breadth seal.

## Live disposition

The single authorized r53 M0 `FilesMoveFile` smoke returned native reward 1.0
and `success=true`. The valid attempt persisted fresh, foreground-matching
accessibility before all 20 decisions. The new before-decision rejection
fired twice in a separately quarantined attempt before that attempt later
encountered an unrelated ADB text-input timeout. The fresh retry then passed
end to end.

The preserved r50 source-exit, r51 exact `Ringtones` content-label
navigation, and r52 post-activation clear-text branches all fired live in the
valid attempt. Exactly one MOVE commit executed and no second mutation
followed it. This evidence permits preparation of a new Gate-D freeze for the
exact r53 source; it does not itself authorize or launch formal Gate E or
Gate F.
