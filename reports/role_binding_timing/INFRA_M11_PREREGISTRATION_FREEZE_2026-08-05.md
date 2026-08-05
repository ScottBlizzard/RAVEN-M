# INFRA-M11 preregistration freeze

**Decision:** `FROZEN_NOT_IMPLEMENTED_NOT_LIVE_ELIGIBLE`

**Frozen tag:** `role-binding-timing-infra-m11-freeze-20260805`

INFRA-M11 is a preregistration-first recovery namespace. This commit freezes the protocol, immutable inputs, first-broken-edge rule, result schema, static contamination gate, behavioral fault matrix, and single future live-chain rule before any M11 attestation implementation exists.

## What is frozen

- Same-run, same-atomic-sample parent-chain evidence only.
- Lossless support projection with PID + creation-time identity, parent identity, executable path/hash, command line, sample metadata, record/snapshot/partition hashes, accessibility status, and ports.
- No cross-sample stitching, cross-run reuse, PID-only or path-only inference.
- Current evidence has priority; any conflict with history fails closed.
- Support nodes permanently lack role, adoption, kill, cleanup, port, and independent authorization rights.
- Attestation expires at terminal completion.
- First failure is immutable and stops a future run.
- At most one future chain under this exact frozen protocol; no patch-and-retry.

## Contamination boundary

The M10 leaked implementation is permanently DEV-contaminated and is not an M11 input. Its frozen metadata is recorded only so the static gate can reject its path, filename, module identifier, known hash, or an exact content-hash copy without reading the leaked file. M11 uses a distinct implementation path, test path, config namespace, and artifact roots.

## Preimplementation status

- M11 implementation: absent.
- Preregistered tests: written but not executed.
- Expected test state: `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.
- Static contamination gate: written but not executed.
- Generation calls/tokens, held-out captures, and live chains: 0.
- Live eligibility: false.

The tests being present is not evidence that the implementation works. No offline gate is claimed to have passed.

## Claim–evidence boundary

This freeze proves only that the M11 rules and planned falsification surface preceded implementation. It does not prove attestation correctness, infrastructure stability, AndroidWorld task performance, controller or memory efficacy, role-binding effects, novelty, or generalization. A later implementation can become live-eligible only after all frozen offline tests pass unchanged and a separate review authorizes the one frozen DEV chain.
