# Protocol-v2.2 r43 M0 Expense development smoke

Status: **INVALID INFRASTRUCTURE-CONTAMINATED ATTEMPT; r43 not adjudicated**

Candidate source:
`5e3af39f2d11423333dbe7510228628d3c95598f`

## Recorded outcome

The runner recorded native reward 0.0 after 12 actions and 20 model calls.
The agent never reached category navigation because it spent steps 7-11
trying to repair a corrupted Name value, `EducEducational`.

The suite summary reports zero infrastructure attempts because AndroidWorld's
internal ADB retry eventually returned success. That accounting is
insufficient for this trajectory.

## Hidden non-idempotent ADB retry

The retained stderr log records:

`adb shell input text Educational` timed out after 10 seconds on its first
attempt.

AndroidWorld's `AdbController.execute_command` retries failed device commands.
Text input is non-idempotent: the timed-out command had already entered the
prefix `Educ`, and the retry entered the full `Educational`. The step-6
screenshot therefore shows the exact concatenation `EducEducational`.

The model supplied the correct task literal and the r42/r43 activation proof
removed its coordinates as designed. The corrupted value arose below the
policy/controller boundary. The later long-press, wait, and refocus actions
are downstream recovery from executor corruption, not evidence about r43's
progress-conditioned swipe rule.

This attempt also contained a first-click no-effect on the plus button and an
accessibility-forwarder refresh, but the text-command timeout provides direct
causal evidence for the invalidating mutation.

## r44 executor boundary

r44 must make `clear_text=true` idempotent at the same boundary where ADB may
retry it:

1. focus the coordinate target first when one is model supplied, preserving
   existing semantics;
2. issue select-all, delete, and the model-authored text as one compound ADB
   request, so every internal retry begins by clearing any partial first
   attempt;
3. keep `clear_text=false` behavior unchanged;
4. propagate a final ADB failure so the runner archives and retries the cell
   as infrastructure rather than exposing partial text to the agent; and
5. add no hidden text, coordinate, or policy action.

The r43 swipe rule remains locally qualified but has not received valid live
evidence.

## Evidence boundary

The raw directory, stderr, screenshots, and hashes are retained. This attempt
is not a method failure, is not pooled with any prior smoke, and does not
authorize Gate D or formal execution.
