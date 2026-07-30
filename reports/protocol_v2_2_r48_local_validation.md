# Protocol-v2.2 r48 local validation

Status: **local PASS; formal Gate E stopped after 4/8**

Parent commit:
`1f5fadee94042326c58216eee0a846f40e0044f4`

## Local evidence

- 369 tests collected and 369 passed.
- 133 focused guard, controller, repair-prompt, and reliability-recovery tests
  passed.
- The full-chain regression executes the first no-effect tap, blocks the next
  ordinary repeat, admits the exact bounded repair once, and observes the
  contact form open.
- The live-shaped audit has one visible-control override, one unverified
  progress block, and a structured `Create contact` accessibility record.
- Separate regressions reject Save, unnamed, editable, system, and keyboard
  controls.
- A repeated request for the same allowance is rejected, proving that a third
  identical tap cannot pass.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Change and compatibility

The controller computes a fresh accessibility assessment for every candidate
tap. It exposes the allowance only during repair of the exact r47
unverified-progress error shape. The guard consumes it only when the
assessment is permitted, the page/action fingerprint exactly matches the
immediately preceding no-effect fingerprint, and that fingerprint has never
used the allowance.

The special repair prompt explicitly permits one exact retry rather than
issuing the contradictory instruction to choose a different control. All
non-tap loop repairs retain the prior higher-level-navigation contract.

The action schema, Planner/executor base prompts, action executor, memory
subsystem, thresholds, evaluator, readiness logic, and runner are unchanged
from r47. r47's input-activation proof path and all task-grounding behavior
remain covered by the passing suite.

## Live smoke evidence

The frozen r48 candidate completed one fresh, isolated, non-scored M0
`ContactsAddContact` smoke with native AndroidWorld reward 1.0. It created
only `Sofija Martin` and `+17634322348`, observed the saved contact page, and
left Company, Email, and other optional fields untouched.

The add-contact tap initially had no semantic delta, but the form appeared
before the next model decision. The model did not request the same tap again,
so `visible_control_activation_repeat_override_count` remained zero. The new
r48 allowance is therefore still deterministic-branch-qualified rather than
live-trigger-qualified. In contrast, the preserved input-activation proof was
consumed once during the form interaction.

AndroidWorld environment construction first failed while reinstalling the
accessibility forwarder, then the runner cold-recovered the emulator and
recorded attempt 2 as successful. The episode itself was valid: 8 executed
steps, 15 model calls, one consequential-action adjudication, one completion
adjudication, no visible failure, no unresolved guard repair, and native
reward 1.0.

## Evidence boundary

This result is development-only and is not pooled with r45 or any formal
paired result. It qualifies end-to-end compatibility of the frozen candidate,
not live firing of the r48 allowance. Gate D subsequently passed: 369/369
tests, the 197/197 Protocol-v1 seal, 27/27 frozen files, the four locked task
instances, and the zero-call formal preflight all matched.

The authorized Gate-E launch then stopped after four native successes because
sequence 4 was invalid after one bounded repair. The file move itself passed
the native evaluator. The remaining conflict was a circular action-critic
rejection of the visible, task-named `Ringtones` folder tap used only to verify
the completed transfer. This consumes the r48 formal authorization; r48 may
not be resumed, and Gate F remains disabled.
