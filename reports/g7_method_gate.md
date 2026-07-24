# G7 full-method development gate

Status: **passed**

G7 is a non-Hard engineering and evidence gate. It does not contain or imply
an AndroidWorld Hard benchmark result.

## Method execution

The fixed v15 schedule completed all 13 cells under the locked
`Qwen/Qwen3-VL-32B-Instruct` revision and four-RTX-4090 BF16 backend.

| Variant | Episodes | Official successes | Decisions | Planner events | Critic events | Max prompt tokens | Infra errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | 5 | 2 | 53 | — | — | 4806 | 0 |
| M0 | 8 | 4 | 80 | 22 | 15 | 5184 | 0 |

M0 had zero role-output errors, zero memory-invariant errors, zero stale FACT
routes, and valid executor output after at most one repair for all 80
decisions. An aggregate-only replay of the persisted suite also passed.

## Manual retrieval audit

The deterministic v15 audit population contained 300 eligible decision-time
routes. Seed `20260724` selected 50 items with source-provenance and current
decision screenshots. One reviewer inspected all 50 pairs using the fixed
rubric:

- 40/50 items met every utility component (80.0%);
- 5/50 were potentially harmful;
- all component labels and FACT-support labels were complete;
- the final audit independently regenerated the same sample keys and
  recomputed utility from the component labels.

The threshold is met exactly. Negative examples remain recorded, including
incorrect timer state, incorrect note-insertion completion, stale page state,
and confirmation of a move to the wrong destination.

## Eight-path component smoke

`component_smoke_v2_20260724` executed all eight fixed paths on one paired
Contacts instance with the exact locked model and parameter hash. It passed
the component audit with:

- eight persisted path results;
- one paired goal/parameter hash;
- zero infrastructure attempts;
- zero structural audit errors;
- zero role-output errors and zero stale FACT routes.

This suite is an execution and instrumentation smoke, not a task-quality
estimate. Individual paths may legitimately end at their fixed action budget
or with a model-declared infeasible outcome; G7 uses the separate fixed M0
schedule and manual retrieval audit for method acceptance.

## Verification and boundary

The full project test suite passed 75/75 tests. The machine-readable final
audit passed every check and is stored at
`05_project/metadata/g7_audit.json`.

G7 permits protocol-freeze preparation to begin. It does **not** permit scored
Hard runs: the preregistration artifact still needs final review, immutable
hashing, and a protocol-v1 tag.
