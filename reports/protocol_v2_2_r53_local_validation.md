# Protocol-v2.2 r53 local validation

Status: **local PASS; one isolated live Files smoke required**

Candidate commit/tag:
`f3d7c9d3c33e54245138fc56336027f533b67f17` /
`protocol-v2-2-r53-local-candidate`

## Trigger and change

The r52 smoke was invalidated after three actions. Its step-2 after screenshot
still showed the open Files roots drawer. The step-3 before screenshot showed
the drawer closed and the storage root loading, but both observations carried
the identical old drawer accessibility hash. That stale tree incorrectly
activated the roots-drawer guard and invalidated both the initial action and
its bounded repair.

r53 requires the existing foreground and cross-modal accessibility readiness
checks before every Protocol-v2.2 policy decision. The previous accepted
after-action pixels and semantic hash become the next decision's freshness
reference. A materially changed screenshot paired with the unchanged
semantic hash is retried before the policy can see it. Before-decision
readiness evidence is also retained on model-output failure steps.

## Local evidence

- 393/393 project tests passed on the exact candidate commit.
- 143/143 focused guard, semantic-controller, and full-memory-policy tests
  passed.
- The r52-shaped integration regression rejects the stale drawer tree,
  accepts the subsequent fresh storage-root tree, and executes two intended
  taps with zero roots-drawer blocks.
- The invalid-repair regression proves before-decision readiness evidence is
  retained even when no action executes.
- r52 clear-text, r51 destination-navigation, and r50 source-exit regressions
  remain passing.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Evidence boundary

No live AndroidWorld action has run from r53. The r52 attempt is frozen and
must not be resumed. The only authorized next action is one fresh, isolated,
non-scored M0 `FilesMoveFile` smoke under an r53 namespace after a
zero-model-call preflight. Gate D, formal Gate E, and Gate F remain
unauthorized until that smoke is audited.
