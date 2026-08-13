# A1-R1 BPR v2 Primary Capability-Gate Result

Date: 2026-08-14 (Asia/Hong_Kong)

Status: **valid scientific failure; primary stopped at the first gate task.**

The prospective primary arm ran `ExpenseDeleteMultiple2` first, as frozen. The
episode completed without an infrastructure error, but AndroidWorld returned
`reward=0.0`. Because this is one of A0's four frozen successes, the 4/4
capability-preservation gate failed immediately. The remaining three gate
tasks, the Recipe sentinel, the other fourteen primary tasks, and the
empty-read arm were not run and must not be resumed under this experiment ID.

## Episode facts

- episode: `ExpenseDeleteMultiple2_20260806_12d76de8`
- result: 0.0 reward; model claimed success incorrectly
- cost: 15 model calls, 14 executed actions, 57,689 total tokens
- transport: exactly one attempt for every call
- errors: no episode error and no lifecycle error
- termination: `model_terminate_success`
- raw episode SHA-256:
  `1a6fb0ce32f39da52cf9d52f84b8fc0fa68f2d71ded411e1bef05d8cb95e6934`

The model deleted `Tuition Fees` and `Public Transit`, did not establish that
`Bike Repairs` had been deleted, and then terminated after inferring that its
absence from the current view implied completion.

## Memory interpretation

The mechanism was not silent: it accepted one receipt and made one 184-character
non-empty injection. Therefore this episode establishes mechanism activation.
It does **not**, by itself, establish that the memory injection caused the final
failure. A0 succeeded on the matched task and seed, so this is a paired system
regression, but causal assignment to the single read would require the frozen
counterfactual/ablation that is unavailable because the primary arm did not
complete.

## Decision

This arm is rejected for capability preservation. It is not eligible for a
19-task score, a cost-improvement claim, an empty-read mechanism verdict, or a
rerun of this scientific failure. Any changed prompt, parser, receipt policy,
or other repair must be a new version and restart from the first gate task.

Machine-readable result:
`A1R1_BPR_V2_PRIMARY_GATE_RESULT_2026-08-14.json`.
