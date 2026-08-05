# INFRA-M13 implementation lock

**Verdict:** `STATIC_IMPLEMENTATION_LOCKED_NOT_BEHAVIOR_TESTED`

## Exact implementation

- Commit: `3c739b66c41f5a20073cfeb0ecc55650be017ee9`
- Tree: `b69211a50e6d0c437a624c4d4cd98cb02de32577`
- Blob: `153df3036797771b2efd24bb60c3e22a166bef5e`
- SHA-256: `8257123377AFBD9328F13CCA6B1C3C8749A9B8D72B3888CA022F63B4E7C7CA8F`
- Source: `05_project/src/raven_m/role_binding_timing/infra_m13_proof_bound_attestation.py`
- Freeze commit: `fb697c67a724e75c602a65ed2713b75b750c1834`
- Freeze tag object: `28c1bd26d80e23578fbcaa5a30f42063f8d930ce`

The implementation commit contains exactly one source file. The implementation recomputes complete raw-and-locked authorization views and candidate ancestry before exact canonical comparison. Public hashes remain content addresses rather than authorization roots. Birth candidate and chain are reconstructed from the verified seal. Temporal authorization additionally requires an active entry in a nonserializable process-local ledger with CSPRNG run nonce and attestation ID; terminal tombstones the run and revokes its entries under the ledger lock.

## Single permitted static chain

The committed source was not changed after this chain.

- Contamination gate: PASS, zero findings, excluded paths not opened. Stdout SHA-256 `6CED52ABCD725C5CEF289EF3F286AB70B1EF3BAEA12B67B6B9B341D4845BCC90`.
- AST syntax: PASS. Stdout SHA-256 `73FCE23C3C45AD63859BBC9C1CC6FFFD92469E55CC696F880C20D52ECB9BAD56`.
- Import: PASS. Stdout SHA-256 `9DEBFE8613E5782777CD109B4A3DBA98887850B6745A389D9B3D4C134A3A662D`.
- All three stderr streams were empty; their SHA-256 is `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.

Runtime: `Python 3.11.9`, executable SHA-256 `21BB438C0D4A6F1F164B9A646F6EE000340185E5871180AEC06DB8D3F07C0082`.

## Explicit non-execution boundary

Both frozen pytest files are `NOT_RUN`. M9 compatibility replay, full regression, offline behavior runner, emulator/live chain, model generation, held-out capture, Stage 1, and Destination-First Gate were not run. All corresponding counters are zero.

This lock supports only a static implementation-existence claim. It does not show that the frozen behavior contracts pass or that proof binding, issuer-ledger behavior, infrastructure, controller behavior, memory efficacy, security, novelty, or generalization is correct.

The M12 runtime was not imported or copied; only its committed vulnerability findings were an input. The excluded untracked file remained visible through `git status` only, M11 was not read or reused, protected WIP hashes remained unchanged, LaTeX was not modified, and nothing was pushed.
