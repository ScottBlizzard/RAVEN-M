# INFRA-M12 implementation lock

**Verdict:** `STATIC_IMPLEMENTATION_LOCKED_NOT_BEHAVIOR_TESTED`

## Exact implementation

- Implementation commit: `a8d3a831eea53fbf075eea6b8e5c3401e435fdf8`
- Source path: `05_project/src/raven_m/role_binding_timing/infra_m12_sealed_role_derivation.py`
- Git blob: `922222aeec7bdb690d225b2018da0288604eb0bb`
- SHA-256: `73D8138F9ECEFA5B31F975968257FA779AFCD466CE93F67808C42A05544A336C`
- Bound freeze: `08aa4182e1fe7fdff0def2b19193b4b3f7b69266`
- Implementation-lock tag: `role-binding-timing-infra-m12-implementation-lock-20260805`

The committed module derives all four process views from complete raw process evidence and locked inputs. It rejects authority labels in either raw source, fuses records by exact PID plus creation time, binds the classifier and every partition, recomputes views on verification, and keeps support non-authoritative. The M9 compatibility route is explicitly replay-only and cannot be sealed or used for authority.

## Static checks only

Exactly one ordered static check chain ran against the same bytes later committed:

1. Static contamination gate: PASS, zero findings, excluded paths opened = false.
2. Python `ast.parse`: PASS.
3. Import with bytecode writing disabled: PASS.

There was no patch or retry after this chain. The frozen role tests and temporal tests were not run. The M9 compatibility replay, offline behavior runner, emulator, model, held-out collection, and live chain were not run.

## Claim boundary

This lock supports only a static implementation identity claim. It does not show that role derivation, sealing, current-evidence conflict handling, temporal attestation, or the 12-exited/1-current case behaves correctly. It does not qualify infrastructure, controllers, memory methods, or the research hypothesis.

Generation calls, generation tokens, held-out captures, Stage 1, Destination-First, and live chains remain zero. M9/M10-invalid/M11/M12-freeze objects are unchanged; protected WIP remains outside the commit; no LaTeX or remote repository was modified.
