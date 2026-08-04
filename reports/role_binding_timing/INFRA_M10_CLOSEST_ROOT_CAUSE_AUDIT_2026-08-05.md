# INFRA-M10 closest-root-cause audit

## Verdict

M9 remains permanently frozen as `FAIL_TEMPORAL_SUPPORT_ATTESTATION`. Its freeze/result tags, 236-file result manifest and protected-WIP hashes remain unchanged. The evidence supports **M10 offline implementation only**; no runtime, model or research-hypothesis claim is authorized by this audit.

## Closest verified defects

The 13 M9 failures split into exactly two observed cases:

- Twelve exact locked ADB helpers and their parents were present in the same history sample, but both had exited by the later framework check. M9 re-evaluated the historical child against the later current process universe, so its historical parent could not be found.
- One helper and its support parent were still current. The source `structural_processes` row contained the verified `cmd.exe` hash, but M9's support projection copied the un-enriched full row and omitted that hash.

The history serializer compounds both defects: candidate rows remain rich, while support rows pass through `compact_identity_universe`, which omits hash and command-line proof. These are the closest code-level causes. There is no evidence that the correct response is to relax parent, hash, port or role checks.

## M10 boundary

M10 may retain a run-local, same-atomic-sample ancestry attestation derived only from the M9-format complete snapshot. A support proof must preserve exact PID+creation identity, parent identity, executable/hash, command line, sample identity/time, source-record hash, snapshot/partition hashes and accessibility state.

The attestation may prove only what was observed in that sample. It cannot join different samples, cross runs, infer from PID/path alone, grant a support node a role, make it adoptable/killable, authorize a controlled-port owner, or revive authority after terminal expiry. Current evidence has priority and any conflict fails closed. An exited candidate may be classified historically but receives no current authority; a still-live candidate may use its birth attestation only after its current identity/hash/command still match and the original complete chain verifies.

## Claim–evidence boundary

- M9 verdict changed or reinterpreted: **no**.
- M10 root cause bounded to temporal/support-proof preservation: **yes**.
- M10 implementation, runtime, burn-in, a11y or grid: not tested.
- Held-out collection, model behavior, role binding and memory efficacy: not tested.

The machine-readable audit is under `05_project/artifacts/role_binding_timing/infra_m10_temporal_attestation_audit/`.
