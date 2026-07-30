# Protocol-v2.2 Gate-E r48 stopped report

Date: 2026-07-31  
Frozen source: `90916a46f678af38f3632d3d229e04bb5f23200d`  
Tag: `protocol-v2-2-gate-e-r48`  
Decision: **STOPPED at 4/8; Gate E did not pass**

## Bottom line

The formal r48 Gate-E run produced four valid AndroidWorld native successes,
then correctly stopped on the frozen `valid_output` rule. Sequence 4
(`M0 / FilesMoveFile`) moved the requested file successfully and received
native reward 1.0, but its final verification-navigation decision was invalid
after the single bounded repair. Sequences 5-8 were not executed.

This is a protocol/controller qualification failure, not a task failure and
not a B3-versus-M0 comparison. The four successes cannot be presented as a
complete paired result.

## Formal results

| Seq. | Variant | Task | Native | Executed steps | Calls | Termination |
|---:|---|---|---:|---:|---:|---|
| 1 | B3 | `ContactsAddContact` | 1 | 10 | 16 | model done |
| 2 | M0 | `SimpleCalendarEventsOnDate` | 1 | 3 | 5 | model answer |
| 3 | B3 | `ExpenseAddSingle` | 1 | 11 | 16 | model done |
| 4 | M0 | `FilesMoveFile` | 1 | 16 | 26 | invalid after repair |
| 5 | M0 | `ContactsAddContact` | — | — | — | not executed |
| 6 | B3 | `SimpleCalendarEventsOnDate` | — | — | — | not executed |
| 7 | M0 | `ExpenseAddSingle` | — | — | — | not executed |
| 8 | B3 | `FilesMoveFile` | — | — | — | not executed |

Startup was clean on the first environment-construction attempt. There were
no infrastructure attempts, evaluator-prompt leaks, memory-isolation errors,
executed blocked actions, unresolved semantic-guard repairs, visible
failures, or model-identity mismatches.

## Sequence-4 causal trace

The task required moving `nature_sounds.mp3` from Music to Ringtones. M0:

1. opened the device storage and Music;
2. searched for the exact filename;
3. selected the exact file and chose `Move to...`;
4. navigated the destination picker to Ringtones;
5. executed the bottom `MOVE` commit exactly once;
6. navigated back to the storage root to verify the destination.

At step 16, the screen visibly showed the `Ringtones` folder and the model
proposed tapping it. The action was reversible navigation and was precisely
the next action needed to expose the destination contents.

The generic consequential-action heuristic nevertheless triggered because
the decision summary used the word `confirm`. The same-turn critic returned
`reobserve` with the constraint “confirm the Ringtones folder is selected and
its contents are visible.” That condition cannot become visible without
opening the folder. The bounded repair returned the same correct Ringtones
tap, after which the binding critic constraint rejected the exact repetition.

No second transfer, selection, long press, Move/Copy command, or other
mutation executed. AndroidWorld independently verified the completed move and
returned reward 1.0. The runner still stopped correctly because the episode
had `valid_after_one_repair=false`.

## Acceptance impact

At the stop point, total success, B3 success, M0 success, IR correctness,
semantic-progress auditing, memory isolation, and native task execution were
all satisfactory. Gate E nevertheless failed because:

- only 4 of 8 formal cells were validly completed;
- the full two-cell IR cache requirement was incomplete; and
- valid output after at most one repair was not 100%.

Therefore `gate_passed=false`,
`stopped_early=true`,
`stop_reason=model_output_invalid_after_one_bounded_repair`, and automatic
Gate-F transition remains disabled.

## Immutable evidence hashes

- `suite_summary.json`:
  `371130c65c33d79edb4dc793d5c11080a41796c6eadf024c310d8243736f75b5`;
- `manifest.snapshot.json`:
  `a0c172e30c52613a3c6fbd1dfddeed3442234eada327941976c745f52c9b0ce8`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- `startup_environment_audit.json`:
  `d9957cb1e7ec8bcad4109b07853b670293c1fec9e974f242938e00b6142891f1`;
- sequence-4 `episode.json`:
  `b8ff9c9f64a95173e6d7fc1c0faba385adffed0b1891ca0646728d491e4599b1`;
- sequence-4 events:
  `aae29d747bfbc26bbfe7fe9f8dc8f03fc928ce0548fcc6c10b146d1f1a3000c4`;
- step-16 current screen:
  `3e7501be3bb452494fb169193fdc25d6320813c7f7b4057fc37d1fa317344220`.

## Next bounded change

A justified r49 must not relax the post-transfer mutation guard or globally
disable action criticism. It may classify a tap as verification navigation
without same-turn commit adjudication only when all of the following are
deterministically true:

- one destination Copy/Move commit has already executed;
- the current app is Android Files and no destination picker is active;
- the action is a tap on a visible, enabled, non-editable application control;
- accessibility at the tap contains the exact task-parameter destination
  folder label;
- the action is not a Move/Copy command or any commit-like control; and
- the exemption and matched destination label are audit-recorded.

Negative tests must retain adjudication for the bottom Move/Copy commit,
wrong folders, unnamed coordinates, non-Files controls, and all
pre-transfer taps. Only one isolated, non-scored M0 Files smoke may follow
local validation. r48 itself is immutable and cannot be resumed.
