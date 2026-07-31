# Protocol-v2.2 r56 M0 Files smoke

Status: **native task PASS; exact r56 source eligible for Gate-D preparation**

Candidate:
`protocol-v2-2-r56-local-candidate` /
`24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`

Suite:
`nonhard_capability_v2_2_seed20260729_r56_candidate_development_smoke_sequence_4`

## Result

The one authorized, isolated, non-scored M0 `FilesMoveFile` smoke moved
`nature_sounds.mp3` from `Music` to `Ringtones`. AndroidWorld returned native
reward 1.0 and `success=true`.

The clean single attempt executed 20 actions with 34 model calls: 26 executor
calls and 8 history-role calls. All 20 decisions were valid within the one
allowed repair, 14 on the first pass. Semantic-progress audit passed with no
executed blocked action, no visible failure, no unresolved repair, and no
semantic no-progress repetition. There was no infrastructure attempt.

The invocation took 753.172 seconds; the episode itself took 730.705 seconds.
It ended at `max_steps`, not `model_done`. As in the earlier successful r53
smoke, native evaluator success is decisive; the final extra navigation is an
efficiency limitation, not contradictory task evidence.

## Task and safety chain

The agent entered `Music`, searched the exact task literal
`nature_sounds.mp3`, and long-pressed a coordinate that accessibility bound to
that exact full filename. It opened Move to, navigated through the destination
picker, entered the exact visible `Ringtones` row, and executed one bottom
MOVE at step 13. The consequential-action critic returned `proceed`.

After the commit, one attempted reselection and two attempts to remain or
scroll in the source folder were blocked. Each repair used reversible Back
navigation. No second file selection, Move to command, destination commit, or
other transfer mutation executed.

Step 18 tapped an exact, noneditable `Ringtones` content label in Android
DocumentsUI. The resulting screenshot visibly contains the destination and
the moved audio file. Its SHA-256 is
`cb65b020f12564eabdf2e865ec32827edf2f297872a842273f9208ee2d7a509e`;
native reward 1.0 is the authoritative result.

## r55 live qualification

The r55 normalization branch fired live at step 17. The initial action was an
invalid post-commit swipe while accessibility still identified `Music` as the
current source. `POST_DESTINATION_SOURCE_EXIT_GUARD` required exact
`{"type":"press_back"}`.

The model returned that exact action, but its `decision_summary` was 188
characters. r55 shortened only that non-executable string to 159 characters.
The protected payload SHA-256 remained
`94428b270c3fd58021e0a0fe4dc3b8335cc5072647213e7fe7e59b7647d2c607`
before and after normalization. The Back action then executed successfully.
This is the first live confirmation of the branch that r54 had reached but
could not execute.

## r56 branch evidence boundary

The specialized r56 view-mode repair did not trigger in this trajectory. Once
Search exposed the exact result, the model's first long press was already
correct, so there was no wrong-neighbor ambiguity to repair. This report does
not mislabel the successful exact selection as live view-toggle evidence.

r56 nevertheless has three complementary evidence layers:

- the exact r55 failure shape and unsafe alternatives pass deterministic
  controller tests;
- a zero-model-call probe on the real AVD found exactly one compatible
  `List view` control with the actual DocumentsUI resource identity; and
- the exact frozen r56 source completed the native Files task without
  weakening any preserved guard.

Another stochastic rerun merely to force the dormant branch is not authorized.
The branch remains available if formal execution naturally encounters the
qualified ambiguity.

## Reliability-aware memory observation

The model's selection statement remained a `HYPOTHESIS`, not verified fact.
Even after the moved file was visible in `Ringtones`, the history critic
remained conservative because it did not treat the earlier selection claim as
proof of the whole transfer. This caused extra reversible source/destination
navigation near the step limit.

That behavior is safe but inefficient. It is also useful research evidence:
reliability-aware memory prevents an intended GUI state from becoming fact,
while overly conservative evidence linkage can increase verification cost.
The native evaluator, rather than the memory claim, determined success.

## Evidence hashes

- suite summary:
  `dc8706fb4c069d25369a3addc194024e8975f69029221b3a4db734c8feab868c`;
- manifest snapshot:
  `9831808a0cc17792d4c47700202572a1d848439acfdc0b3ce59a526e9dcbca6c`;
- instances snapshot:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- startup audit:
  `9f32f700244ec3b528e1fb04f6d964ed1437373a2c20779c7e5a9e7b51077378`;
- episode:
  `542673be86a5f4e06732aa149af5f7dcc433b6812a136c487ac1e2a323906ec8`;
- events:
  `31dd260a149f119687c4ea50e2010b3c189dce64d02d93707b77288b3e107364`;
- r55 normalization before screenshot:
  `d14fe2604254d8c36152dea814319b4e7aa412345d80dcc6b2fd8bb8b69ef332`;
- destination screenshot:
  `cb65b020f12564eabdf2e865ec32827edf2f297872a842273f9208ee2d7a509e`.

## Decision boundary

This development smoke passes and permits preparation of a new Gate-D freeze
for the exact r56 source. It is not pooled with formal results and does not
itself authorize or launch Gate E. Formal Gate E and Gate F remain unstarted;
the r56 development trajectory is immutable and must not be rerun.
