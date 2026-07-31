# Protocol-v2.2 Gate-E r53 stopped report

Date: 2026-07-31  
Frozen source: `f3d7c9d3c33e54245138fc56336027f533b67f17`  
Tag: `protocol-v2-2-gate-e-r53`  
Decision: **STOPPED at 1/8; Gate E did not pass**

## Bottom line

The formal r53 Gate-E runner stopped correctly after the first scored cell.
The fresh second `B3 / ContactsAddContact` attempt executed six actions but
did not save the contact. Its seventh decision remained invalid after the
single bounded repair, so sequences 2-8 were not executed and Gate F remained
disabled.

The first infrastructure attempt never reached a task action or model call
because AndroidWorld could not retrieve an accessibility tree. It was
archived, excluded from scoring, and followed by a passing cold-recovery
smoke. The scored second attempt was fresh.

## Formal cell result

| Seq. | Variant | Task | Native reward | Executed steps | Calls | Termination |
|---:|---|---|---:|---:|---:|---|
| 1 | B3 | `ContactsAddContact` | 0 | 6 | 12 | invalid after repair |
| 2-8 | — | — | — | — | — | not executed |

The second attempt retained 16 readiness observations and three readiness
retries. No unsafe text action executed. The cell nevertheless failed both
the native evaluator and the frozen 100% valid-output requirement.

## Causal trace

At step 6, the screen showed:

- first name `Sofija` and last name `Martin` already entered;
- the empty Company field still focused;
- the empty Phone field visible but not input-ready; and
- the soft keyboard dismissed.

The model proposed the correct task-literal number but used `y=638`, which is
outside the normalized `[0,1]` coordinate schema. The one bounded repair
changed it to `y=0.638` but kept `type_text` and `clear_text=true`.

The existing `UNFOCUSED_CLEAR_TEXT_GUARD` correctly rejected that repair.
AndroidWorld would click the Phone field and immediately send Ctrl+A; focus
activation can race, so the controller requires a separate activation tap
and a later observed text step. Because the outer schema error had already
consumed the one repair, the inner focus requirement could not be repaired in
the same decision.

This is a serial-validation blind spot, not a reason to weaken the focus
guard or accept pixel coordinates.

## Bounded r54 direction

r54 is restricted to malformed coordinate-bearing `type_text` responses
whose text is already verified as an unchanged task literal. Its one repair:

1. must be a pure normalized `tap`;
2. must hit a visible editable field;
3. must match the semantic role of the original task value; and
4. may only establish one-step input-activation proof.

Typing, clearing, navigation and commits remain forbidden in that repair.
The exact r53 repair—direct `type_text` at `y=0.638`—is now an explicit
negative regression case.

The r53 directory is immutable and must not be resumed. Only one isolated,
non-scored B3 Contacts smoke may follow complete r54 local validation.

## Evidence boundary

This is an incomplete non-Hard protocol requalification. It is neither a
paired B3/M0 comparison nor Hard benchmark evidence.
