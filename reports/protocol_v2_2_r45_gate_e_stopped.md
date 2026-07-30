# Protocol-v2.2 Gate-E r45 stopped report

Date: 2026-07-30  
Frozen source: `3d0d719bfccac5934c62d3ab8be902a0ef66d7e9`  
Tag: `protocol-v2-2-gate-e-r45`  
Decision: **STOPPED; Gate E did not pass**

## Bottom line

The r45 Gate-E requalification did not complete. The first launch was
invalidated before any scored result because the emulator produced a Contacts
ANR and the MotionPro/VPN path then disconnected the local tunnel to the
remote model service. After connectivity was restored, the suite was restarted
under a clean evidence namespace. That restart produced five formal results:
the first four passed the native AndroidWorld evaluator, but sequence 5
(`M0 / ContactsAddContact`) failed the one-bounded-repair contract. The frozen
runner correctly stopped before sequences 6-8.

This is a protocol/controller qualification failure, not evidence about B3
versus M0 task quality. The four successes, the failed fifth cell, and the
three unexecuted cells must not be reported as a complete paired result.

## Attempt separation

| Attempt | Evidence namespace | Valid results | Disposition |
|---|---|---:|---|
| Original launch | `nonhard_capability_v2_2_seed20260729_r45` plus archive suffix `vpn_interrupted_20260730T184010` | 0 | infrastructure-invalid; excluded |
| Clean restart | `nonhard_capability_v2_2_seed20260729_r45_restart1` | 5 | stopped on formal protocol failure |

The original launch contains one Contacts ANR attempt and one model connection
failure after the VPN/tunnel dropped. Model health recovery polled for the
frozen 1,800-second bound and timed out. It produced no `suite_summary.json`
and no valid scored cell. The archive preserves 19 files. Two emulator-start
log handles remained in the original namespace because QEMU still owned them;
they contain no task result and are not evidence.

## Formal restart outcome

| Seq. | Variant | Task | Native | Steps | Calls | Termination |
|---:|---|---|---:|---:|---:|---|
| 1 | B3 | `ContactsAddContact` | 1 | 9 | 16 | model done |
| 2 | M0 | `SimpleCalendarEventsOnDate` | 1 | 3 | 5 | model answer |
| 3 | B3 | `ExpenseAddSingle` | 1 | 11 | 15 | model done |
| 4 | M0 | `FilesMoveFile` | 1 | 20 | 31 | max steps |
| 5 | M0 | `ContactsAddContact` | 0 | 6 | 11 | invalid after repair |
| 6 | B3 | `SimpleCalendarEventsOnDate` | — | — | — | not executed |
| 7 | M0 | `ExpenseAddSingle` | — | — | — | not executed |
| 8 | B3 | `FilesMoveFile` | — | — | — | not executed |

Sequence 1 first encountered a visible Contacts ANR. The runner archived that
attempt as `INFRA_EMULATOR_ANR`, cold-recovered the emulator, passed its smoke
check, and then produced the valid native success shown above. It is one
accounted infrastructure attempt, not a scored model failure.

## Sequence-5 causal trace

The task asked only for `Sofija Martin` and `+17634322348`. After entering the
first and last names, M0 refreshed its plan and introduced an unsupported
`company_name` requirement. On the post-keyboard screen:

1. the initial executor response proposed typing invented `TechCorp` into
   Company while declaring `text_origin=task_literal`;
2. `DECLARED_TEXT_SOURCE_GUARD` correctly rejected the value because it does
   not occur in the task;
3. the sole bounded repair changed to the correct phone number, but proposed
   coordinate-bearing `type_text` with `clear_text=true` while the Phone input
   was not active;
4. `UNFOCUSED_CLEAR_TEXT_GUARD` correctly rejected the unsafe Ctrl+A race;
5. with the one-repair budget exhausted, the episode ended as
   `MODEL_OUTPUT_INVALID_AFTER_REPAIR`.

No invalid action executed. The failure exposes a gap between two individually
correct safeguards: the declared-source repair tells the model to use a
remaining task value immediately, but does not require a separate activation
step when that value belongs to a different, unfocused field. The planner
prompt also says to preserve task requirements but does not explicitly forbid
inventing optional variables.

## Acceptance impact

The restart reached four native successes, including both variants, and one
correct cache-matched information-retrieval answer. However, it fails the
frozen requirements for eight valid paired cells, 100% valid output after at
most one repair, semantic-progress audit, unresolved-repair count, loop guard,
task/action compatibility, and visible-failure enforcement. Therefore:

- `gate_passed=false`;
- `stopped_early=true`;
- `stop_reason=model_output_invalid_after_one_bounded_repair`;
- automatic Gate-F transition remains disabled.

## Immutable top-level hashes

- restart `suite_summary.json`:
  `d74f3b4c5a346d79db81250298ab907bc39e53873bf7f877e7cadb4c1cd5ab38`;
- restart `manifest.snapshot.json`:
  `7fcefbea9718c159a303743a2559fb1324e441ab819949ba7ce6afebb7979c0c`;
- restart `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- failed sequence-5 `episode.json`:
  `4ad9fd65d8c539b52ae014c54f9f11739afb13c83d256112a001090e74b974df`.

## Next bounded change

Any retry requires a new frozen version. The justified r46 scope is:

1. require Planner variables and subgoals to be grounded only in explicit task
   requirements or currently verified UI state, never an unspecified optional
   field or placeholder value;
2. when declared-source repair must switch to a different visible input,
   require a reversible activation tap first and defer text entry until the
   next observed policy step;
3. validate this with deterministic tests, historical compatibility checks,
   and one isolated M0 Contacts live smoke before authorizing another Gate E.

No change to the r45 artifact is permitted, and no method-superiority claim is
supported.
