# Protocol-v2.2 r48 development-candidate addendum

Status: locally qualified; fresh M0 Contacts smoke passed; Gate-D freeze pending

This addendum follows the valid r47 M0 Contacts development failure. It
preserves r46's live-qualified task grounding, r47's locally qualified
input-activation repair, and every immutable r45-r47 artifact.

## Visible-control activation retry

The r47 Contacts screen exposed a visible add-contact `+` control. The first
tap was delivered but did not change the 11-element accessibility state. On
the unchanged page, both the next policy response and its bounded repair
selected the same still-visible control. The ordinary unverified-progress
guard rejected both responses, even though no alternative direct control
could open the required form.

r48 separates this lost-control-activation case from open-ended repetition. A
bounded repair may repeat the immediately preceding tap exactly once only
when current accessibility evidence binds the coordinate to at least one
control that is:

- explicitly visible;
- explicitly enabled;
- explicitly clickable;
- owned by a non-system, non-keyboard application package;
- non-editable;
- bounded at the proposed coordinate; and
- named by visible text, content description, hint, or tooltip.

Every matched control must also be non-commit-like. Labels containing Save,
Delete, Remove, Send, Submit, Confirm, Done, Yes, Purchase, Buy, Pay, Install,
Order, Transfer, Upload, Download, Call, Message, Copy, Move, Share, Publish,
Accept, Authorize, or equivalent mutation terms are denied.

## Single-use and audit boundary

The allowance is available only while validating the sole bounded repair of
`LOOP_GUARD: ... UNVERIFIED_PROGRESS_REPEAT_REQUIRED` and only for a tap whose
complete semantic-page/action fingerprint exactly equals the preceding
no-effect fingerprint. The guard stores each admitted fingerprint in a
single-use set and emits both a count and a structured record containing the
accessibility assessment.

The same fingerprint cannot consume the allowance again. If the second tap
also produces no semantic change, the ordinary no-effect threshold blocks
the fingerprint and any third identical tap remains invalid. A visible
failure also retains the ordinary blocked-fingerprint path.

## Preserved safety boundary

The allowance does not apply to:

- normal policy responses;
- swipes, long presses, text actions, open-app actions, or terminal responses;
- screenshot-only states without accessibility elements and controls without an
  application package;
- disabled, non-clickable, editable, unnamed, or out-of-bounds targets;
- commit-like controls;
- a changed semantic page or a different action fingerprint; or
- any fingerprint that already consumed this allowance.

r47's input-field activation exception remains separate and unchanged. No
loop threshold, task budget, model-call budget, action schema, executor,
memory rule, evaluator, readiness rule, text provenance rule, task-scope
rule, or completion rule changes.

## Qualification boundary

Deterministic regressions reproduce the full r47 failure shape:

1. a named `Create contact` control receives one tap with no semantic change;
2. the next ordinary identical tap is rejected;
3. the sole bounded repair repeats the exact tap and is admitted once;
4. the second execution opens a semantically different contact form; and
5. the audit records one override and one ordinary validation block.

Additional regressions deny Save, unnamed, and editable targets and prove
that a third identical tap remains blocked even when the caller again
requests the allowance.

The one authorized fresh, isolated, non-scored M0 Contacts smoke passed with
native AndroidWorld reward 1.0. It created exactly `Sofija Martin` with
`+17634322348`, executed Save, observed the resulting contact page, and did
not populate any optional field.

The first add-contact tap initially produced an unchanged semantic snapshot,
but the form became visible before the next policy decision. The model
therefore progressed to First name rather than proposing the same add-contact
tap. Consequently, the r48 visible-control allowance was not consumed in this
live run and remains deterministically, not live, branch-qualified. This is
not treated as evidence that the allowance fired.

The smoke does establish end-to-end compatibility of the frozen r48 source,
model identity, task grounding, input-activation repair, consequential-action
adjudication, completion adjudication, and native evaluation. A formal Gate-D
freeze may now be prepared. Formal Gate E must still use a fresh suite,
unchanged frozen source, the locked four instances and eight paired cells,
and a separate zero-call preflight. Gate F remains manual-only.
