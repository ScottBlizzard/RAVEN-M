# Protocol-v2.2 r60 Gate-F Batch-1 stop report

Date: 2026-07-31  
Decision: **formal Gate F stopped/failed at 2/12; Batch 1 stopped at 2/4**

## Frozen outcome

The r60 formal runner produced two valid scored cells and stopped at the first
preregistered method failure:

1. H01 `BrowserMultiply`, B3: native reward 1.0, success;
2. H17 `SportsTrackerActivitiesOnDate`, M0: native reward 0.0,
   `MODEL_OUTPUT_INVALID_AFTER_REPAIR`.

H03, H16, Batch 2, and Batch 3 were never run. The checkpoint reports one
success, one failure, 1,408.735 cumulative active seconds, and a projected
9,317.170 seconds for all twelve cells, below the 12,600-second cap. Time was
not the stop cause.

The checkpoint, progress file, and summary are byte-identical with SHA-256
`f39cf0e02268d67329a37276edbb21aecae0bcabafa2446edd353b2b3ed2002b`.
The r60 formal namespace is now immutable and cannot be resumed, overwritten,
or used to start Batch 2.

## Infrastructure accounting

Initial AndroidWorld construction hit one ADB install timeout. The audited
cold-recovery path succeeded before any scored cell began. Both scored cells
used their first attempt, both post-episode reset audits passed, and no cell was
classified as an infrastructure attempt. The model remained healthy and the
emulator remained connected after the stop.

The later logcat teardown warning does not change the result: H17 had already
produced a complete episode, native reward, reset audit, and deterministic
protocol stop. The H17 failure is a valid method failure, not a post-hoc
infrastructure exclusion.

## H17 causal trace

The target was an older date in OpenTracks' reverse-chronological activity
list. The agent never scrolled to September 24 and never emitted a terminal
answer. Instead, it alternated between the activity list and the empty
`Markers` page.

Two UI transitions completed later than the corresponding post-action audit:

- Step 9 tapped `Search`. The immediate semantic snapshot remained
  `06de312ae857...`, but the next step began at `f19d911aa418...` with a
  focused Search field and keyboard.
- Step 10 tapped the Markers icon from that Search UI. The immediate semantic
  snapshot remained `f19d911aa418...`, but the next step began at
  `94f944ba80e4...` on the empty Markers page.

Their immediate pixel-change ratios were 0.0050 and 0.0091, both below the
current 0.01 material-change threshold. Readiness therefore accepted each
screen after one observation, before accessibility reflected the completed
transition.

This timing error had a direct memory effect. After step 9, the system wrote a
critic conclusion that Search had not changed the UI and recommended tapping
the location-pin icon. At step 10, the Search field was visibly ready for
input, but that stale critic constraint was still routed, and the model
followed it into Markers.

At step 11, `press_back` was the model's first action and its bounded repair.
Both responses were byte-identical and both were rejected by the frozen loop
guard because that state/action fingerprint belonged to the prior alternating
loop. No action executed, the semantic audit recorded an unresolved repair,
and the formal stop policy fired correctly.

## Interpretation

The loop guard should not be loosened to accept this trajectory. It correctly
prevented another unproductive alternation. The upstream defect is that a
late semantic transition was recorded as no progress, allowed a false critic
constraint to persist onto a materially different screen, and thereby routed
the policy away from the available next action.

Historical same-seed protocol-v2 evidence independently shows that older
entries can be reached by scrolling the chronological list, although that old
trajectory later returned the wrong activity type. The frozen task parameters
identify `swimming` as the evaluator category; this is offline causal evidence
only and was not visible to the agent.

## Bounded next scope

A new candidate may reconcile a semantic change that appears between an
action's immediate after-observation and the next decision observation. Such a
reconciliation must correct the recorded previous outcome and expire critic
constraints that were created solely from the now-contradicted no-progress
claim. It must not reveal evaluator data, special-case the answer, or bypass
the loop guard.

Before any new formal run, this requires replay-shaped unit tests, full local
regression, the protocol-v1 seal, a fresh source tag and namespace, a zero-call
preflight, and one isolated non-scored H17 M0 smoke.
