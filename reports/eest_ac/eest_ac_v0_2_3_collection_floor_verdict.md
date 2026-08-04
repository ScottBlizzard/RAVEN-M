# EEST-AC v0.2.3 Outcome Oracle Trace Qualification — Collection-Floor Verdict

## Outcome

**Overall verdict: `FAIL_COLLECTION / measurement-infrastructure floor`.**

The action-conditioned oracle candidate produced useful offline mechanism signals, but the preregistered development collection qualification did not produce a valid `collection_complete.json`. The separately supervised, fully logged rerun also failed before completion. Per the frozen stopping rule, no held-out matrix was selected or collected, the oracle was never evaluated on held-out input, and this phase is **not eligible for a separately preregistered live oracle qualification**.

This verdict does not change the permanent v0.2.2 `FAIL` verdict and supports no M-SLOTS, M-RISK, memory, task-success, or efficacy claim.

## Frozen question and authority boundary

The preregistered question was whether a task-agnostic oracle could allocate outcome authority by action class instead of demanding exact terminal pixel equality. The offline candidate has separate `scroll`, `open_app`, and `navigation_press` policies; pixels are auxiliary and cannot authorize acceptance. Missing critical evidence fails closed as `uncertain`, while contradictory or stable no-effect evidence is rejected.

The machine contract, generated input schema, parser/oracle implementation, trace harness, and property tests are preserved as **offline, unqualified candidate artifacts**. Their presence and unit-test success cannot substitute for the required frozen held-out trace matrix.

## Development replay (contaminated, non-scoring)

The frozen DEV replay contains nine prior v0.2.2 live/measurement traces. Every row declares `development_contaminated=true` and `held_out_eligible=false`. It produced five accepts, three rejects, and one uncertain result, and passed the preregistered directional sanity checks: the prior BACK trace is explained as a semantic transition; the dynamic Camera control is rejected; and the missing-a11y control is uncertain.

This is implementation-direction evidence only. It contributes zero rows to PASS and cannot reclassify any v0.2.2 result.

- DEV replay: `reports/eest_ac/eest_ac_v0_2_3_dev_replay.json`
- DEV replay SHA-256: `01b0b632c71e9e712a1fa8e32515dcfab76246e513c2800d67599e7e39aa9a7a`
- Held-out eligible rows: `0`

## Collection qualification and hard stop

The first Chrome-based development harness attempt was already development-contaminated and failed because Chrome remained in first-run setup. It was abandoned without held-out use.

A Settings scroll scene already contaminated by v0.2.2 was then used only to qualify the collector. A foreground attempt wrote raw frames but did not reach completion while its parent execution window ended. Under the supervisor's explicit boundary, the same Settings scene and unchanged collector semantics were rerun exactly once in the background with independent stdout/stderr logs.

That definitive rerun failed in two independently sufficient ways:

1. The collector wrote the action audit, pre frame, four post frames, and collection record, but `ground_truth_qualification_pass=false`. The terminal pair was semantically stable, yet the pre sample lacked critical a11y/package/route evidence (`semantic_element_count=0`, empty package set, null route), so the scroll transition could not be qualified.
2. During final cleanup, `adb -P 5038 ... reverse --remove tcp:18765` returned `listener 'tcp:18765' not found`. The exception escaped `finally`, so no `collection_complete.json`, corpus manifest, or valid completion accounting was created.

The collector, sampling window, label rule, and oracle were not modified after this failure. No easier held-out scene was substituted.

### Definitive rerun evidence

- Run root: `runs/eest_ac_v0_2_3_harness_dev_settings_qualification_b_20260804`
- Collection record SHA-256: `4583af1cabdbf8684165d1f210f04219b95bec096cfe70d28704174a52aee2b2`
- Oracle-input file SHA-256: `ce019d0980ac6437a1e46f8e4c342526eaffffcdbc9fa9fbc34f87c536936e13`
- Canonical unmutated trace SHA-256: `ea36652835991e4fb1b811e2b27f5ce95d49b77729f38a94d8b344dbaa6f686a`
- stderr SHA-256: `847f37008c2949239c2e2dd405429759f291e2038c5f2a6356f2fc5fe5219d8f`
- `collection_complete.json`: absent
- Held-out trace count: `0`
- Held-out oracle evaluations: `0`
- False accepts / false rejects / per-class precision-recall: not computable

## Offline tests

- EEST-focused regression: **116 passed, 0 failed**.
- Full repository regression: **1,118 passed, 1 failed** across 1,119 collected tests.
- The sole full-regression failure is the already declared protected legacy r79/r78 Gate-F frozen-manifest mismatch: `tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes`.
- No legacy manifest was edited to hide the mismatch.
- Full-regression stdout SHA-256: `c4bf90fb3fd7bfdab1ace8240cd5245806900e322decd6b5f2a2a06629cd08ad`

## Accounting and isolation

- v0.2.3 generation calls: `0`
- v0.2.3 model-call/generation/raw-call files: `0`
- Live model probes: `0`
- 9-cell / 48-cell / M-RISK runs: `0`
- Held-out labels exposed to oracle: `0`
- Remaining v0.2.3 collector/oracle processes at final audit: `0`
- ADB server/client path remained the official SDK binary on explicit port `5038`; no fallback to `5037` was used.
- Model health was read only; no generation endpoint was invoked.

## Claim-evidence verdict

| Claim | Verdict | Evidence boundary |
|---|---|---|
| O-C1: action classes have distinct authority policies | **PASS, offline candidate only** | Contract/schema/oracle property tests pass; no held-out qualification. |
| O-C2: semantic transitions are recognized without exact pixels | **NOT TESTED held-out** | DEV replay is contaminated and non-scoring. |
| O-C3: pixel-only changes never false-accept | **NOT QUALIFIED** | Offline and DEV controls pass directionally; held-out matrix absent. |
| O-C4: missing/contradictory evidence fails closed | **NOT QUALIFIED** | Property tests pass; held-out matrix absent. |
| O-C5: per-trace provenance is complete | **FAIL prerequisite** | No valid completed held-out corpus exists. |
| O-C6: eligible for separate live qualification | **FAIL** | `FAIL_COLLECTION`; strict held-out metrics are not computable. |
| O-C7: DEV/held-out isolation | **PASS** | All replay/collector attempts are explicitly DEV; no held-out evaluation occurred. |
| O-C8: v0.2.2 remains immutable | **PASS** | No prior trace or verdict was rewritten. |

## Final boundary

`eligible_for_separately_preregistered_live_oracle_qualification = false`

The next stage, if separately authorized, must first repair and requalify the measurement/collection infrastructure under a new protocol. It may not treat this oracle candidate or any v0.2.2/Settings/Camera/notification/Chrome trace as held-out evidence.
