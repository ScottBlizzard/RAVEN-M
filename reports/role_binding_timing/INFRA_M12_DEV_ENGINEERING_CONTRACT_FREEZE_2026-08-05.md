# INFRA-M12 DEV engineering contract freeze

**Decision:** `FROZEN_NOT_IMPLEMENTED_NOT_TESTED_NOT_LIVE_ELIGIBLE`

**Freeze tag:** `role-binding-timing-infra-m12-freeze-20260805`

## Honest boundary

M12 is deliberately named a DEV engineering contract. It is informed by prior diagnosis and is neither an independent preregistration nor held-out evidence. The M10 leaked implementation and M11 V1 are excluded contamination/boundary records; neither is an implementation, test, or contract input for M12.

No M12 implementation exists. The role-source tests, temporal tests, and static contamination gate are frozen but have not been executed. Their exact status is `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.

## Role source is now machine-bound

Raw process rows cannot declare trusted roles. Authority labels, `observed_class`, candidate reasons, and lifecycle permissions in raw input cause fail-closed rejection.

The frozen classifier derives runner, candidate, support, and unrelated views from one complete atomic raw snapshot plus:

- exact locked runner PID, creation time, executable path/hash, and command line;
- locked project-binary paths and executable hashes;
- complete controlled-port ownership evidence;
- classifier version and contract hash;
- a future separately locked implementation SHA-256 and Git blob OID.

Every sealed view binds the raw snapshot, classifier, runner, known paths, ports, candidate reasons, parent chain, and every partition hash. Current verification must recompute classification from raw evidence. It cannot trust stored classes or hashes alone.

The role/view-source tests must pass before temporal tests may run. Added negative directions include support-to-candidate, unrelated-to-candidate, fake runner, candidate-reason tampering, path/port tampering, derived-class tampering, classifier mismatch, raw/sealed mismatch, and PID creation-time reuse. A locked replay compares M12 membership with the exact committed M9 derivation.

## Frozen future boundary

Any offline failure stops before live. Only after unchanged offline gates pass and a separate implementation hash/blob lock is reviewed may one DEV chain become eligible. Its order remains exclusive 5038, launch, boot, display/framework, 24 cycles over 180 seconds, Settings a11y 3/3, and a 4-by-3 DEV grid. First failure stops the chain; same-version retry is forbidden.

Generation calls, tokens, held-out captures, Stage 1 runs, Destination-First runs, and live chains are all zero. This freeze supports no claim about implementation correctness, infrastructure qualification, task success, memory efficacy, role-binding effects, novelty, or generalization.
