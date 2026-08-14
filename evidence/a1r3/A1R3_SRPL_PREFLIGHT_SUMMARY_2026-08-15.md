# A1-R3 SRPL zero-generation qualification

Date: 2026-08-15 (Asia/Hong_Kong)

Status: **PASS — live generation may begin only after a fresh server receipt.**

## Frozen identity

- implementation commit: `4bbac3214c69d921912219f59f027424c921ec8e`
- mechanism: `a1r3_stale_resistant_pending_v1`
- experiment: `A1R3_SRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- source-freeze content SHA-256:
  `dbc7d08a080fea5f77cd68c83dce2612fe12c0081d06143bdf4bd9bb081ce4f8`
- preflight content SHA-256:
  `ec9e7ba122e58a879f708e5eecaaad9be6e654fca183f8dfffb85c8daa2d69f2`

## What was qualified

The full official mobile-agent test directory passed, along with Python
compilation, source-drift checks, forbidden-import inspection, a deterministic
runtime canary, and a real zero-generation replay of all 19 valid A1-R2
episodes. The runtime canary measured 0.1356 ms at P99 and 0.2603 ms maximum,
below the frozen 2 ms and 10 ms limits. No model generation was called.

The replay is bound to 603 historical model calls and 595 executed actions. It
projects 282 A1-R3 non-empty reads and 75,609 rendered characters, 69.7352% of
A1-R2's 108,423. Identical-state writes fail to refresh memory 130 times.
Eleven bounded failed-attempt facts are created and are actually read 34 times
across six failed episodes. All six A1-R2 success sentinels retain memory
exposure and create zero failed-attempt facts.

These are feasibility and intervention-opportunity results, not a predicted
reward improvement.

## Live stopping rule

A fresh A1-R3-qualified vLLM process must run the six fixed capability tasks
first. They must all receive reward 1.0. Any valid scientific failure stops the
arm permanently; only a trace-linked infrastructure-invalid attempt may be
replaced. The remaining thirteen tasks are released only after 6/6.

