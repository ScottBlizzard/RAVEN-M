# INFRA-M6 Display-Observability v1

## Scope and immutable predecessor

M6 is one zero-model, DEV-only infrastructure chain. M5 remains immutable `RUNTIME_UNSTABLE:FRAMEWORK_NOT_STABLE`; this revision does not relabel it. It makes no held-out capture, model, memory, controller, or role-binding claim and cannot launch Phase C. The three legacy r79 WIP files remain unstaged and hash-protected.

## Falsifiable infrastructure question

Can one preregistered, task-agnostic observation quorum distinguish a usable rendered display from missing/version-mismatched legacy text while preserving the M4/M5 process, port, journal, external-log, cleanup, and stop boundaries?

PASS only authorizes preparation—not execution—of a separately reviewed v0.3 collection protocol.

## Display quorum

Every framework sample and burn-in cycle persists raw command bytes, hashes, process snapshots, the parsed planes, and the verdict. The required planes are conjunctive:

1. `dumpsys display`: an internal physical device is ON, any reported committed state is ON, logical display state is ON, and geometry is 1080x2400;
2. `dumpsys power`: wakefulness is Awake, HAL interactive mode is true, and the display suspend blocker is held;
3. window manager/policy: expected geometry, a focused window, a visible surface/task, and screen-on/interactive evidence;
4. `screencap -p`: strict PNG decode, at least 4096 bytes, exact 1080x2400 geometry, and nonuniform sampled pixels.

SurfaceFlinger is optional only when its command is unavailable or empty. If it returns output, the output must contain recognized display/composition evidence; explicit OFF/disconnected/disabled evidence vetoes the quorum. Missing required evidence or any contradiction fails closed. A missing M5 legacy marker is not OFF, and a screenshot alone is never full framework authority.

Framework readiness requires three consecutive passing samples within 20 bounded attempts. Burn-in requires 24/24 passing cycles and at least 180 seconds. The first failed cycle stops the chain and writes a full failure snapshot.

## Cleanup-only process authority

M5 process identity remains the base policy. M6 adds exactly one secondary cleanup authorization: the locked qemu must parent the locked `cmd.exe`, whose exact command starts the locked official emulator helper with `-kill <registered-qemu-pid> -sleep 20`; the helper's path, hash, command, start ordering, and full ancestry must all match. It is never authorized outside `cleanup`, cannot change the primary framework verdict, and no PID-specific exception exists.

5037 remains forbidden. The registered 5038 identity, qemu identity, and port ownership may not restart or drift.

## Offline gates

Before the live chain, M6 requires:

- fixture/corruption tests for installed Android output variants, true OFF, missing/contradictory fields, unavailable and contradictory SurfaceFlinger, invalid/truncated/wrong-size/uniform PNG, and screenshot-only rejection;
- exact cleanup ancestry tests for phase, path, hash, command, PID/start identity, parent, and qemu chain;
- M4 terminal-accounting, M5 identity, complete role-binding namespace, and full-project regressions;
- schema corruption, source-isolation, frozen binary/hash, protected-WIP, empty-output, external-log-residue, no-listener, and zero-generation preflight;
- a machine-readable lock committed and tagged before live mutation.

The known frozen r79 manifest conflict is reported exactly and is the only accepted full-regression failure.

## One frozen live chain and stopping rule

One fresh M6 output root is permitted: exclusive 5038 launch, boot, display/framework quorum, 24-cycle/180-second burn-in, Settings same-observation screenshot+a11y 3/3, four-app by three-round DEV grid 12/12, qualified cleanup, external-log sealing, and independent terminal completion.

Any failure stops later gates. Cleanup/seal evidence is secondary and cannot replace the first broken edge. Only a complete 12/12 DEV PASS may set `v0_3_preparation_authorized=true`; even then, no v0.3 capture is run in M6.
