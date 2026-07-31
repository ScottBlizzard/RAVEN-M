# Protocol-v2.2 r54 development-candidate addendum

Status: local validation passed; isolated B3 Contacts smoke required

This addendum follows the stopped formal r53 Gate-E run. It preserves r53
before-decision cross-modal freshness, r52 post-activation clear-text
protection, r51 exact destination-label binding, r50 source-exit behavior,
the one-commit boundary, and all prior protocol artifacts.

## Malformed-coordinate input activation

r53 exposed a two-layer validation conflict. An otherwise source-grounded
`type_text` response used `y=638`, so schema validation consumed the single
bounded repair. The repaired response used normalized `y=0.638` but still
attempted `clear_text=true` on a visible, inactive Phone input. The
`UNFOCUSED_CLEAR_TEXT_GUARD` correctly rejected it, but no repair remained.

r54 recognizes only this narrow precursor:

- the original action is `type_text`;
- its text is a non-empty `task_literal`;
- `source_memory_ids` is exactly empty; and
- at least one supplied x/y field lies outside normalized `[0,1]`.

The controller does not normalize, invent, or supply a coordinate. Instead,
the bounded repair must return one normalized `tap`. The repair is accepted
only when the tap hits a visible editable field, the original task literal is
verified against the task, and the target field's semantic role matches that
literal. The repair cannot type, clear, navigate, wait, save, or commit.

After execution, the existing one-step input-activation proof applies. Text
may be entered only on a later observed policy step under the unchanged
focused-input and post-activation guards.

## Preserved boundary

r54 does not accept pixel coordinates, add a model call, add a repair,
execute controller-supplied coordinates, weaken text provenance, weaken
field-role binding, bypass `UNFOCUSED_CLEAR_TEXT_GUARD`, or change an action
schema, prompt, task, seed, evaluator, budget, memory policy, readiness rule,
success definition, or Gate-E acceptance criterion.

## Required evidence

The positive deterministic regression begins with an out-of-range
task-literal Search coordinate. Its only repair activates the visible Search
input, a later observed step types without coordinates or Ctrl+A, and the
input-activation proof is consumed.

The negative regression reproduces r53's repaired direct `type_text`; the new
repair contract rejects it before execution.

The exact candidate passed 395/395 project tests, 145/145 focused guard,
controller, and full-memory-policy tests, compilation, diff validation, and
the unchanged 197/197 Protocol-v1 breadth seal.

No post-change AndroidWorld action has run. The only authorized next action is
one fresh, isolated, non-scored B3 `ContactsAddContact` smoke under an r54
development namespace after zero-model-call preflight. Formal Gate E and Gate
F remain unauthorized.
