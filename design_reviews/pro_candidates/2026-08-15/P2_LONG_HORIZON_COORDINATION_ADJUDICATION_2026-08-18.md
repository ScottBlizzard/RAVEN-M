# P2 long-horizon coordination adjudication (2026-08-18)

## Decision

`SYS-SCOPE-R2` is sealed as **`PREFLIGHT_INVALID_NO_LIVE`**. This is not a
`0/7` performance result: no model generation was authorized or performed.
The pipeline must proceed to P3 outcome/completion judgment.

## What was audited

The Pro response
`GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_DESIGN_2026-08-15.md` was read in
full and treated as an unvalidated blueprint. Its only recommended treatment
is a frozen A1-R2 base plus one same-Qwen Phase Coordinator call at the static
midpoint, followed by at most eight short envelope injections. The document
explicitly labels itself `NO-GO-AUDIT` and makes the following pre-generation
requirements hard gates:

1. two independent blinded human reviewers;
2. at least 90% executed-step annotation coverage;
3. Cohen's kappa at least 0.70 plus arbitration;
4. at least three failed tasks with a coordination defect, across at least two
   task families;
5. at least two defects before/near the midpoint with eight decisions of
   remaining runway;
6. no more than one of the six R2 successes positive for the same composite
   defect;
7. a wrong-track exclusion separating coordination defects from terminal,
   outcome-judgment, or single-coordinate failures.

The CPU-only audit verified every formal A1-R2 episode hash and all available
screenshots. It also materialized every task-independent observable that can
be established without semantic labels: exact midpoint, whether the historical
trajectory reached it, and remaining native decision slots.

## Observable projection

- 19/19 formal R2 episodes were hash-bound.
- 12/19 reached the proposed static checkpoint.
- 9/13 failed tasks reached it.
- 3/6 successful tasks reached it:
  `ExpenseDeleteMultiple2`, `SimpleCalendarAddOneEvent`, and `OsmAndMarker`.
- Therefore the mechanism has nontrivial opportunity, but also nontrivial
  success-path exposure. Merely reaching the midpoint cannot establish either
  a coordination defect or a false positive.

## Why the minimal repair did not authorize live

The minimal repair preserved the research direction and materialized raw
hashes, exact checkpoint exposure, remaining slots, and the fixed seven-task
projection. The repository contains no blinded annotation artifact, reviewer
identities, arbitration log, or versioned annotation manual. Consequently the
semantic gates have zero eligible annotations and cannot be evaluated.

Replacing those reviewers with episode length, RGB repetition, or a model-made
summary would not be an interface clarification. It would redefine the claimed
construct from long-horizon coordination to an observable heuristic and would
let the system certify the premise that justifies its own auxiliary call. That
is a new unsupported identity, not a minimal repair. Using a GPT/Pro response
as either reviewer would likewise turn design prose into evidence.

## Scientific boundary

- No claim is made that phase coordination cannot work.
- No claim is made that the candidate scored `0/7`.
- No GPU call was made, because the Pro design's own G0 gate failed.
- The three successful checkpoint exposures are regression risk, not proof of
  harm.
- A future SCOPE study would require independently collected, frozen human
  annotations before any model generation. It may not reuse this `NO_LIVE`
  identity after changing the gate.

Machine-readable evidence:
`evidence/p2_long_horizon/P2_SCOPE_R2_ZERO_GENERATION_AUDIT.json`

Canonical content SHA-256:
`137c8f76760251b3c8214d4746289c18ad8d398f61cec73cf8305a168033424e`
