# Protocol-v2.2 r60 Gate-F addendum

Date: 2026-07-31  
Method source: `5ef66de358423f9940191d8dfde0e74002ccdcec`  
Method tag: `protocol-v2-2-r60-local-candidate`

## Decision boundary

The isolated, non-scored r60 H01 B3 smoke passed the native evaluator and its
semantic audit. This authorizes construction and zero-call preflight of a new
formal Gate-F namespace. It does not retroactively alter r56-r59, convert the
smoke into a scored cell, or authorize an automatic formal batch.

Gate F remains three separately invoked four-cell batches. Every batch requires
an explicit launch, writes a checkpoint, and stops. A batch never launches its
successor, and Gate F never launches Gate G.

## Preserved experiment

The r60 formal manifest inherits the r56 experiment controls without change:

- six preregistered Hard task families and native step budgets;
- seed `20260730`, B3/M0 pairing, blocked-order seed `2026073001`, and
  blocked-order candidate 21;
- twelve-cell order and three four-cell batches;
- prompts, schemas, call limits, context cap, and 3.5-hour cumulative cap;
- success, efficiency, provenance, isolation, reset, and safety thresholds;
- immediate stop on a valid protocol failure; and
- no result-dependent tuning or automatic transition.

Only the r60 controller correction and its evidence prerequisites differ from
the stopped r56 execution.

## Frozen r60 prerequisite

Before a formal preflight or batch, the runner must verify both prerequisites:

1. the immutable r56 Gate-E pass still matches its exact hash and source; and
2. the r60 H01 B3 development smoke report and every cited raw artifact match
   their exact hashes.

The second check additionally requires the report to record a non-scored
development run, one successful H01 B3 result with native reward 1.0, no setup
button pollution, exactly five executed target clicks, operands
`6, 2, 3, 9, 10`, result `3240`, joint count-and-operand completion, and no
sixth proposed or executed click. A hash match alone is insufficient.

## Formal isolation and preflight

The formal suite is `hard_micro_v2_2_seed20260730_r60` under
`runs/protocol_v2_2`. Its wrapper disables development-smoke mode so a formal
command cannot silently create another diagnostic cell.

Before Batch 1, zero-call preflight must verify the exact source tag and commit,
all frozen files, both prerequisites, six registered task classes,
restart-stable instances, paired goal/parameter hashes, model identity,
emulator connectivity, the protocol-v1 seal, and absence of the formal suite
directory. Preflight may write its report and generated manifest only. It may
not create the scored suite or make a model call.

## Evidence boundary

Even twelve valid cells constitute an engineering feasibility result, not a
statistical superiority claim. A native task failure remains a scored failure
unless the preregistered infrastructure classifier applies. A stopped formal
namespace is immutable and cannot be resumed, overwritten, or relabelled.
