# Protocol v1 amendment 005: stable pairing hash metadata

Status: `active`

Date: 2026-07-26

Scope: `posthoc_pairing_hash_metadata`

## Trigger

The completed 95-cell breadth phase passed all episode-level audits but its
suite summary reported one pairing invariant error for
`H15-s20260720` (`SaveCopyOfReceiptTaskEval`).  All five variants had the same
goal, file name, seed, image mode, image size, and other serialized task
parameters.  Their sole difference was the hexadecimal process-local address
inside the repr of a PIL `ImagingCore` object.

The address is allocation metadata, not task-instance content.  Hashing it
made five semantically identical parameters appear different.

## Permitted correction

A separately hashed post-hoc repair:

1. recognizes only full runtime-object repr strings of the form
   `<... object at 0x...>`;
2. removes only the hexadecimal address before hashing task parameters;
3. applies the corrected derived hash only to the five completed H15 scored
   result records;
4. preserves each prior hash in `params_sha256_before_hotfix_005`;
5. records amendment identity and hashes in every affected scored result;
6. rebuilds `suite_summary.json` and `suite_progress.json` from the 95 scored
   results and requires zero pairing and episode-audit errors.

## Unchanged semantics

- raw episodes, events, screenshots, replay records, and evaluator outputs;
- model calls, prompts, decisions, GUI actions, and observations;
- seeds, task order, task goals, task content, and variant assignment;
- rewards, success labels, failure codes, budgets, and retry decisions;
- every scientific metric other than correction of the false-positive
  pairing-audit flag.

No episode may be rerun under this amendment.
