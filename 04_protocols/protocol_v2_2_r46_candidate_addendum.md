# Protocol-v2.2 r46 development-candidate addendum

Status: locally qualified; fresh M0 Contacts smoke pending

This addendum follows the stopped r45 Gate-E restart. It preserves every r45
result and does not reinterpret the incomplete five-cell suite as a paired
method comparison.

## Failure-derived scope

The r45 sequence-5 task asked for a contact name and phone number only. M0
introduced an unsupported `company_name`, proposed invented `TechCorp`, and
then used its sole repair to type the correct phone number into a different,
unfocused field with `clear_text=true`. The existing declared-source and
unfocused-input safeguards correctly blocked both actions, so no unsafe text
executed. The formal runner then stopped as preregistered.

r46 closes the gap between those safeguards without weakening either one.

## Task-grounded planning

The Planner contract now requires every user-entered value and task variable
to come from an explicit task requirement. A visible blank optional field may
guide navigation but cannot create a new payload requirement. Company, email,
note, label, placeholder, example, and default values remain absent unless the
task explicitly supplies them. An invented optional variable from a previous
plan must be removed on the next refresh.

The shared Protocol-v2.2 turn prompt repeats the same scope boundary for both
B3 and M0: fill or mutate only fields and values explicitly required by the
task, and leave visible blank optional fields untouched.

## Cross-field source repair

When `DECLARED_TEXT_SOURCE_GUARD` rejects invented or relabelled text, the sole
bounded repair may no longer type or answer. If a visible empty field matches
a remaining task value, the repair may only tap that role-matched field to
activate it. Text entry is deferred until a later policy step has observed the
focused input or keyboard. The subsequent step remains subject to all existing
text provenance, field-role, focus, clear-text, loop, and action-schema checks.

The controller supplies no text, field coordinate, or app-specific action. The
model must bind the activation tap from the unchanged screenshot.

## Frozen invariants and qualification boundary

r46 changes no model, seed, task instance, evaluator, schema, action budget,
model-call budget, memory lifecycle, guard threshold, action executor,
readiness accounting, infrastructure retry, or Protocol-v1 artifact. It does
not modify either executor system prompt; the per-turn scope instruction is
shared by B3 and M0.

The only authorized live action after source freeze and zero-call preflight is
one fresh, non-scored M0 `ContactsAddContact` smoke using the same frozen
instance that exposed the r45 failure. It must demonstrate:

1. no invented optional value is planned or typed;
2. the exact name and phone number are preserved;
3. any cross-field transition separates activation from text entry;
4. all executed actions pass existing guards; and
5. the episode ends with valid output after at most one bounded repair.

The smoke may qualify r46's behavior but is not pooled with r45, does not prove
method superiority, and cannot by itself pass Gate E.
