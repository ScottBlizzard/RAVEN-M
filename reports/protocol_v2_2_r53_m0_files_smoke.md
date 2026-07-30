# Protocol-v2.2 r53 M0 Files smoke

Status: **native task PASS; r50-r53 Files chain live-qualified; eligible for Gate-D preparation**

Candidate:
`protocol-v2-2-r53-local-candidate` /
`f3d7c9d3c33e54245138fc56336027f533b67f17`

Suite:
`nonhard_capability_v2_2_seed20260729_r53_candidate_development_smoke_sequence_4`

## Result

The fresh, isolated, non-scored M0 `FilesMoveFile` smoke moved
`nature_sounds.mp3` from `Music` to `Ringtones`. AndroidWorld returned native
reward 1.0 and `success=true`. The valid attempt executed 20 actions with 33
model calls (25 executor and 8 history-role calls), and its semantic-progress
audit passed.

Exactly one bottom MOVE commit executed at step 15. No second transfer,
selection mutation, or executed blocked action followed it. Step 18 entered
the exact visible `Ringtones` content row; its after screenshot visibly shows
the `Ringtones` breadcrumb and the moved audio file. The native evaluator is
the decisive success evidence.

The episode ended at `max_steps`, not `model_done`. At step 19 the completion
critic rejected a completion claim because Android Files clipped the visible
filename, and the bounded repair pressed Back. This conservative rejection
does not change native task success, but it is retained as an efficiency and
terminal-evidence limitation.

## r53 and preserved branch evidence

All 20 valid-attempt steps persisted a before-decision readiness record. Each
accepted record used accessibility, matched the foreground Android package,
and was cross-modally fresh. Three additional after-action observations were
rejected because pixels had materially changed while the semantic hash was
still unchanged; each was followed by a fresh semantic tree.

The invocation's first attempt was later invalidated by an unrelated
10-second ADB text-input timeout. Before that fault, r53's new
before-decision rule fired live twice: at steps 2 and 9 it rejected a
materially changed screenshot paired with the prior semantic hash, then
accepted the refreshed tree before any model decision. This is diagnostic
branch evidence only; the entire attempt is quarantined under
`invalid_infrastructure_attempts` and is not used as task-success evidence.

The valid attempt also exercised the preserved Files safety chain:

- r50 source-exit guard: one live block and an exact `press_back` repair;
- r51 destination navigation: one permitted tap bound to the exact visible,
  enabled, noneditable `Ringtones` content label;
- r52 post-activation clear guard: one live block, followed by the exact
  task-bound text with no coordinates and `clear_text=false`;
- exact-target selection: one wrong-neighbor long press was blocked before
  execution, Search exposed the exact filename, and the later long press
  selected the target;
- one destination-picker commit, no post-commit mutation block, no visible
  failure, and no unresolved guard repair.

## Infrastructure accounting

Attempt 1 reached the search-input action, where AndroidWorld's
`adb shell input text nature_sounds.mp3` exceeded its fixed 10-second timeout.
The runner classified it as `INFRA_EMULATOR_LOST`, archived the complete
attempt, cold-restarted the emulator, ran the recovery smoke, and created a
fresh attempt 2. Attempt 2 completed successfully. The invocation therefore
contains one explicitly invalid infrastructure attempt and one valid native
success; no partial trajectory was resumed.

The complete invocation took 1933.172 seconds. The valid episode took 692.119
seconds, used 43 readiness observations with 3 retries, and had 15 first-pass
decisions plus 5 decisions valid after the one allowed repair.

## Evidence hashes

- `suite_summary.json`:
  `29ceaaa7b006844adac82d157f4658edaf1912a0a02fa8a8a679426890efd922`;
- `manifest.snapshot.json`:
  `72b68e01b62af347491d0ec88bf5900e65e9164f27be1a942a5ef652dd790981`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- `startup_environment_audit.json`:
  `f0c83eab9a8b1228e00a508f5c4f0080b145d2f88df0eb1049907bfce0b7598a`;
- valid episode:
  `2233c07312b3bfdc48f6f49698de53e6ef78c697cc6a47f04d8cb38eba931e67`;
- valid events:
  `1185db9f2ee56d3a86ec9f529a4ee6cab80c9983741511952d346cbde781b0dc`;
- step-18 destination screenshot:
  `cb65b020f12564eabdf2e865ec32827edf2f297872a842273f9208ee2d7a509e`;
- quarantined attempt-1 episode:
  `eac0823964ef7c64cdad5978109f76faf9efe6d68f912871a8a8a0ec6502e276`;
- cold-recovery command audit:
  `24e91961d4389f9b4acd4e2dad45a2ade3ab242b9a190e3233f31a2b173bce43`.

## Decision boundary

This development smoke passes and permits preparation of a new Gate-D freeze
for the exact r53 source. It is not pooled with a formal paired result and
does not itself authorize or launch Gate E. Formal Gate E and Gate F remain
unstarted; r52 and both r53 attempts are immutable.
