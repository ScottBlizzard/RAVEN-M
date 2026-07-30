# Protocol-v2.2 r47 development-candidate addendum

Status: locally qualified; fresh M0 Contacts smoke failed on a separate
visible-control activation conflict

This addendum follows the r46 M0 Contacts development failure. It preserves
r46's live-qualified task-grounding change and every immutable r45/r46
artifact.

## Contract-conflict repair

The r46 screen displayed an empty input with a blue focus border after a tap,
but the accessibility digest did not report active input and the keyboard was
absent. `UNFOCUSED_CLEAR_TEXT_GUARD` correctly rejected the following
coordinate-bearing `clear_text=true` action and mandated a separate activation
tap. That exact repair tap then collided with
`UNVERIFIED_PROGRESS_REPEAT_REQUIRED`, which treated it as an ordinary repeated
policy action.

r47 adds one narrowly scoped validation flag. It is true only while validating
the sole bounded repair of an error whose prefix is exactly
`UNFOCUSED_CLEAR_TEXT_GUARD:` and only when the repaired action is a tap. If
that tap's complete semantic-state/action fingerprint exactly matches the
immediately preceding unverified-progress no-effect fingerprint, the loop
guard admits it once and records
`input_activation_repeat_override_count += 1`.

## Preserved safety boundary

The allowance does not apply when:

- the action comes from a normal policy step;
- the initial error has any other prefix;
- the repair action is not a tap; or
- the repair tap differs from the immediately preceding fingerprint.

After the tap executes, the existing controller marks one pending
input-activation proof. On the next transition that proof is consumed.
Repeating the tap again is blocked by `POST_ACTIVATION_INPUT_GUARD`; two
no-effect executions also retain the ordinary blocked-fingerprint threshold.
Text entry still requires task-bound provenance, and `clear_text=true` remains
forbidden until input readiness is established.

No loop threshold, task budget, action schema, model-call budget, executor,
memory rule, evaluator, or infrastructure path changes.

## Qualification boundary

The deterministic regression reproduces the full three-step chain:

1. a policy activation tap produces no semantic change and arms the ordinary
   unverified-progress repeat guard;
2. coordinate-bearing `clear_text=true` is rejected, and the bounded repair
   repeats the activation tap exactly once;
3. the next policy step enters the same task-bound text without coordinates
   and with `clear_text=false`, consuming the activation proof.

Ordinary repeated actions remain covered by the existing loop tests. The only
authorized live action after source freeze and zero-call preflight is one
fresh, isolated, non-scored M0 Contacts smoke on the same task instance.
The smoke was audited in
`reports/protocol_v2_2_r47_m0_contacts_smoke.{md,json}`. It did not reach the
r47 exception and is a valid failed development attempt: a visible,
accessibility-backed `+` control did not respond to its first tap, while the
ordinary policy and bounded repair both proposed the same still-visible
control and were blocked. r47 is therefore rejected for live use. Gate D and
formal Gate E remain unauthorized; only the bounded r48 development described
in the smoke report may proceed.
