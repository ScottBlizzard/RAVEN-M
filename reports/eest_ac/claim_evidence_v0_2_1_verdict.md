# EEST-AC v0.2.1 Qualification Claim–Evidence Verdict

Overall verdict: **FAIL — remain at controller floor**.

| ID | Verdict | Evidence | Strict boundary |
|---|---|---|---|
| Q-C1 | **FAIL (live boundary gap)** | Generated artifacts were hash-exact and all 10 action forms passed prompt/schema/adapter offline conformance. Live Q-SWIPE nevertheless failed because the schema's `intent.maxLength=24` constraint was not made explicit enough in the executor/repair interface. | The authoritative source closed action syntax, but did not demonstrably prevent drift or omission across the complete decision envelope. |
| Q-C2 | **PASS, offline only** | All 18 v0.2 raw outputs were replayed: 8 safely normalizable and 10 must-repair. Property/boundary/direction tests prohibited clamp and `recent_app` substitution. | No live normalization efficacy claim; Q-SWIPE emitted direct canonical action shapes. |
| Q-C3 | **PASS for boundedness/transparency; effectiveness not established** | Exactly one repair was made. Both raw outputs, diagnostic code, attempts, and token use are recorded. The repair was not an identical action-object repetition, then terminated transparently on schema invalidity. | This does not mean repair was sufficient: it failed to satisfy the envelope length constraint. |
| Q-C4 | **FAIL** | Initial complete-decision pass 0/1; within-one-repair pass 0/1; adapter and task execution not reached; achieved coverage 0/3; only reset passed. | No qualification for a new held-out efficacy protocol and no memory claim. |
| Q-C5 | **PASS** | Raw JSONL calls = attempts = counters = 2. Zero truncations. The first hard failure stopped cells 2 and 3. | The controller/schema failure is not relabelled as infrastructure retry. |
| Q-C6 | **PASS** | Lock 22/22 matched; legacy hashes were unchanged; no forbidden source imports/guards; P2A/P2B/N2 were not reused; M-RISK and efficacy auto-start remained off. | Q-SWIPE is non-scoring qualification evidence only. |

## Falsifiable-question verdict

Question: can the frozen real model produce, initially or after one syntax repair, a complete canonical decision that validates, maps through the adapter, executes, and resets across all three frozen categories?

Answer: **No under v0.2.1.** The first probe produced canonical-looking swipe payloads twice, but both full decisions were schema-invalid because their `intent` strings exceeded 24 characters. The preregistered hard stop therefore prevented the remaining two probes.

## Allowed next step

Only a separately versioned and frozen controller-contract repair/qualification is allowed. It should treat decision-envelope constraints as first-class contract data and test prompt/schema/repair conformance for them, but this completed batch must not be edited or reused as a blind test. No 48-cell or online M-RISK experiment is authorized.
