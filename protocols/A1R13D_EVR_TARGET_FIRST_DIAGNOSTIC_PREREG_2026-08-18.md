# A1-R13D EVR target-first diagnostic protocol

Date: 2026-08-18
Status: prospective, pre-generation
Parent evidence commit: `c3deaf9d2082be92e1e3842d3c4192f3080098f8`
Mechanism ID: `a1r13_evidence_value_register_v1`
Experiment ID: `A1R13D_EVR_TARGET_FIRST_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`

## 1. Why this is a new experiment but not a new mechanism

A1-R13 stopped on its first preservation task with reward zero while the new
register was completely silent: zero activations, appends, and rendered reads.
Its first textual prompt was byte-identical to the successful R2 and V4 runs,
but the current screenshot differed and the live trajectory diverged before an
EVR opportunity.  This valid failure remains sealed and is not rerun.

A1-R13D changes only the prospective task order so the mechanism is evaluated
before a silent stochastic preservation failure can censor it.  The EVR source,
renderer, constants, controller, model, seeds, sampling, task instances, and
native step budgets remain unchanged.  A1-R13D is a matched exploratory
diagnostic, not held-out evidence and not a new memory-mechanism claim.

## 2. Frozen order and gates

The exact order is:

1. `BrowserMultiply` target gate;
2. the six R2 successes in their frozen order;
3. the remaining twelve tasks in the original 19-task order.

Browser must have reward 1, exactly one EVR activation, exactly five accepted
values, and at least one exact rendered suffix containing `[1, 8, 10, 7, 2]`.
A valid target failure is terminal and is not rerun.

After target success, every one of the six R2-success tasks must have reward 1
and EVR activation/render counts of zero.  Any valid failure is terminal and is
not rerun.  Only after both gates pass may the remaining twelve run.  An
infrastructure-invalid episode is retained and only the current task may be
replaced according to the shared fail-closed contract.

## 3. Runtime boundary

The runtime mechanism is exactly
`EvidenceValueRegisterMemory` from the frozen A1-R13 implementation.  It adds
zero model calls, uses no OCR/UI tree/evaluator/task identity, performs no
arithmetic, and never blocks, overrides, or terminates an action.  It retains at
most six explicit integer atoms from the model's own valid `observed=` field and
only appends its fixed factual suffix after the exact R2 renderer.

## 4. Claim boundary

Target success is `TARGET_SUCCESS_CANDIDATE_SUPPORT_ABLATION_UNRESOLVED`; it is
not causal proof because no exact-prefix empty-register ablation is run in this
diagnostic.  Target failure after an exact EVR read refutes this rendering as a
sufficient intervention on that run.  A silent target failure is unattributed.
Successes on tasks where EVR is silent are not credited to EVR.

The full 19-task result is reported even if it merely matches R2.  Accuracy
improvement requires more than R2's six full successes with no loss on the six
R2 successes.  All costs and exact read provenance are reported separately.

## 5. Evidence and freeze discipline

The zero-generation preflight must validate the A1-R13 19-episode replay,
its Browser five-value trace, the six-success silence result, this exact config,
focused tests, and every source-closure blob at the implementation commit.
Only a fresh live-server receipt bound to that preflight may authorize model
generation.  Any semantic change after first valid generation requires a new
experiment identity.
