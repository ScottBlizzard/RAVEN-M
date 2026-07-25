# Protocol v1 amendment 002: contiguous model-outage continuation

Status: `active`

Date: 2026-07-25

Scope: `single_cell_contiguous_model_outage_recovery`

## Trigger

Breadth cell 013 (`H09-s20260720`, B2, `OsmAndTrack`) was interrupted three
times by one flapping loss of the locked model endpoint.  The attempts ended
after 38, 41, and 2 steps, respectively.  All three carry
`INFRA_MODEL_UNAVAILABLE`, have identical goal and parameter hashes, and
remain archived.  No evaluator result or scored result was produced.

The endpoint briefly passed a single health poll between attempts, so the
frozen three-attempt cap was consumed during the same contiguous external
network incident.  The runner stopped as designed.

## Authorized correction

This amendment authorizes exactly one attempt 4 for only the manifest-named
cell, after the exact model endpoint passes three consecutive health checks.
The attempt uses the same task seed, generated goal and parameters, model,
backend, prompts, variant, budgets, evaluator and leakage rules.

The three invalid attempts are not deleted, renamed, overwritten or counted as
agent outcomes.  Attempt 4 is written to a new directory and records both
hotfix-001 and hotfix-002 identities.  If attempt 4 suffers another
infrastructure failure, execution stops for manual review.

All later model-recovery barriers require the same consecutive-health gate.
No additional attempt-cap exception is authorized for any other cell.

## Unchanged semantics

- no Hard observation changes a prompt, threshold, method or claim;
- no model output, action, screenshot or evaluator result is edited;
- task order, pairing, statistics and success/failure definitions are fixed;
- the original protocol-v1 and hotfix-001 files remain byte-identical.

Resumption requires a regression test, the full project test suite, an exact
hash manifest, and Git tag `protocol-v1-hotfix-002`.
