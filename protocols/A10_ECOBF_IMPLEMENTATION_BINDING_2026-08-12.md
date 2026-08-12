# A10 ECOBF implementation binding — 2026-08-12

This file records the implementation boundary of
`GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md`. It does not amend the
mechanism, thresholds, experiment order, or success criteria.

## Frozen identity

- Mechanism: `a10_evidence_calibrated_obligation_branch_frontier_v1`
- Experiment: `A10_ECOBF_QWEN3VL32B_AW_HARD_S20260806_V1`
- Parent evidence commit: `ee6df0d11e8e45a903ec291e5a2dbe7fbacb60aa`
- Task seed: `20260806`
- Generation seed: `3407`
- Model calls added: `0`
- Guard/action override/forced termination: `0/0/0`

## Coding boundary

The implementation follows the Pro document's stated trigger and retrieval
conditions without adding trace-specific exceptions.  A physical RGB frame
that appears once as an action destination and again as the next action source
is one visit at that executed step.  Route evidence is attached to the original
receipt's frontier, branch, phase, open mask, confidence baseline, and touched
anchors.  Late return revises, rather than double-counts, an earlier durable
departure.  Exact and threshold-qualified near visual matches are both legal.

The implementation deliberately does not weaken T2 merely to satisfy a frozen
replay.  If a successful historical trajectory contains a qualifying no-gain
closed route, the mechanism creates and may retrieve T2 exactly as specified;
the offline silence gate must then fail visibly.

## Pre-generation gates

- All A10 and adjacent official-controller tests pass.
- The materialized 27-episode real-RGB replay report passes every frozen gate.
- The independent A10 source freeze and tokenizer budget must pass.
- A fresh A10 live-server receipt is mandatory; no A678/A89 receipt is reused.
- Formal execution is the four A0-success tasks in frozen order, fail-fast
  4/4, followed by the remaining 15 tasks without rerunning the gate tasks.

No live generation is authorized by this document alone.

## Current qualification state

The committed replay report is authoritative; the earlier hand-written A0-only
summary is not a qualification artifact.  At the current implementation the
formal replay is expected to fail if the Pro trigger rules and the Pro silence
gate conflict.  A failed replay blocks live generation and must not be relabeled
as an infrastructure success.
