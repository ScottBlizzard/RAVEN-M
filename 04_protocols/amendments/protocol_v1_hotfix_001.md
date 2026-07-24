# Protocol v1 amendment 001: nullable aggregation field

Status: `active`

Date: 2026-07-24

Scope: `post_episode_aggregation_only`

## Trigger

The first frozen breadth cell completed all 34 allowed steps and persisted its
raw episode, events, screenshots, replay, evaluator reward, success label, and
failure code.  The runner then failed inside `record_result` because baseline
history policies intentionally serialize `history_update.details` as `null`,
while the aggregation expression assumed an object and called `.get()` on it.

## Permitted correction

The byte-frozen protocol-v1 runner remains unchanged.  A separately hashed and
tagged wrapper:

1. verifies the complete original protocol-v1 freeze;
2. treats `history_update.details=null` as an empty object only in a deep copy
   passed to post-episode aggregation;
3. never rewrites the raw `episode.json`;
4. backfills a `scored_result.json` only when exactly one completed,
   non-infrastructure raw attempt exists and its variant and seed match the
   frozen schedule record;
5. records this amendment identity and hashes in every affected result.

## Frozen semantics that remain unchanged

- model ID, revision, backend, precision, generation and transport policy;
- AndroidWorld commit, task registry, task instances, seeds and order;
- prompts, schemas, agent variants, memory lifecycle and route thresholds;
- context, action, model-call and retry budgets;
- actions, observations, evaluator calls, success labels and failure codes;
- invalidity rules, pairing, metrics and statistical analysis.

The already completed first episode remains the scored B1 failure recorded by
its evaluator output.  It must not be rerun merely because aggregation failed.

## Validation and resumption gate

Resumption requires:

- a regression test showing normalization happens on a copy;
- the full project test suite passing;
- original preregistration hash verification passing;
- exact amendment file hashes recorded in
  `05_project/metadata/protocol_amendment_001.json`;
- Git tag `protocol-v1-hotfix-001`;
- healthy locked model service and AndroidWorld smoke.

Only the breadth phase may resume in this round.  Later frozen phases remain
manual and blocked until breadth completion is reviewed.
