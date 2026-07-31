# Protocol-v2.2 r55 local validation

Date: 2026-07-31  
Candidate source: `66370821e2fd7577d8c7a508f80297ae1a4b1513`  
Tag: `protocol-v2-2-r55-local-candidate`  
Decision: **local pass; one isolated M0 Files smoke authorized**

## Why r55 exists

Formal r54 stopped at 4/8 even though every executed task received native
reward `1.0`. In the fourth cell, the sole repair returned the exact required
Back action, but its `decision_summary` was 242 characters against a
240-character schema maximum.

r55 deterministically bounds only `decision_summary` and
`expected_outcome`, only for an exact post-destination Back repair after the
model's one repair has already been spent. It records before/after lengths and
matching protected-payload hashes.

## Validation

- 399/399 project tests passed.
- 149/149 focused guard, semantic-controller and full-memory-policy tests
  passed.
- The exact 242-character r54 repair now produces the required Back action
  with a 159-character rationale and an explicit normalization audit.
- An overlong non-Back repair remains invalid.
- An exact Back repair with unrelated invalid completion evidence remains
  invalid even after rationale normalization.
- Both rationale fields are independently bounded.
- `compileall` and `git diff --check` passed.
- The unchanged Protocol-v1 breadth seal verified 197/197 files with zero
  failures; seal SHA-256 is
  `8b707052bbf3d22ff9643dc1fd4bc55d8f09461a00be9c13728e6eacdfa37ac9`.

## Evidence boundary

This is deterministic local evidence only. No server/GPU/AndroidWorld action
has run after the r55 source change. The single authorized next action is a
fresh non-scored M0 `FilesMoveFile` development smoke after a zero-call
preflight. Gate D, formal Gate E and Gate F remain unauthorized.

