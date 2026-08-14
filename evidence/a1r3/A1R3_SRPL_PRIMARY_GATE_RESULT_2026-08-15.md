# A1-R3 SRPL primary gate result

Date: 2026-08-15 (Asia/Hong_Kong)

Verdict: **FORMAL_GATE_TERMINAL — do not rerun or continue this arm.**

## Scored result

The first frozen capability task, `ExpenseDeleteMultiple2` at task seed
`20260806`, completed as a scientifically valid failure:

- reward `0.0`, full success `false`;
- termination `max_steps`;
- 34 model calls and 34 executed actions;
- 128,383 prompt tokens, 4,392 completion tokens, 132,775 total tokens;
- 837.221526 seconds valid episode elapsed time;
- maximum transport attempts per call `1`;
- zero lifecycle errors and no episode error.

The suite checkpoint is `stopped_capability_gate_failure`. The preregistered
six-task gate therefore terminates A1-R3 at 0/1; no later task may run and the
valid failure may not be retried.

## What the result does and does not test

The inherited A1 writer contract did not activate in this episode. All 34
executed responses were invalid `MEMORY[...]` prefixes. Consequently A1-R3 had
zero valid writes, zero non-empty reads, zero injected characters, zero stale
state suppressions, and zero repeated-failure facts. It added no model calls,
guard, action override, or forced termination.

Thus the prospective **system arm** regressed on a task solved by A0, A1, and
A1-R2 and must be rejected. However, this trace cannot attribute the regression
to A1-R3's new stale-resistant lifecycle or negative failed-attempt memory,
because neither mechanism executed. The precise diagnostic lesson is that the
model-authored memory writer remains a fragile dependency even when offline
replay shows historical exposure. Offline replay feasibility did not guarantee
prospective writer compliance.

## Evidence binding and shutdown

- implementation commit:
  `4bbac3214c69d921912219f59f027424c921ec8e`
- suite: `official_qwen_20260815T015804_ea09c9a4`
- episode: `ExpenseDeleteMultiple2_20260806_33274904`
- episode JSON SHA-256:
  `97321270492a16471d59bfe401500e26ca9cbdfa20499b5f49c340f2ce7d78bb`
- checkpoint SHA-256:
  `fd9b8c281bd3e790d7e90b4b0dca6bd511adb10a930f4ca604f7eeef965868ca`
- run-signature SHA-256:
  `58d710487e18b679d5dd1ff308d671d6470cd69835f90731b677a6e56df7c95d`

After the terminal verdict, the SSH tunnel and vLLM PID 1718 were stopped.
GPU memory returned to 0 MiB used by the experiment process.

