# Protocol-v2 Gate E capability result

Date: 2026-07-27  
Suite: `nonhard_capability_seed20260729_rerun5`  
Development source: `protocol-v2-dev-r4` at
`de5278b6fc78ca01d4b530ef1442e5060dccbf10`  
Experiment freeze: `protocol-v2-gate-e-rerun5-freeze`  
Decision: **PASS**  
Automatic Gate-F transition: **disabled; Gate F not started**

## Outcome

All eight preregistered non-Hard B3/M0 cells completed in 2,648.953 seconds
(44 minutes 8.953 seconds). Five cells passed the native AndroidWorld
evaluator. B3 contributed two successes and M0 contributed three. There were
no infrastructure retries.

| Seq. | Variant | Task | Native result | Failure code |
|---:|---|---|---|---|
| 1 | B3 | `ContactsAddContact` | pass | — |
| 2 | M0 | `SimpleCalendarEventsOnDate` | pass | — |
| 3 | B3 | `ExpenseAddSingle` | pass | — |
| 4 | M0 | `FilesMoveFile` | fail | `TASK_UNSUCCESSFUL_AT_BUDGET` |
| 5 | M0 | `ContactsAddContact` | pass | — |
| 6 | B3 | `SimpleCalendarEventsOnDate` | fail | `INCORRECT_ANSWER` |
| 7 | M0 | `ExpenseAddSingle` | pass | — |
| 8 | B3 | `FilesMoveFile` | fail | `PREMATURE_COMPLETION` |

The three failures are ordinary capability outcomes. Every cell remained
protocol-valid and is included in the final aggregate.

## Preregistered criteria

All criteria in the frozen Gate-E manifest passed:

- 8/8 valid scored cells;
- exact B3/M0 pairing over four non-Hard task families;
- zero task/action compatibility errors;
- two information-retrieval cache cells;
- at least one correct information-retrieval cell;
- 5 total successes, exceeding the minimum of 4;
- at least one B3 success and at least one M0 success;
- zero unhandled third identical no-effect actions;
- zero M0 completion deadlocks;
- 100% valid output after at most one bounded repair;
- zero evaluator-prompt leakage findings;
- zero cross-episode memory-isolation findings;
- exact frozen model revision and backend.

The M0 calendar cell produced an exact cache-matched answer and passed the
native evaluator. The B3 calendar cell also populated and matched its own
interaction cache but its answer was natively incorrect; this remains visible
as a capability error rather than being hidden by the cache audit.

## Development evidence retained

Five earlier runs remain immutable diagnostics:

- attempt 1 exposed incomplete canonical action forms;
- rerun 1 exposed a tunnel-watchdog false restart during long generation;
- rerun 2 exposed an incomplete M0 `state_delta` contract;
- rerun 3 exposed ordinary completion incorrectly using `answer`;
- rerun 4 exposed partial repair of multiple missing required fields.

Each semantic correction was generic, regression-tested, and followed by a
complete Gate-D requalification. Before rerun 5, two live 32B repair-contract
checks passed without executing GUI actions or accessing an evaluator.

## Integrity

- `suite_summary.json` SHA-256:
  `69dfdf29e84e8efeb3ad52e82a566205de733e414432ef1677340962b927a501`
- `manifest.snapshot.json` SHA-256:
  `f0e35c51d02974a0a5f5c0f3618d740bf84c799f877156b75bf1534d2c17238a`
- `instances.snapshot.json` SHA-256:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`

Gate E establishes protocol and non-Hard capability readiness. It is not a
Hard-suite result and not a paper-level empirical claim. Gate F remains a
separate, explicitly authorized stage.
