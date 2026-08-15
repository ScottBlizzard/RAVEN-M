# A1-R3-v3 OSCNR primary capability-gate result

Date: 2026-08-15 (Asia/Hong_Kong)

## Verdict

- Experiment status: `STOPPED_CAPABILITY_GATE_FAILURE`
- Episode status: `VALID_SCIENTIFIC_FAILURE`
- Outcome classification: `PRESERVATION_FAILURE_UNATTRIBUTED`
- Mechanism-opportunity classification: `CNR_NO_OPPORTUNITY`
- Continuation: forbidden for this frozen identity
- Same-identity scientific rerun: forbidden
- Neutralized ablation: not released because there was no committed CNR read

The first frozen capability task, `ExpenseDeleteMultiple2`, completed as a
valid episode with reward `0.0`. The arm therefore failed the preregistered
six-success preservation gate and stopped before any other task was run.

This is a system-level preservation failure relative to A1-R2, which had
reward `1.0` on the same task instance and seed. It is not evidence that the
new CNR text caused harm: the CNR receipt was never created, read, committed,
or injected.

## Episode outcome

| Field | Value |
|---|---:|
| Suite | `official_qwen_20260815T150827_f10cb784` |
| Episode | `ExpenseDeleteMultiple2_20260806_d481ed6b` |
| Task seed | `20260806` |
| Generation seed | `3407` |
| Evaluator reward | `0.0` |
| Success | `false` |
| Termination | `max_steps` |
| Model calls | 34 |
| Executed actions | 34 |
| Prompt tokens | 136,034 |
| Completion tokens | 3,956 |
| Total tokens | 139,990 |
| Valid elapsed time | 1,147.997 s |
| Infrastructure-invalid attempts | 0 |
| Lifecycle errors | 0 |
| Transport attempts | exactly 1 for every call |

The checkpoint closed with status `stopped_capability_gate_failure`, one valid
summary, zero invalid attempts, and a capability-gate score of `0/6` after the
first task.

## Mechanism activity and attribution

The inherited compact A1-R2 ledger produced 33 non-empty reads and 8,116
rendered characters. The new OSCNR intervention itself remained silent:

| OSCNR field | Value |
|---|---:|
| First-support observations | 10 |
| CNR receipt creations | 0 |
| CNR committed reads | 0 |
| CNR injected reads | 0 |
| CNR drops or expiries | 0 |
| CNR receipt events | 0 |
| CNR read events | 0 |

The failure trace repeatedly moved among the navigation menu, Expense Logs,
an expense detail page, and back. Those route cycles produced substantial RGB
changes. They therefore did not satisfy the frozen trigger requiring two
consecutive same-family actions with negligible visible change. The trigger's
coverage was too narrow to produce an intervention opportunity in this trace.

No causal-harm claim is permitted. The exact first user-prompt text and prompt
hash matched A1-R2, while the initial UI JSON was byte-identical. The initial
RGB images differed only at 292 of 2,592,000 pixels, with maximum channel
difference 1 and no pixel difference above 5. Nevertheless, the first model
response already differed. Both runs first swiped upward, but by step 2 A1-R2
tapped the Pro Expense icon whereas A1-R3-v3 continued swiping. This divergence
occurred before any possible CNR receipt. The available evidence cannot
separate sensitivity to the tiny image-byte difference from GPU sampling
nondeterminism.

## Frozen comparison

| Arm | Reward | Calls | Actions | Termination |
|---|---:|---:|---:|---|
| A1-R2 CVP | 1.0 | 18 | 17 | `model_terminate_success` |
| A1-R3-v3 OSCNR | 0.0 | 34 | 34 | `max_steps` |

The result falsifies this prospective arm's outcome-preservation commitment.
It does not, by itself, falsify the semantic usefulness of a CNR message,
because no such message reached the model.

## Integrity chain

- Mechanism: `a1r3v3_one_shot_controller_nonprogress_receipt_v1`
- Experiment: `A1R3V3_OSCNR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- Implementation commit: `665fe0d8b67f9a1ed39cd733b2bcf0dce847e7e5`
- Source-freeze content SHA-256: `cf356211a2281a5fb315108e9a789c5ddee1bbb8d7e73fd4ae575b5b1aa70ac4`
- Source-freeze file SHA-256: `66a3b252447251532996efd1119d899a9b60bb54d629702f5f63ec76d6295e94`
- Preflight content SHA-256: `571ab8669f909bf704d4a6875e691f2813f3467fc582d03485961fedbc5e2946`
- Preflight file SHA-256: `bd52e89a549485c855960af28b6e7d00889de8e5a76ee254f9a7ba232f3b2c27`
- Live-receipt content SHA-256: `d269f7cc390533b7419b5901a253a75b6041f14add098eea4706d65e2837876e`
- Live-receipt file SHA-256: `456325c95a52434ee24d5533a0382f6f9ae488e5dc6af54500e26fe441eabe5e`
- Run-signature canonical SHA-256: `3f9e0add4ab9dab5f9b66cb89e629973dcbb056984b2966cf249912f1bcf1310`
- Run-signature file SHA-256: `85780a6a0a8b99942088dcb3546371990639db758d9265004fb818e3ff16337a`
- Manifest snapshot file SHA-256: `c1d718e9d380e443d12d2c29ab2182ae801a3befc53881b864cd830f2ad0440a`
- Episode JSON SHA-256: `28fd49d2582490e312f4ccc6057ff12a10c483872870275f230b17b9639822bb`
- Event stream SHA-256: `358614acc2fbbfaea4a8dc89b5b84e2414b15471d5c350d88b9d9b604bde0eb9`
- Episode summary SHA-256: `a74ad0d9721441cab4cd888879d90e07fa4dba99d66f86c3c4348b28ea6028d6`
- Terminal checkpoint content SHA-256: `41230a518cdc3a722af191e8dd464b621a7623a0b8d13d51fcc6a0f5dd808bba`
- Terminal checkpoint file SHA-256: `908927f696d2e917ec4124c48e262aa96738564a5bc170d76d6c9af08ba0d59a`

The raw suite remains under `runs/a1r3v3_oscnr/` and is intentionally excluded
from Git. This committed closure records the authoritative outcome and binds
the ignored raw artifacts by hash.

## Operational closure

After the terminal scientific verdict, the remote vLLM process and local SSH
tunnel were stopped. No further generation was performed.
