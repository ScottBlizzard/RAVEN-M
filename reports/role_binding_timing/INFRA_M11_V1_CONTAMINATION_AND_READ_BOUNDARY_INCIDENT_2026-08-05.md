# INFRA-M11 V1 contamination and read-boundary incident

**Incident verdict:** `READ_BOUNDARY_VIOLATION_RECORDED`

**M11 V1 status:** `NOT_AUTHORIZED_FOR_IMPLEMENTATION`

## Two events that must remain visible

First, M11 V1 was not independently clean. The same task that had already written the invalid pre-freeze M10 implementation later authored the M11 protocol and tests. Even without reopening that file, the authoring process had been exposed to the prior implementation effort. M11 V1 tests therefore cannot be presented as independent preregistration; at most, they were a DEV engineering contract.

Second, after the M11 freeze, the parent-supervision thread ran an overbroad read-only `rg` search for four process-view/role terms. Its scope unintentionally included the prohibited untracked M10 path, and several matching line fragments were printed. The file was not modified, copied, moved, staged, committed, or opened in full, and the fragment text was not forwarded to this task. Nevertheless, including the path in the read scope was a `READ_BOUNDARY_VIOLATION`. The fragments are prohibited design input.

## Contract gap found by read-only review

M11 V1 did not machine-freeze the source of role identities. A fixture or caller could supply a role-like field, and the proposed API did not make it impossible to trust that declaration. This is weaker than the committed M9 design, which derives mutually exclusive runner, candidate, support, and unrelated views from the complete raw process universe, the locked runner identity, locked project-binary paths, and controlled-port evidence, and recomputes attached views before authorization.

The missing negative directions include support-to-candidate escalation, unrelated-to-candidate escalation, fake runner root, candidate-reason tampering, known-path and port-evidence tampering, derived-class tampering, and classifier version/hash mismatch.

## Immutable and evidentiary boundaries

The original M11 freeze commit `a9b287a58ba61e96c88e6b14eaa56abbdc52d22c`, tag `role-binding-timing-infra-m11-freeze-20260805`, and tag object remain unchanged. This report does not rewrite the old freeze. It adds a later status record that makes implementation authorization false.

Generation calls, generation tokens, held-out captures, live chains, and test executions remain zero. No claim is supported about attestation correctness, infrastructure qualification, controller or memory efficacy, or the role-binding research hypothesis.
