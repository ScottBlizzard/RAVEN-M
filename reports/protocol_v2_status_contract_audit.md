# Protocol-v2 status-contract audit

Date: 2026-07-27  
Scope: `action.v2` and `action.raven.v2`, system prompts, bounded repair  
Purpose: close the full status/action contract before another Gate E run

| Case | B3 `action.v2` | M0 `action.raven.v2` |
|---|---|---|
| Continue | one GUI action; `state_delta=[]`; `memory_citations=[]` | one GUI action; structured `state_delta` or `[]`; `completion_evidence=[]` |
| Ordinary completion | `status=done`; `action=null` | `status=done`; `action=null`; `state_delta=[]`; at least one completion-evidence record |
| Information return | `status=done`; answer action with provenance | `status=done`; answer action with provenance; `state_delta=[]`; at least one completion-evidence record |
| Infeasible | `status=fail`; `action=null` | `status=fail`; `action=null`; `state_delta=[]`; `completion_evidence=[]` |

The audit also checks these shared constraints:

- all eight GUI action forms are exact JSON objects;
- normalized coordinates and canonical swipe endpoints are required;
- text and answer actions carry `text_origin` and `source_memory_ids`;
- verified-memory text cites exact routed FACT IDs;
- non-empty M0 state records use the complete fact structure;
- completion-evidence records use `claim`, `evidence`, and `memory_ids`;
- creating, editing, moving, deleting, saving, and sending remain ordinary
  GUI tasks even when the result screen displays a requested literal;
- a repair that receives “answer is permitted only for an
  information-return goal” must remove the answer and use `action=null`.

After the correction, the two v2 system prompts and the bounded repair prompt
explicitly cover every row in the table. Regression tests lock the canonical
GUI action forms, state-delta structure, and complete status/action matrix.
