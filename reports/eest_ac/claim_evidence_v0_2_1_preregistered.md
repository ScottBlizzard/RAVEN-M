# EEST-AC v0.2.1 Preregistered Claim–Evidence Table

| ID | Claim | Minimum evidence | PASS criterion | Forbidden inference |
|---|---|---|---|---|
| Q-C1 | One authoritative contract prevents prompt/schema/adapter drift. | Generated-artifact check plus per-action conformance matrix. | Every canonical type has exactly matching fields, prompt example, schema acceptance, adapter mapping, and execution coverage. | Treating three manually similar definitions as one contract. |
| Q-C2 | Safe deterministic aliases can be normalized without semantic guessing. | Property/boundary tests and all 18 v0.2 replays. | Only frozen complete aliases normalize; direction and bounds are correct; no clamp or recent-app substitution occurs. | Calling ambiguous or out-of-range rewriting “repair.” |
| Q-C3 | Syntax repair is bounded and transparent. | Invalid/missing/extra-field tests plus live repair traces. | At most one repair; diagnostic includes rejected action and legal forms; identical invalid repetition has a deterministic failure code. | Silently retrying or hiding repeated invalid output. |
| Q-C4 | The real model can satisfy the canonical action contract. | At most three frozen qualification probes. | 3/3 canonical within one repair, 3/3 schema/adapter/execute/reset, full three-category coverage, zero truncation, complete accounting. | Any memory-efficacy or task-success claim. |
| Q-C5 | Failure-path accounting is complete. | Raw JSONL, attempts, per-probe summary, early-stop record. | Raw calls equal counters and attempts; a hard failure stops later probes. | Relabelling model/controller invalidity as infrastructure retry. |
| Q-C6 | Qualification isolation is preserved. | Source scan, protocol lock, legacy start/end hashes, run stop reason. | No task/App/coordinate special branch; no P2A/P2B/N2 held-out reuse; no M-RISK; no automatic efficacy run. | Treating a qualification probe as a held-out experiment. |

PASS means only “eligible to design a new held-out efficacy protocol.” FAIL means “remain at the controller floor.”
