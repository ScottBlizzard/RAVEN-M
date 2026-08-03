# EEST-AC v0.2 Preregistered Claim–Evidence Table

| ID | Claim | Minimum evidence | Pass criterion | Forbidden inference |
|---|---|---|---|---|
| V2-C1 | The repaired controller confirms no-effect only after stable pixel and a11y observations. | Delayed-transition replay plus every live Recovery admission trace. | All admitted Recovery entries satisfy the frozen dual-modal window; ambiguous/missing a11y produces none. | Treating one immediate hash equality as real no-effect. |
| V2-C2 | Recovery prevents action repetition in the same stable state. | Exact-repeat and same-class replay plus live recovery counts. | Exact and same-class proposals are blocked; the next executed proposal has a different action class. | Claiming task recovery merely because a record exists. |
| V2-C3 | The shared role parser separates source, field, and destination. | Exact-span parser tests and frozen parse records shared across arms. | Supported task literals yield the same exact spans for all arms; ambiguity fails closed. | Counting parser output as method evidence or using task-template branches. |
| V2-C4 | M-SLOTS captures source→field→value. | H1 labels for both held-out positives and raw evidence provenance. | Report TP/FP/FN and episode accuracy; any positive conclusion is limited to capture. | Calling multiple records independent task successes or claiming superiority from H1 alone. |
| V2-C5 | M-SLOTS retains the destination role. | H2 labels at the value-carrying decision. | Report correct/source-as-destination/other/missing confusion and accuracy. | Equating correct value retention with correct destination retention. |
| V2-C6 | M-SLOTS improves end-to-end value→destination action correctness. | H3 labels, evaluator results, and paired outcomes. | At least one H3 paired win and one real positive success, with success not below B3-MATCH. | A task-level claim from record accuracy or a failed episode. |
| V2-C7 | B3-MATCH is a valid policy/ceiling control. | Eligible, planned, realized, missed-call records and first divergence. | Shared trigger policy and ceilings, useful calls only, no padding; realized differences disclosed. | Claiming actual call equality from policy matching. |
| V2-C8 | Generic completion removes the negative-control floor. | Early-completion replay and held-out negative cell. | Stable satisfied requirement terminates without a later model call or obvious extra action in every arm. | App-name/task-class hardcoding or evaluator-as-controller leakage. |
| V2-C9 | Accounting and evaluator coverage are complete. | Per-call JSONL, failure replay, every cell summary. | Calls equal raw records and every cell has an evaluator result, including controller/model-invalid cells. | Relabelling invalid model/controller output as infrastructure retry. |
| V2-C10 | Risk Gate improves online execution. | None in v0.2. | Out of scope. | Any online Risk Gate efficacy claim; M-RISK has zero live cells. |

Evidence levels remain `mechanical`, `development replay`, `held-out episode`, `paired nine-cell smoke`, and `expansion-grade`. v0.2 cannot reach expansion-grade because it contains only two positive pairs.
