# B2 Clean MobileUse diagnostic preregistration

## Status and purpose

This document freezes a five-task **development diagnostic**, not a held-out
efficacy result. The parent PF01 arm has already exposed the same seed and all
five task structures. B2 may qualify a clean controller for a later full arm;
it cannot establish generalization or overwrite PF01.

Arm id: `B2_CLEAN_MOBILEUSE_QWEN3VL32B_AW_HARD_DEV_S20260806_V1`.

## Question

Does MobileUse retain useful behavior after removing avoidable implementation
failure, reducing unconditional auxiliary inference, and requiring evidence for
terminal success, while leaving its free-text memory representation unchanged?

## Frozen changes

1. Three exhausted Operator parse attempts become an explicit
   `terminate(failure)` action. They never create an empty action record.
2. Historical empty actions remain in the audit log but are omitted inside the
   upstream trajectory detector so they cannot crash a later valid step.
3. Reflector generation occurs only on the first action, every fourth action,
   an unchanged screen, an app-package transition, or a typed value.
4. Progressor generation occurs only on the first action, every fourth action,
   an app-package transition, or a typed value that was not rejected.
   Otherwise, the previous free-text progress is carried forward unchanged.
5. `Uncertain` or malformed GlobalReflector outputs veto completion. At most two
   GlobalReflector checks are allowed, preventing an unbounded review loop.
6. Upstream OpenAI clients that are immediately replaced by the audited local
   transport are not constructed.
7. Planner, NoteTaker, retrieval, accessibility-tree input and privileged
   actions remain disabled. The memory form remains MobileUse free-text history
   plus free-text progress; no structured memory is introduced.

No task-specific UI rule, coordinate, answer, entity, field value or evaluator
state may be introduced.

## Frozen tasks and rationale

Order: `H12, H08, H05, H01, H14`.

- H12 tests whether the prior parser/detector crash becomes a valid episode.
- H08 tests retention of a prior full success.
- H05 tests retention of a prior cross-app partial success.
- H01 tests whether reduced free-text progress rewriting changes the observed
  answer drift; the task remains a development example.
- H14 tests cost control and terminal integrity on the longest selected trace.

Native AndroidWorld budgets are unchanged: 60, 20, 18, 22 and 50 decisions.

## Frozen model and environment

- Model: `Qwen/Qwen3-VL-32B-Instruct`.
- Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Generation: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5,
  repetition penalty 1.0, seed 3407.
- AndroidWorld commit: `3e50888527ef9f29b9157ecd537e408008bb1c85`.
- Native reset, evaluator and task-instance hashes remain authoritative.

## Expansion gate

All conditions must pass:

1. Five of five tasks are scientifically valid.
2. H08 remains a full success.
3. Total reward across the five tasks is at least 2.0.
4. False-success count is at most one.
5. Generated model requests divided by Operator decisions is at most 2.4.
6. Event hash-chain errors equal zero.
7. Implementation and infrastructure errors equal zero.

The efficiency threshold is a 24% reduction from the parent arm's 3.17
requests per Operator decision across its four valid comparable tasks. H12 is
excluded from that parent ratio because it had no valid decision denominator.

If any gate fails, do not launch the full B2 arm. Preserve the diagnostic and
either stop B2 or create a separately identified development revision. A failed
diagnostic may not be tuned and relabelled as held out.

If every gate passes, the same code and prompts may be frozen for a new full
19-task B2 arm on seed 20260807. No semantic modification is permitted between
the passed diagnostic and that freeze.

