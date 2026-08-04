# INFRA-M6 Display-Observability Audit

Date: 2026-08-05  
Mode: read-only reuse of frozen DEV infrastructure evidence  
Generation calls: 0  
Device mutations: 0

## Verdict

The M5 value `display_on=false` is a parser/command marker miss, not direct evidence that the physical display or framebuffer was off. The frozen parser searched `dumpsys window displays` for a `state ON` or `mState=ON` marker. That command's 20 frozen M5 samples do not contain this marker, although every sample contains the independently observable window/policy and power indicators listed below. A frozen output from the same installed Android build shows that `dumpsys display`, which M5 did not collect, is where this build emits `DisplayDeviceInfo ... state ON`, `mState=ON`, and `DisplayInfo ... state ON`.

This audit does **not** establish that M5 had a usable rendered frame. M5 captured neither `dumpsys display`, SurfaceFlinger evidence, nor a decoded screencap at the framework gate. The immutable M5 verdict therefore remains `RUNTIME_UNSTABLE:FRAMEWORK_NOT_STABLE`.

## Frozen evidence audit

| Direct observation | M5 result | Interpretation |
|---|---:|---|
| Frozen legacy parser returns `display_on=true` | 0/20 | Its expected marker is absent from the command it parses. |
| `mWakefulness=Awake` | 20/20 | Power manager reports awake. |
| `mStayOn=true` | 20/20 | Device is configured to remain awake. |
| `mHalInteractiveModeEnabled=true` | 20/20 | HAL interactive mode is enabled. |
| `mHoldingDisplaySuspendBlocker=true` | 20/20 | Display suspend blocker is held. |
| 1080x2400 current window display geometry | 20/20 | Window manager knows an active-sized display. |
| `mScreenOnEarly=true` and `mScreenOnFully=true` | 20/20 | Window policy reports screen-on progression complete. |
| Visible/visible-requested task | 20/20 | A task is reported visible. |
| Non-null current focus | 20/20 | Window manager reports a focused window. |
| `SCREEN_STATE_ON` and `INTERACTIVE_STATE_AWAKE` | 20/20 | Window policy independently reports on/interactive. |

All counts and SHA-256 identities are recorded in `display_observability_audit.json`. The same-build `dumpsys display` reference is DEV-contaminated and is used only to identify installed-output syntax, never as M5 success evidence.

## Claim-evidence matrix

| Claim | Verdict | Evidence boundary |
|---|---|---|
| The M5 parser missed the installed build's display-state location/format. | Supported | 0/20 old marker, 20/20 concordant nonlegacy markers, and same-build `dumpsys display` syntax. |
| The M5 physical display was OFF. | Not established | Marker absence is not an OFF observation. |
| The M5 physical display was ON and rendered correctly. | Not established | No display-service sample, SurfaceFlinger sample, or validated PNG at that gate. |
| A screenshot alone would establish framework health. | Rejected by protocol design | Rendering must agree with display, power, and window evidence. |
| M5 should be relabelled PASS. | Rejected | M5 remains frozen and immutable. |
| This evidence bears on role binding, memory, or model quality. | Unsupported | All evidence is DEV-only infrastructure telemetry with zero model calls. |

## M6 correction boundary

M6 must freeze a task-agnostic quorum before live execution:

1. display-service device and logical-display state;
2. power wakefulness, HAL interactive state, and display suspend blocker;
3. window/display geometry, focus/visible surfaces, and screen-on policy;
4. SurfaceFlinger/display evidence when the installed command exposes it; and
5. a strictly decoded PNG screencap with expected geometry, nontrivial bytes, and nonuniform pixels.

Missing or contradictory required evidence fails closed. Missing legacy text does not mean OFF; a screenshot alone does not mean the framework is healthy. Raw command bytes and the complete failure snapshot must be persisted for every gate.

The cleanup-only correction is separate: only the exact verified `qemu -> cmd.exe -> official emulator -kill` ancestry may be admitted during shutdown. It cannot authorize a process during the main framework verdict and cannot change the primary failure.

## Stop/continue decision

**CONTINUE_TO_M6_OFFLINE_IMPLEMENTATION_ONLY.** The audit supports a generic measurement correction. No live M6 chain is authorized until the new quorum, cleanup ancestry policy, corruption tests, protocol, config, schemas, and immutable lock all pass offline gates and are committed/tagged.
