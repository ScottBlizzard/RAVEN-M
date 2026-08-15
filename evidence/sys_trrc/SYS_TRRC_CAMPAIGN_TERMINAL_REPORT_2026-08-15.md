# SYS-TRRC terminal live report — 2026-08-15

## Bottom line

The prospective SYS-TRRC campaign stopped at invocation 4/12 because the
primary Full arm failed the first preservation task,
`ExpenseDeleteMultiple2` (reward `0`, 34/34 native actions). This is a valid
scientific gate failure, not an infrastructure failure. The same Full identity
must not be resumed or rerun.

SYS-TRRC is **not** a new memory arm. It is frozen A1-R2 memory plus an
episode-local deterministic detector and, in Generic/Full only, at most one
same-model auxiliary recovery call. No result from this campaign may be called
a pure-memory improvement.

## Frozen identity and validity

- Protocol: `SYS_TRRC_R2_ONE_SHOT_RECOVERY_PREREG_V1`
- Implementation commit: `e3394f0b0dc8ed0cab9fd15307ee7b9466412d03`
- Model revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Task seed / generation seed: `20260806` / `3407`
- Four mode-specific zero-generation preflights: `PASS`
- Four mode-specific live receipts: `PASS`
- Invalid infrastructure attempts: `0`
- Every recorded normal and auxiliary call used exactly one transport attempt.
- Claim boundary: matched exploratory diagnostic; not held out.

## Executed campaign prefix

| Ordinal | Arm | Task | Reward | Normal calls | Aux calls | Total tokens | Result |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Base | ExpenseDeleteMultiple2 | 0 | 34 | 0 | 144,793 | control stage sealed |
| 2 | Detector | ExpenseDeleteMultiple2 | 1 | 18 | 0 | 70,977 | control stage sealed |
| 3 | Generic | ExpenseDeleteMultiple2 | 1 | 19 | 0 | 74,959 | active control stage sealed; detector silent |
| 4 | Full | ExpenseDeleteMultiple2 | 0 | 34 | 1 | 147,814 | **terminal preservation-gate failure** |

The different Base/Detector/Generic outcomes on the same seed show that the
live mobile trajectory is not bitwise deterministic across independent model
processes. They do not establish a detector or generic-reasoning benefit,
because neither Detector nor Generic delivered an auxiliary intervention.

## What happened in Full

Full created one detector trigger and made one bounded auxiliary call before
normal request step 7. The response was semantically plausible but contained
blank lines between the three required fields. The frozen parser required
exactly three single-line fields, so it correctly failed closed:

- `trigger_count = 1`
- `aux_prepared_count = 1`
- `aux_committed_count = 1` (transport completed and was audited)
- `aux_output_invalid_count = 1`
- invalid reason: `aux_schema`
- `injection_committed_count = 0`
- auxiliary request SHA-256:
  `f036028a33b6250625531d220b577936e028cfa372bf572ea586e4c8505ef741`
- auxiliary response SHA-256:
  `5f8c63ee635b460ce38f61dc00c67bf3eb9ed0b8d43c94decaf9e8ae404278a1`

Therefore the terminal failure is **not evidence that injected specialized
recovery advice harmed the executor**: no advice was injected. It is evidence
that the frozen composite system failed its end-to-end preservation contract,
and that its strict auxiliary output interface had a real reliability failure.

## Scientific adjudication

- System accuracy verdict: `TERMINAL_FAIL`.
- Specialized-recovery causality: `NOT_ADJUDICATED`; there was no committed
  Full advice and no exact-prefix Full-vs-Generic intervention pair.
- Memory improvement claim: prohibited.
- The campaign must not proceed to L2, Browser activation, or the remaining
  tasks under this identity.
- A future version may redesign the auxiliary interface (for example, robust
  deterministic field parsing or constrained decoding), but that is a new
  prospective identity and must restart from invocation 1.

## Evidence map

- Campaign ledger:
  `SYS_TRRC_CAMPAIGN_LEDGER_TERMINAL_2026-08-15.json`
- Per-invocation formal results:
  `SYS_TRRC_LIVE_01_BASE_L1_RESULT.json` through
  `SYS_TRRC_LIVE_04_FULL_L1_RESULT.json`
- Full raw episode record (screens referenced by hashes; PNGs remain in the
  local run archive):
  `SYS_TRRC_FULL_L1_EXPENSE_EPISODE_2026-08-15.json`
- Full episode JSON SHA-256:
  `d92971a1162e723045781f364ac826a35a58e637c5a3b05858307492e39c0922`
- Formal result file SHA-256 values, in invocation order:
  - Base: `d0d3fbabda25f346c3ffcdd873bfc02694edae7762c1a80e3c616acd669b9f2e`
  - Detector: `8b51790fd883333f7cdf1caca10de74232e5857e99c8f9efcca985f3a486e2fa`
  - Generic: `32a5b34ca2aadbcdf58dbeffb87682d791d717d5fe5040cc38af90c1b0de0d2d`
  - Full: `71fa77182388bf1453da0e4cf56b0e24abe6279dd1318b537ea735f942a9d7f9`

