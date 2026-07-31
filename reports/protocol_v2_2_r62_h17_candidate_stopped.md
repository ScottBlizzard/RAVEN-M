# Protocol v2.2 r62 H17 Candidate Stop Audit

## Decision

**The r62 navigation mechanism passed live, but the terminal answer was
incorrect.** The non-scored development cell is stopped and immutable. It
does not authorize formal Gate F or a retry of the same candidate.

Attempt 1 lost Android accessibility during reset and was archived as
`INFRA_EMULATOR_LOST`; the bounded cold recovery succeeded. Attempt 2 is the
valid method result: native reward 0, five executed actions, nine model calls,
199.9 seconds, `INCORRECT_ANSWER`, and a passing post-episode reset.

## What r62 fixed

The executor opened the chronological history and used three direct upward
content swipes. It never tapped `Markers`, never opened text Search, and never
typed the date. The deterministic chronology assessment changed from an
older-scroll requirement at `7 Oct`, to the same requirement at `2 Oct`, to
target-visible at `24 Sep`. Thus the target date was reached without the r61
detour.

The toolbar validation block count is zero because the model followed the new
prompt on its first proposal; this is not evidence that the mechanism was
inactive. The first-pass trace itself changed from the r61 map-pin tap to the
intended list swipe.

## Why the answer failed

On the final screenshot, `Skill work` and `Recovery day` are the two rows dated
`24 Sep`; `Bicycle Adventure` is visibly dated `2 Oct`. The task asks for
activity **types**, but the model answered the visible activity **names**
`Bicycle Adventure, Recovery day`. Therefore one item was bound to the wrong
date, and both items were bound to the wrong semantic field.

Both same-turn visual-source and completion critics returned `proceed` because
they verified that the strings were visible, not that each string belonged to
a target-date row and represented the requested field. The native evaluator
correctly rejected the answer.

For causal audit only, the frozen instance reconstructs the two target rows as
`Recovery day → inline skating` and `Skill work → cycling`. The sampled
`swimming` parameter is deliberately excluded by AndroidWorld's
without-replacement fixture and is not the answer. None of these hidden values
were visible to the agent or used to generate an action.

## Safe next scope

A new candidate may add a generic terminal-answer association rule: for a
dated list query, every answer item must be bound to a row carrying the target
date, and its visible semantic field must match what the task requests. If the
list exposes only a row title/name while the task asks for a type, category,
duration, or another field, the policy must open the target row and obtain
explicit field evidence before answering. Once the target date is visible it
must not continue blind scrolling.

This mechanism must not mention H17, OpenTracks, the target date, target row
names, expected categories, or any hidden task parameter. It requires local
positive and negative replay tests, full regression, a new source tag and
namespace, and another zero-call preflight before any later live request.

Machine-readable evidence:
`reports/protocol_v2_2_r62_h17_candidate_stopped.json`.
