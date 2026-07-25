# Protocol v1 amendment 004: nullable decision aggregation

Status: `active`

Date: 2026-07-26

Scope: `post_episode_aggregation_nullable_decision`

## Trigger

Breadth cell 037 completed its raw trajectory, evaluator call, teardown, and
post-episode reset.  Its terminal failure was
`MODEL_OUTPUT_INVALID_AFTER_REPAIR`, for which the controller correctly
serialized one step with `decision=null`.  Post-episode aggregation then
called `.get("memory_citations")` on that null value and exited before writing
`scored_result.json`.

## Permitted correction

The byte-frozen protocol-v1 runner and amendments 001--003 remain unchanged.
A separately hashed wrapper:

1. treats `decision=null` as an empty mapping only in a deep copy passed to
   post-episode aggregation;
2. retains amendment 001 normalization of nullable history instrumentation;
3. never rewrites raw episodes, events, screenshots, replay, or evaluator
   output;
4. backfills a score only when exactly one completed non-infrastructure raw
   attempt matches the frozen variant and seed;
5. records amendment 004 identity and hashes in affected scored results.

## Unchanged semantics

- model, revision, backend, prompts, schemas, seeds, and task order;
- all GUI observations, decisions, actions, and model calls;
- evaluator rewards, success labels, and failure codes;
- context, step, action, retry, and model-call budgets;
- invalid-infrastructure rules, pairing, metrics, and analysis.

Cell 037 remains the failed B3 episode produced by the frozen controller.  It
must be aggregated from its completed raw record rather than rerun.

## Resumption gate

Resumption requires regression tests, the full project test suite, original
freeze verification, exact amendment hashes, Git tag
`protocol-v1-hotfix-004`, healthy model identity, and a responsive
AndroidWorld emulator.  Only the running breadth phase may resume.
