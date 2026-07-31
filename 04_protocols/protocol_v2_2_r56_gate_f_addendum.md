# Protocol-v2.2 r56 Gate-F compatibility addendum

Date: 2026-07-31  
Method source: `24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`  
Method tag: `protocol-v2-2-gate-e-r56`

## Authorization boundary

The r56 Gate-E report records a pass for all eight frozen non-Hard cells.
That result authorizes preparation and preflight of Gate F; it does not
automatically authorize a Hard cell.

Gate F remains three separately invoked four-cell batches. Batch 1, Batch 2,
and Batch 3 each require an explicit user request. A completed batch never
launches the next batch, and a completed Gate F never launches Gate G.

## Preserved experiment

The r56 manifest preserves the original Gate-F controls exactly:

- the six preregistered Hard task families and native step budgets;
- seed `20260730`;
- B3/M0 pairing;
- blocked-order seed `2026073001` and candidate 21;
- the twelve-cell order and three four-cell batches;
- prompts, action schemas, model-call budgets, 3.5-hour cumulative cap;
- success, efficiency, provenance, isolation, reset, context, and answer
  acceptance thresholds; and
- result-independent execution with no post-hoc tuning.

Therefore this addendum changes the execution and evidence layer, not the
task sample, order, budget, variants, or acceptance thresholds.

## r56 compatibility mapping

The legacy runner counted every guard validation block as a loop-recovery
obligation. In protocol-v2.2, validation blocks also include expected
input-focus, field-role, exact-target, and consequential-action safety
checks. Requiring a matching recovery completion for every such block would
incorrectly fail safe trajectories.

For r56, loop compliance is instead closed over the per-episode semantic
progress audit:

- every executed step must contain before/after semantic observations and a
  guard audit;
- a fingerprint blocked on an unchanged screen may not later execute;
- no guard repair may remain unresolved after the bounded repair; and
- the existing third-identical-no-effect protection remains active inside
  the guard.

The raw validation, recovery-completion, and recovery-obligation counts remain
reported as diagnostics. They are not reinterpreted as method outcomes.

The r56 runner additionally preserves the Gate-E execution protections:

- auditable AndroidWorld startup with one bounded cold-recovery attempt;
- extended emulator-loss and ANR infrastructure classification;
- protocol-v2.2 controller mode and the visual-source critic;
- readiness-observation accounting;
- consequential-action adjudication accounting;
- visible-failure enforcement; and
- immediate diagnostic stop on a failed semantic-progress audit.

## Frozen prerequisite and zero-call preflight

Before Batch 1, the runner must verify:

1. the formal r56 source tag resolves to the exact frozen method commit;
2. that commit is an ancestor of the executing checkout;
3. every frozen method, prompt, schema, runtime, and runner file matches its
   SHA-256;
4. the exact final Gate-E report matches its SHA-256 and records a Gate-E
   pass for the same source;
5. all six Hard task classes remain registered;
6. instance generation is restart-stable and each B3/M0 pair has identical
   goal and parameter hashes;
7. the expected model backend and revision are healthy;
8. the AndroidWorld emulator is connected; and
9. the scored Gate-F suite directory does not exist.

The preflight records zero model calls, zero GPU experiment cells, and no
automatic Batch-1 launch. It may write only its report, never a scored suite
directory.

## Evidence boundary

Gate F is still a bounded engineering feasibility gate. Even a pass of all
twelve cells is not a statistical claim that M0 outperforms B3. Any failed
native task remains a valid scored failure unless a preregistered
infrastructure classifier applies; results may not be relabelled after
inspection.
