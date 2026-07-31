# Protocol-v2.2 r55 development-candidate addendum

Status: local validation passed; isolated M0 Files smoke required

This addendum follows the stopped formal r54 Gate-E run. It preserves r54
malformed-coordinate input activation, r53 cross-modal freshness, all
post-destination Files guards, the one-commit boundary, and every prior
protocol artifact.

## Exact Back-repair rationale normalization

r54 completed four tasks with native reward `1.0` each. The fourth episode
stopped only because the sole bounded repair returned an exact permitted
`{"type":"press_back"}` action with a 242-character `decision_summary`, two
characters above the action schema's maximum.

r55 recognizes only this narrow case:

- the initial decision has already failed and consumed the one model repair;
- the validation error is a post-destination commit, source-exit, or
  completion-reobserve contract;
- the repaired response is strict JSON with `status="continue"`;
- its action is exactly `{"type":"press_back"}`; and
- `decision_summary` or `expected_outcome` is a string longer than 159
  characters.

Only the overlong rationale string is deterministically shortened to at most
159 characters. The parse audit records each field's before/after length and
SHA-256 hashes of the protected payload before and after normalization.

## Preserved boundary

r55 does not normalize initial responses, malformed/wrapped JSON, non-Back
repairs, or non-string fields. It does not add a model call or second repair.
It cannot alter `status`, `action`, coordinates, typed text, provenance,
citations, `state_delta`, or `completion_evidence`.

After normalization, the full action schema, exact repair contract, history
policy, same-turn adjudication, semantic guards, task success evaluator,
budgets and Gate-E criteria still run unchanged. An unrelated schema error or
unsafe action remains fatal.

## Required evidence

The exact r54 242-character repair trace is a positive regression: its safe
Back action becomes executable and the audit proves every protected field is
unchanged. Negative regressions prove that:

- an overlong non-Back repair is not normalized;
- an exact Back repair with another schema violation still fails; and
- both permitted rationale fields are bounded independently.

The exact candidate passed 399/399 project tests, 149/149 focused guard,
semantic-controller and full-memory-policy tests, compilation, diff
validation, and the unchanged 197/197 Protocol-v1 breadth seal.

No AndroidWorld action has run after the source change. The only authorized
next action is one fresh, isolated, non-scored M0 `FilesMoveFile` smoke under
an r55 development namespace after a zero-model-call preflight. Formal Gate E
and Gate F remain unauthorized.

