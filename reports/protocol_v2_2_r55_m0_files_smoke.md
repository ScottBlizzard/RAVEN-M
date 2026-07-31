# Protocol-v2.2 r55 M0 Files smoke

Status: **valid development failure; Gate D withheld; bounded r56 local work
allowed**

Candidate:
`protocol-v2-2-r55-local-candidate` /
`66370821e2fd7577d8c7a508f80297ae1a4b1513`

Suite:
`nonhard_capability_v2_2_seed20260729_r55_candidate_development_smoke_sequence_4`

## Result

The one authorized, isolated, non-scored M0 `FilesMoveFile` smoke was a valid
task failure. It had one clean attempt, no infrastructure attempt, native
reward 0.0, 11 executed actions, 12 decision attempts, and 21 model calls.
The runner stopped at step 11 with
`MODEL_OUTPUT_INVALID_AFTER_REPAIR`.

This does not exercise the new r55 rationale-normalization path: the episode
never reached a destination commit or post-destination Back contract. The
live result therefore neither confirms nor contradicts the exact r54 replay
already covered by deterministic r55 tests. r55 must not be rerun.

## Exact failure

The agent opened Files, entered the emulated storage and `Music`, opened
Search, and typed the exact task literal `nature_sounds.mp3`. Search returned
several grid tiles whose visible labels were clipped. Accessibility contained
the exact filename, but the model repeatedly aimed at the nearby
`nature_sounds_2023_02_11.mp3`.

At step 11 the initial long press at `(0.30, 0.35)` was rejected by
`EXACT_TARGET_GUARD` before execution. The repair instruction allowed a
non-selection information-gathering action such as Search, a view-mode
change, or scrolling. The model tapped the Search control again. Because
that toggle was already part of a no-progress A-B cycle on the same semantic
state, `LOOP_GUARD` rejected the repair. Neither unsafe action executed.

The safety side is therefore correct: four wrong-neighbor long presses were
blocked, no file was selected, no MOVE commit occurred, and no second
mutation executed. The capability side remains incomplete because the
generic repair did not bind the model to the safer visible view-mode control.

## Reliability-aware memory observation

The history path contained the model-generated statement “The file
nature_sounds.mp3 is selected,” but routed it only as `HYPOTHESIS`, with no
promotion to verified fact. It was not used as native-success evidence. This
is useful live evidence for the project’s reliability framing: an intended
or claimed GUI state remains distinct from a screen-verified fact.

## Bounded r56 direction

r56 may specialize only this observed state: Android DocumentsUI, the exact
task-literal filename present in accessibility among multiple visually
ambiguous candidates, the proposed long-press coordinate bound to a neighbor,
and one visible enabled view-mode control.

In that state, the sole repair may be a pure tap on the
accessibility-grounded view-mode control followed by a fresh observation.
Search, text entry, scrolling, long press, selection, commit, and completion
remain forbidden within that repair. If the control cannot be identified
unambiguously, the controller must retain the present safe failure. Existing
exact-target, loop, provenance, memory, destination, and post-destination
guards stay unchanged.

The exact r55 trace and unsafe/no-control alternatives must first pass
deterministic tests, the full suite, and the protocol-v1 seal. No further live
model call is authorized by this report.

## Evidence hashes

- suite summary:
  `bd645c66b7130b47bc5438bfe65d6bd475095fbc780cc11a8ce85de2f84ae889`;
- manifest snapshot:
  `56a3f409762441a40330c8cdae761b2089d2f9d6b3023cdd8f3b42e3709a355a`;
- instances snapshot:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- startup audit:
  `680598dc5b9ae8ea1c71866f1823e7667aa885196ea204902092cf1baf7ba12d`;
- episode:
  `1d4f093411060045551de29426b3f4a44dc18fedc4933d37a6cf586ff0cf9667`;
- events:
  `9de551924ed8febf7c863469ce4b62063fa80c214339654929fd1853c0cb561f`;
- step-11 before screenshot:
  `97c81d7f0e7b8c89b59c1961f02f6222c0341ee3e41e7cef6eddd0a98a6c8f0a`.

## Model-service clarification

The smoke finished before a later controlled model-service restart. After
restart, health passed both remotely on port 8000 and locally through the
SSH forward on port 18000. The health field `concurrent_generations: 1` is
hard-coded server capacity, not a live request count; idle GPU utilization
confirmed that no request remained active.

## Decision boundary

This valid development failure withholds Gate D. It is not pooled with formal
evidence and authorizes neither formal Gate E nor Gate F. The r55 trajectory
is immutable; only bounded local r56 implementation and validation may
proceed.
