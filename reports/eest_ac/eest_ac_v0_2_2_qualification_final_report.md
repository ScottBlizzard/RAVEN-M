# EEST-AC v0.2.2 Decision Envelope Qualification - Final Report

## Verdict

**FAIL under the preregistered conjunctive rule.** The batch stopped after all three qualification cells; no efficacy batch was started.

The narrow action-contract signal is positive: all three first outputs were complete schema-valid canonical commands, all three mapped through the adapter, executed, and reset successfully. The overall qualification still fails because DEQ-BACK-03 did not satisfy exact terminal screenshot-hash agreement. Although the action moved from Camera to the launcher and terminal a11y/package signatures stabilized, the last two launcher pixel hashes differed. The frozen rule therefore forbids relabelling it as PASS.

## Per-probe evidence

| Probe | Initial / repair | Canonical action | Schema / adapter / execute | Stable change | Reset | Calls | Tokens | Time (s) | Verdict |
|---|---|---|---|---|---|---:|---:|---:|---|
| DEQ-SCROLL-01 | initial_direct / no | `{"duration_ms":500,"type":"swipe","x":0.5,"x2":0.5,"y":0.8,"y2":0.2}` | pass / pass / pass | pass | pass | 1 | 3558 | 70.235 | PASS |
| DEQ-OPEN-02 | initial_direct / no | `{"app_name":"Settings","type":"open_app"}` | pass / pass / pass | pass | pass | 1 | 3520 | 53.766 | PASS |
| DEQ-BACK-03 | initial_direct / no | `{"type":"press_back"}` | pass / pass / pass | FAIL: terminal_pixels_unsettled | pass | 1 | 3510 | 56.094 | FAIL |

## Aggregate

- First-output command pass: 3/3; accepted within one repair: 3/3; repairs used: 0.
- Coverage/schema/adapter/execution/reset: 3/3 each; required stable state change: 2/3.
- Calls: 3 raw = 3 attempts = 3 records; accounting PASS.
- Tokens: 10452 prompt + 136 completion = 10588 total.
- Time: 180.095s summed probe time; 224.114s batch wall time.
- Truncation/max-token hits/metadata-only repairs: 0/0/0.

## Claim-evidence boundary

The evidence supports that the repaired full envelope can elicit valid executable commands from the frozen real model (3/3 direct). It does not support a full qualification PASS because the required state-change measurement passed only 2/3. It provides no M-SLOTS, M-RISK, memory, or task-efficacy evidence. No held-out efficacy batch may start from this result.

## Frozen runtime and audit

- Model: `Qwen/Qwen3-VL-32B-Instruct` revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, backend `qwen3_vl_32b_transformers_bf16_4x4090_v1`.
- ADB: port 5038, serial `emulator-5554`, same official client/server binary: `True`; no 5037 fallback.
- Lock: `eest-ac-v0.2.2-envelope-candidate-r2-20260804` / `f86c992a3ecb28cf796b6578ccbfde58de14d76b`, 33 files; start record matched lock: `True`.
- Legacy WIP end hashes: `3/3`; staged legacy files: `0`.
- Remaining experiment processes: `0`.
- Raw completion SHA-256: `e0a8c4679b85934df478cae3adb82278bf1ed57f35be9f7679760a895002c372`.

Final boundary: stop at controller/measurement qualification. Do not start new task selection, 9-cell, 48-cell, M-RISK, or efficacy experiments.
