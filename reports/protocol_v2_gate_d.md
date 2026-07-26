# Protocol-v2 Gate D verification report

Date: 2026-07-26  
Protocol: `androidworld_protocol_v2_exploratory`  
Branch: `protocol-v2-exploratory`  
Implementation commit: `31a9e33dd31311caf0f11cafa928caafb9aee0af`  
Decision: **GO for Gate-E preparation only; no GPU run is authorized**

## Outcome

The no-GPU implementation gate passed. Protocol v1 remains sealed, all 19
original Hard task classes have complete declared action coverage under v2,
the full local test suite passes, and AndroidWorld's information-retrieval
answer/evaluator behavior was reproduced without a model.

This is an engineering and protocol-readiness result, not evidence that the
agent solves Hard tasks. The next permitted action is to prepare and review
the eight-cell non-Hard Gate-E configuration. Starting Gate E still requires
an explicit go decision.

## Gate evidence

| Check | Result |
|---|---:|
| Protocol-v1 sealed files rehashed | 197/197 |
| Protocol-v1 hash failures | 0 |
| Selected task capability rows | 19/19 pass |
| Deliberately unsupported capability | audit fails closed |
| Full local tests | 124/124 pass |
| New focused tests over original 86 | 38 |
| Canonical action execution paths | 10/10 |
| Live Android answer cache propagation | pass |
| Native IR evaluator, correct answer | 1.0 in 3/3 cycles |
| Native IR evaluator, wrong answer | 0.0 |
| Empty-cache evaluator before each cycle | 0.0 in 3/3 cycles |
| Three-cycle reset isolation | pass |
| GPU/model calls in Gate D | 0 |

Machine-readable evidence:

- `checksums/protocol_v1_breadth_seal_20260726.json`
- `reports/protocol_v2_task_action_coverage.json`
- `reports/protocol_v2_live_android_answer_smoke.json`
- `05_project/metadata/protocol_v2_gate_d.json`

## Implemented semantic corrections

### Terminal answer

`answer` is present in both v2 schemas and the adapter mapping. The controller
executes it before evaluation, logs the answer hash and length, and verifies
the exact `interaction_cache` value. The adapter writes the benchmark's
authoritative cache directly; it does not depend on AndroidWorld's cosmetic
overlay broadcast, which was observed to block on the local overlay service.

### Text provenance

Every v2 `type_text` and `answer` action carries `text_origin` and
`source_memory_ids`. Literal, current-screen, deterministic-calculation, and
verified-memory paths are tested. Verified-memory sources must also be routed
memory citations; false memory provenance is rejected.

### Loop recovery

The controller fingerprints `(page_sha256, canonical_action)`. A third
identical no-effect action is blocked, and a repeated A-B-A-B transition cycle
blocks both cycle actions. The bounded repair must select one of six generic
recovery classes. Detection, blocks, obligations, and recovery compliance are
logged.

### Completion and authority

M0 and MREL share the same protocol-v2 completion implementation. Direct
current-screen evidence or routed FACT evidence is required, followed by a
same-turn Critic verdict. Critic rejection returns its concrete unmet
constraint and fails closed within the ordinary model-call budget. Every
decision also receives a conservative risk/authority audit record.

## Deviations and resolved infrastructure observation

The first full AndroidWorld gRPC environment connection stalled in the local
accessibility wrapper, and the native answer overlay broadcast separately
timed out. ADB device health recovered after restarting the local ADB daemon.
Because the benchmark evaluator reads `interaction_cache` and the overlay is
cosmetic, the final adapter uses the exact evaluator channel without relying
on the overlay. The live smoke then passed with the actual AndroidWorld
information-retrieval evaluator and a connected emulator.

No v1 artifact was edited to make this pass. No Hard task, model server, 4090,
or A40 experiment was started.

## Freeze rule

The `protocol-v2-dev` tag is valid only for this implementation and these
audits. Any change to controller semantics, schemas, prompts, adapter behavior,
history policy, task capability selection, or budgets requires a new commit
and a complete Gate-D rerun before experimental use.
