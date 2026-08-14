# A1-R2 CVP Zero-Generation Qualification Summary

Date: 2026-08-14 (Asia/Hong_Kong)

Status: **PASS; live generation requires a fresh A1-R2 process receipt.**

- implementation commit: `ad7a39b55926408aa4a3c7101c9ff5cd83af4d80`
- parent evidence: BPR-v2's valid first-task capability-gate failure
- model writer protocol: exact frozen A1 `MEMORY[observed; verified; pending]`
- new response syntax: none
- ordinary-history memory duplication: removed
- resident memory: one latest `verified + pending` pair
- extra model calls, guards, overrides, forced terminations: zero
- complete official mobile regression: 287 passed
- runtime canary: p99 0.1233 ms; maximum 0.4709 ms
- generation calls during qualification: zero
- artifact bindings: canonical JSON hashes, invariant to CRLF/LF checkout policy

Real A1 trace replay covered 19 episodes and 596 executed actions. It parsed 515
valid A1 prefixes. All four A0 successes and the Recipe gain retained projected
write/read exposure. Projected rendered characters fell from 531,044 to 146,925
(27.6672% of A1). This is feasibility and cost evidence, not a live reward
claim.

The live order is immutable: A0 four with fail-fast 4/4, Recipe as the fifth
fail-fast sentinel, then the remaining fourteen. A first-task scientific
failure terminates the arm exactly as BPR-v2 did.

Machine-readable artifacts:

- `A1R2_CVP_OFFLINE_REPLAY_REPORT.json`
- `A1R2_CVP_SOURCE_FREEZE.json`
- `A1R2_CVP_ZERO_GENERATION_PREFLIGHT.json`
