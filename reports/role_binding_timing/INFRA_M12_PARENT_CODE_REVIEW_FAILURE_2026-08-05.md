# INFRA-M12 parent code-review failure

**Status:** `NOT_AUTHORIZED_FOR_OFFLINE_GATES`
**Review verdict:** `FAIL_PROOF_BINDING_AND_ISSUER_AUTHORITY`

This is an additive review record. The M12 protocol, implementation, implementation lock, commits, and tags remain immutable. No frozen role test, temporal test, offline runner, or live chain was executed.

## Locked subject

- Freeze commit: `08aa4182e1fe7fdff0def2b19193b4b3f7b69266`
- Implementation commit: `a8d3a831eea53fbf075eea6b8e5c3401e435fdf8`
- Implementation blob: `922222aeec7bdb690d225b2018da0288604eb0bb`
- Implementation SHA-256: `73D8138F9ECEFA5B31F975968257FA779AFCD466CE93F67808C42A05544A336C`
- Implementation-lock commit: `889788c21eca08f23eed5afcfb41fdb432d34667`
- Implementation-lock tag object: `a05e89ab619ffb48962cc717c4db724ec9448943`

## Independently confirmed defects

1. `_validate_supplied_views` at locked lines 682–691 checks identity sets and candidate reasons, not complete canonical equality between every supplied row and the recomputed row. Mutated non-identity and proof fields can therefore survive this gate.
2. `_proof_mismatch_code` at lines 772–781 compares stored hash strings rather than recomputing the source-record hash from the stored row. Lines 863–887 then verify partition, complete-view, and seal hashes that an untrusted caller can recompute. Ordinary SHA-256 provides content addressing here, not authorization.
3. `verify_temporal_attestation` at lines 1053–1069 validates the birth candidate only by identity and the chain only by sample sequence/time. It does not extract the candidate from the verified sealed view or rebuild the exact chain from `candidate_ancestry` and sealed records. A changed candidate or chain plus a recomputed attestation hash is not independently anchored.
4. `_RUN_EPOCHS` at lines 891–905 is process-local mutable memory, but issued attestations carry no unpredictable run nonce, attestation ID, or issuer-ledger membership proof. A hand-built object can assert the current run/epoch, while restart leaves no membership basis for distinguishing an old serialized object. The frozen terminal test covers only same-process expiration.

These are direct code observations. The bypass descriptions are security consequences inferred from the missing bindings; no exploit test was run.

## Why tests must not run first

The frozen M12 tests do not require complete row equality, exact sealed-view reconstruction of birth evidence, or current-process issuer-ledger membership. Even a future all-green result would therefore be insufficient to prove the contract semantics. Running them now would add cost without resolving the proof gap and could create a misleading pass signal.

## Claim–evidence boundary

Supported: the exact locked M12 blob contains the four defects above, and M12 is not authorized for offline gates or live execution.

Not supported: implementation correctness, infrastructure qualification, task success, role-binding or memory effects, novelty, held-out behavior, or generalization.

Generation calls/tokens, held-out captures, Stage 1, Destination-First Gate, offline behavior tests, and live chains are all zero. Protected WIP hashes and old frozen objects remain unchanged. The M10 leaked file was not opened; its existence was observed only through `git status`. M11 V1 was not read or reused. LaTeX was not modified and nothing was pushed.
