# INFRA-M13 parent code-review failure

**Status:** `NOT_AUTHORIZED_FOR_OFFLINE_GATES`

**Review verdict:** `FAIL_CALLER_SUBSTITUTABLE_AUTHORITY_CONTEXT_AND_INCOMPLETE_ANCESTRY`

This is an additive audit record. The M13 freeze, implementation, implementation lock, commits, and tags remain immutable. No frozen pytest, M9 replay, offline runner, or live chain was executed.

## Locked subject

- Implementation commit: `3c739b66c41f5a20073cfeb0ecc55650be017ee9`
- Implementation blob: `153df3036797771b2efd24bb60c3e22a166bef5e`
- Implementation SHA-256: `8257123377AFBD9328F13CCA6B1C3C8749A9B8D72B3888CA022F63B4E7C7CA8F`
- Implementation-lock commit: `dc48ef630a71528458291a9ad5e851f09c047b17`
- Implementation-lock tag object: `c80066c12e2f10f75812c8ebce4a7d1dd477c67f`

## Independently confirmed defects

1. Locked lines 348–374 compare an observed row only with the `locked_runner_record` supplied by the same caller. Derive and verification continue to accept caller-provided runner, known paths, and ports, while `begin_issuer_run` at lines 887–905 has no authority-context parameter. There is no independently initialized capability preventing a caller from selecting a different real process as the root and supplying matching fields.
2. `_canonical_ports` at lines 336–345 accepts any unique subset of the five controlled ports. An empty or reduced set can delete evidence for ports such as 5038 or 5554.
3. `_listener_map` at lines 183–204 validates syntax but never proves each owner PID resolves to exactly one fused process identity. Unknown or ambiguous controlled-port owners can therefore be silently ignored by row-based candidate derivation.
4. Lines 478–518 collect candidate reasons before ancestry qualification and add observed chain nodes to support even when `complete` is false. Lines 530–552 emit every candidate-like identity and partial support identity into their views. Complete same-frame ancestry ending at the exact root is not an authorization prerequisite.

These are direct locked-code observations. The substitution and weakening scenarios are security consequences inferred from the missing authority bindings; no behavior or exploit test was run.

## Test boundary

The frozen M13 matrices do not establish an opaque authority root, exact full-port equality, listener-owner universe membership, or complete-root ancestry before candidate/support projection. Even an all-green run would not close these proof gaps. M13 therefore must not enter offline gates.

Generation calls/tokens, held-out captures, Stage 1, Destination-First Gate, frozen tests, M9 replay, offline runner, and live chains are all zero. Protected WIP hashes and old tags remain unchanged. The excluded untracked file was not opened; M11 was not read or reused. LaTeX was not modified and nothing was pushed.
