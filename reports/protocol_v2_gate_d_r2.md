# Protocol-v2 Gate D rerun 2

Date: 2026-07-26  
Implementation commit: `f3575ddf735d99360ebc0339d02b7eb3f062b291`  
Trigger: Gate-E rerun 2 M0 `state_delta` shape failure  
Decision: **PASS**

The v2 M0 Executor prompt now gives the exact structured `state_delta` object
form, matching the schema and the already established v1 contract. The
protocol-v2 bounded repair prompt gives the same generic fact form while
retaining the rule that B3 must use an empty `state_delta`.

No task-specific date, coordinate, answer, application procedure, evaluator
value, or hidden state was added.

Verification:

- protocol-v1 seal: 197/197 hashes, zero failures;
- task/action coverage: 19/19;
- full local tests: 129/129;
- correct native answer score: 1.0 in three isolation cycles;
- empty-cache score before each cycle: 0.0 in three cycles;
- wrong native answer score: 0.0;
- exact M0 state-delta form documented and regression-tested;
- no model/GPU cell was run as part of this Gate-D rerun.

The two completed Gate-E rerun 2 cells remain diagnostic and are not reused.
Gate E must restart from all eight cells under a new suite ID and freeze tag.
