# Qwen Mobile Memory Study: A0 → A1 → A2

## Current research handoff

The current project state is in `HANDOFF_2026-08-13.md`. The next design request,
`GPT_PRO_A1_VERTICAL_REFINEMENT_DESIGN_REQUEST_2026-08-13.md`, moves from broad
horizontal comparison to a minimal vertical refinement of A1. The A10-v2/A11/
A12 enriched six-task study remains explicitly post-hoc and does not repair any
failed formal arm.

In parallel, `GPT_PRO_COMPOSITE_TRACKS_INDEX_2026-08-13.md` defines seven
independent Pro design studies beyond pure memory. Their common evidence ledger
is `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md`. They are
unreviewed design requests, not registered or authorized experiment arms.

The newest prospective vertical result is A1-R2 CVP: **6/19**, reward **6.5**,
with all five A1 successes preserved and `OsmAndMarker` added. Its accuracy
verdict passes, its strict cost verdict fails because calls equal rather than
undercut A1, and causal mechanism attribution remains unestablished without a
matched ablation. See
`evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md`.

The next prospective pure-memory arm is A1-R3 SRPL. It directly targets the
130 unchanged-state refreshes and repeated no-progress actions observed in
A1-R2, without adding a planner, verifier, model call, guard, or action
override. Its real-trace replay and zero-generation preflight pass at frozen
implementation commit `4bbac3214c69d921912219f59f027424c921ec8e`.
Live execution still requires a fresh server receipt and a blocking 6/6 gate.
See `evidence/a1r3/A1R3_SRPL_PREFLIGHT_SUMMARY_2026-08-15.md`.

Live execution then failed the first capability task: 0/1, reward 0, 34 calls,
with no infrastructure error. The A1 writer produced zero valid memory prefixes,
so A1-R3's new lifecycle never activated. The arm is formally terminal; this
is a system-level regression but not evidence that the inactive negative-memory
rule caused it. See
`evidence/a1r3/A1R3_SRPL_PRIMARY_GATE_RESULT_2026-08-15.md`.

This branch is the clean audit packet for a Zhejiang University summer-camp study of memory mechanisms in long-horizon AndroidWorld tasks. It replaces the earlier public-framework selection packet. Superseded MobileUse/B2/C0 explorations remain recoverable in Git history but are intentionally absent from this branch so that an independent reviewer can focus on the current paired experiment.

## Research progression

1. **A0 — official Qwen mobile baseline.** The public Qwen3-VL mobile-agent prompt and action protocol were ported to AndroidWorld with Qwen3-VL-32B. On the frozen first seed it achieved 4/19 full successes.
2. **A1 — simple Action Working Memory.** Six recent `observed / verified / pending` records were injected within each episode. It achieved 5/19 but increased steps from 329 to 603 and tokens from 1.27M to 3.46M.
3. **A2-v1r1 — scored verified-progress compound arm.** It completed the 19-task suite at 0/19, with 705 calls and 3,170,413 tokens. It is retained as a negative comparison rather than an improvement over A0 or A1.
4. **A1-R2 compact vertical refinement.** It retained one latest verified/pending ledger, deduplicated the memory prefix from ordinary history, and scored 6/19 with 603 calls and 2.686M tokens. This is the first matched accuracy improvement beyond A1 in the vertical line, but not yet a causal mechanism result.
5. **A1-R3 stale-resistant pending ledger.** It preserves A1-R2's positive
   kernel, prevents unchanged-state TTL renewal, and remembers one repeated
   visible failed attempt. It is preflight-qualified but has no live reward
   result yet.

The A2 guard is not claimed as memory intelligence. It only limits obvious repeated-action waste. All memory reads/writes and guard assessments/blocks/stops are recorded separately so the final trace analysis can attribute changes.

Exact A1 result/code is frozen at commit `fbc25dc`. The current branch changes shared files for A2, so it intentionally refuses to masquerade a new A1 run as the old frozen arm.

## Audit order

An external reviewer should read:

1. [`GPT_PRO_A2_AUDIT_REQUEST.md`](GPT_PRO_A2_AUDIT_REQUEST.md)
2. [`assessment/夏令营考核题目_提取文本.txt`](assessment/夏令营考核题目_提取文本.txt)
3. [`evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md`](evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md)
4. [`evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md`](evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md)
5. [`evidence/a2/A2_DESIGN_RATIONALE_AND_A1_REPLAY_2026-08-10.md`](evidence/a2/A2_DESIGN_RATIONALE_AND_A1_REPLAY_2026-08-10.md)
6. [`protocols/A2_VERIFIED_PROGRESS_MEMORY_PREREG_2026-08-10.md`](protocols/A2_VERIFIED_PROGRESS_MEMORY_PREREG_2026-08-10.md)
7. [`implementation/src/raven_m/official_qwen_mobile/progress_memory.py`](implementation/src/raven_m/official_qwen_mobile/progress_memory.py)
8. [`evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json`](evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json)

The full file map is in [`ARTIFACT_MANIFEST.md`](ARTIFACT_MANIFEST.md).

## Frozen comparison

- Model: `Qwen/Qwen3-VL-32B-Instruct`
- Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Backend: BF16 vLLM on one RTX PRO 6000
- Benchmark: the same 19 AndroidWorld Hard task instances
- Task seed: `20260806`
- Generation seed: `3407`
- Observation: current screenshot only
- Final label: AndroidWorld evaluator, hidden from the agent
- A2 extra model calls: `0`

## A2 claim boundary

A2 may claim an accuracy improvement only if it exceeds A1's 5/19 full successes. It may claim a cost improvement only if total tokens and wall time are both below A1. One seed remains a paired diagnostic, not proof of generalization. A guard-only saving is cost control, never evidence that memory improved reasoning.

## Raw evidence boundary

Full step-level run trees contain screenshots, UI audit records, model requests/responses, actions, transitions, memory events, and evaluator outputs. They remain local because of size. This repository provides frozen aggregate evidence, task manifests, executable mechanisms, tests, preregistrations, and zero-generation qualification reports. Claims requiring absent raw artifacts must be listed as information gaps.
