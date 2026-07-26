# Protocol-v2 Gate D rerun 4

Date: 2026-07-27  
Implementation commit: `b8b334944a41b437e39a48cc1d82a34192c66f77`  
Trigger: Gate-E rerun 4 partial required-field repair  
Decision: **PASS**

Both v2 system prompts now include a complete top-level response skeleton.
The bounded repair prompt lists every required base field, conditionally adds
M0 completion evidence, and explicitly requires all validator-listed missing
properties to be fixed in the single permitted repair.

Verification:

- protocol-v1 seal: 197/197 hashes, zero failures;
- task/action coverage: 19/19;
- full local tests: 132/132;
- correct native answer score: 1.0 in three isolation cycles;
- empty-cache score before each cycle: 0.0 in three cycles;
- wrong native answer score: 0.0;
- live 32B missing-field repair: strict JSON and schema-valid;
- live 32B forbidden-answer repair: `status=done, action=null`;
- live repair calls executed zero GUI actions and accessed no evaluator;
- no experimental Gate-E or Hard cell was run during Gate D.

The two completed Gate-E rerun 4 cells remain diagnostic and are not reused.
Gate E must restart from all eight cells under a new suite ID and freeze tag.
