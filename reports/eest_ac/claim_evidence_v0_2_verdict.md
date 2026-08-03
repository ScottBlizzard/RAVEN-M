# EEST-AC v0.2 Claim–Evidence Verdict

| ID | Verdict | Post-batch evidence and boundary |
|---|---|---|
| V2-C1 | **Mechanical pass; live unexercised** | Delayed-transition and missing-a11y replays passed before freezing. The live batch admitted no Recovery records because no action executed. Do not claim live no-effect correctness. |
| V2-C2 | **Mechanical pass; live unexercised** | Exact/same-class repeat tests passed. Live blocks and different-class recoveries were both 0, so task recovery is unmeasured. |
| V2-C3 | **Supported as parser evidence only** | Shared frames matched the frozen exact spans in 6/6 positive arm-episodes and 18/18 roles. Parser output is not memory or task-success evidence. |
| V2-C4 | **Unsupported/unmeasured online** | M-SLOTS H1: correct 0, missing 2. Execution failed before evidence capture, so no comparison to summary is permitted. |
| V2-C5 | **Unsupported/unmeasured online** | M-SLOTS H2: correct 0, missing 2. Correct initialized destination spans do not establish retention at a value-carrying decision. |
| V2-C6 | **Unsupported; continuation criterion failed** | M-SLOTS had 0/2 positive successes, H3 correct 0/2, and H3 win/loss/tie 0/0/2 against B3-MATCH. |
| V2-C7 | **Configuration frozen; live opportunity absent** | Every cell reported eligible/planned/realized = 0/0/0. Two actual raw calls were executor + repair, not matched auxiliary memory calls. Actual-call equality is incidental. |
| V2-C8 | **Not demonstrated** | All three negative-control arms failed before the first action. The repaired completion policy never saw a stable satisfied screen. |
| V2-C9 | **Supported in this batch** | Schema truncations 0; model calls, raw records, and attempts all equal 18; evaluator results exist in 9/9 cells, including all controller-invalid endings. |
| V2-C10 | **Out of scope** | M-RISK remained offline-only. No online Risk Gate efficacy claim is allowed. |

Overall verdict: the v0.2 blind smoke is an auditable controller-floor diagnosis, not a memory-method comparison. It must not be expanded to 48 cells.
