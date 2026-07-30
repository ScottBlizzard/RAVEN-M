# Protocol-v2.2 r52 M0 Files smoke

Status: **invalid cross-modal stale-accessibility attempt; r52 branch not reached; Gate D withheld**

Candidate:
`protocol-v2-2-r52-local-candidate` /
`92d7be90e9627346d717ad68163f52de4948a8a2`

Suite:
`nonhard_capability_v2_2_seed20260729_r52_candidate_development_smoke_sequence_4`

## Result

The fresh, isolated, non-scored M0 `FilesMoveFile` attempt stopped after
three executed actions because the fourth decision and its sole repair were
rejected by the existing Files-roots-drawer contract. The recorded summary
contains `MODEL_OUTPUT_INVALID_AFTER_REPAIR`, but post-hoc cross-modal review
shows that the decision was validated against stale accessibility and must
not be treated as a valid semantic task failure.

r52's post-activation clear-text branch was not reached. The attempt provides
no evidence for or against that branch.

## Cross-modal invalidation

After step 2 tapped the `sdk_gphone64_x86_64` drawer row:

- `step_002_after.png` still showed the open roots drawer;
- `step_003_before.png` showed the drawer closed and the storage-root page
  loading;
- the two images had different SHA-256 values and 35.875270% of pixels
  changed;
- both observations nevertheless carried the exact same accessibility
  semantic hash
  `a29a59ded2e927e33ef335f954f58bb19edc882310deb71d2cb49f02d17c797e`
  and the same nine-element tree.

The step-3 screenshot visibly contained the storage-root title, breadcrumb,
category chips, and an empty loading content area. The stale semantic tree
still contained drawer rows, so `files_roots_drawer_action_assessment`
reported `drawer_active=true`, six standard root labels, and one visible
storage row. It rejected the model's visible Audio-category tap and then
rejected the repeated repair as not hitting a stale drawer row.

The controller already performs cross-modal freshness checks after actions,
but its before-decision observation used `require_accessibility=false` and
did not compare against the prior after-action pixels/semantic hash. It
therefore paired a new screenshot with the previous same-package
accessibility tree. This is a readiness-accounting defect, not an r52 policy
failure or network outage.

## Bounded r53 scope

A justified r53 may change only Protocol-v2.2 before-decision readiness:

- retain the previous executed step's after-action pixels and semantic hash;
- require accessibility for the next before-decision observation;
- pass the retained state into the existing cross-modal freshness check;
- retry when pixels materially changed but the semantic hash is unchanged;
- preserve the existing bounded accessibility refresh behavior; and
- persist before-decision readiness observations even when model output
  ultimately fails validation.

The rule must not change Protocol-v1 behavior, action semantics, budgets,
guard thresholds, or any r52/r51/r50 policy branch. A deterministic
integration test must reproduce drawer pixels/tree after an action, then a
closed-root screenshot with the stale drawer tree, then the fresh root tree;
the policy may see only the fresh tree.

r53 requires complete local and Protocol-v1-seal validation, a new source
tag, a zero-call preflight, and at most one fresh isolated M0 Files smoke.
r52 is immutable and may not be resumed. Formal Gate E and Gate F remain
unauthorized.

