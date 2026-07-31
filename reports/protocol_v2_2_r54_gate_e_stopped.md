# Protocol-v2.2 Gate-E r54 stopped report

Date: 2026-07-31  
Frozen source: `54adaf031abd87dc5c420bd1d8d07acc8c0a4b94`  
Tag: `protocol-v2-2-gate-e-r54`  
Decision: **STOPPED at 4/8; Gate E did not pass**

## Bottom line

The formal r54 Gate-E runner stopped correctly after four scored cells. All
four completed tasks received AndroidWorld native reward `1.0`, including
`M0 / FilesMoveFile`. The suite nevertheless failed the frozen valid-output
criterion because the Files episode's seventeenth decision remained invalid
after the single bounded model repair.

The invalidity was confined to a non-executable rationale field. The repair
returned the exact safe `{"type":"press_back"}` action required by the
post-destination repair contract, but its `decision_summary` was 242
characters, two above the schema's 240-character maximum. The action was not
executed, sequences 5-8 were not run, and Gate F remained disabled.

## Formal cell results

| Seq. | Variant | Task | Native reward | Model calls | Termination |
|---:|---|---|---:|---:|---|
| 1 | B3 | `ContactsAddContact` | 1.0 | 16 | `model_done` |
| 2 | M0 | `SimpleCalendarEventsOnDate` | 1.0 | 5 | `model_answer` |
| 3 | B3 | `ExpenseAddSingle` | 1.0 | 16 | `model_done` |
| 4 | M0 | `FilesMoveFile` | 1.0 | 27 | invalid after repair |
| 5-8 | - | - | - | - | not executed |

There were no infrastructure attempts or startup failures. The exact model,
revision and backend matched the freeze. Pairing, memory isolation, evaluator
leakage, readiness accounting, semantic-progress auditing and native-success
criteria all remained valid through the four completed cells.

## Sequence-4 causal trace

The Files trajectory selected the exact `nature_sounds.mp3`, chose
`sdk_gphone64_x86_64/Ringtones`, and executed one bottom MOVE commit. The
immediate UI remained visually stale, so the policy pressed Back once and
observed the Music source view. AndroidWorld later returned reward `1.0`,
proving the requested filesystem mutation had succeeded.

On step 16:

1. The initial model response proposed another swipe in Music.
2. `POST_DESTINATION_SOURCE_EXIT_GUARD` correctly rejected it and required
   exactly one `press_back`.
3. The bounded repair returned exactly `{"type":"press_back"}`.
4. Its 242-character `decision_summary` exceeded the schema maximum of 240.
5. Strict validation rejected the whole response before action execution.

This is not an action-safety failure and not a task-execution failure. It is a
serialization-boundary failure in which harmless explanatory verbosity
invalidated an otherwise contract-compliant repair.

## Bounded r55 direction

r55 may normalize only the two top-level, non-executable rationale strings
`decision_summary` and `expected_outcome`, only after the one model repair has
already been used, and only when a post-destination repair contract permits
the exact `{"type":"press_back"}` action. Each overlong string may be
deterministically shortened below the prompt limit, with before/after lengths
recorded in parse audit.

The normalization must not:

- run on an initial response;
- add a model call or a second repair;
- alter `status`, `action`, coordinates, text, provenance, citations,
  `state_delta`, or `completion_evidence`;
- rescue malformed JSON or non-string rationale fields; or
- bypass any repair contract, history-policy adjudication, semantic guard,
  schema rule unrelated to those two lengths, or Gate-E acceptance criterion.

The r54 directory is immutable and must not be resumed. Any r55 live action
requires complete deterministic validation and a fresh development namespace.

## Evidence boundary

This is an incomplete non-Hard protocol requalification. The 4/4 native
successes are valid task-execution evidence, but the stopped suite is not a
passed Gate E, a complete paired B3/M0 comparison, or Hard benchmark evidence.
