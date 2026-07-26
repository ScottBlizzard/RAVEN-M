# Protocol-v2 Gate D rerun 1

Date: 2026-07-26  
Implementation commit: `56c96424a6aaa422867682ce29f854a6f5d60a23`  
Trigger: Gate-E attempt 1 canonical action-shape failure  
Decision: **PASS**

The v2 Executor prompts now enumerate every exact canonical GUI action object.
The bounded repair prompt explicitly shows `open_app` and `swipe`, and forbids
the observed legacy forms: string actions, `action_details`, `action_args`,
`direction`, and `distance`.

The Gate-E aggregator is null-safe and now stops immediately after an atomic
cell fails the one-bounded-repair validity requirement.

Verification:

- protocol-v1 seal: 197/197 hashes, zero failures;
- task/action coverage: 19/19;
- full local tests: 128/128;
- correct native answer score: 1.0 in three isolation cycles;
- wrong native answer score: 0.0;
- no model/GPU cell was run as part of this Gate-D rerun.

The failed Gate-E attempt remains diagnostic and is not reused. Gate E must be
rerun from all eight cells under a new suite ID and freeze tag.
