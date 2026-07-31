# Protocol v2.2 r62 H17 Candidate Preflight

## Decision

**PASS.** The exact r62 package is authorized for one non-scored H17/M0
development smoke at sequence 2. No formal Gate-F batch is authorized.

The preflight verified all 28 frozen files, all six paired task instances and
their restart stability, the 197-file protocol-v1 breadth seal, the exact
Qwen3-VL model revision, the frozen four-4090 backend, Android emulator
connectivity, and the absence of the fresh r62 suite directory.

The preflight made **zero model calls** and launched **zero GPU experiment
cells**. It cannot automatically start batch 1, a following batch, or Gate G.
The r61 suite remains stopped and immutable.

Machine-readable evidence:
`reports/protocol_v2_2_r62_h17_candidate_preflight.json`.
