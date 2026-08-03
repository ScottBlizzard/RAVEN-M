# EEST-AC v0.2 Blind Task Selection Freeze

This selection was made only after the v0.2 focused suite, full regression, source-isolation audit, and zero-generation-call real-runtime gate passed. The repository-wide novelty scan covered prior `runs/`, `05_project/configs/`, and `reports/` text artifacts.

## Frozen templates and instances

| Key | Role | Template | Parameter seed | Goal SHA-256 | Params SHA-256 | Selection reason |
|---|---|---|---:|---|---|---|
| EEST-P2A | positive | `SimpleSmsSendClipboardContent` | 2026080401 | `64f9e10977cba5e75e00e1c7fb5570d1718f9c21eef844af845b6f3d750e6492` | `699f6a975af6770a9eb8cd66ceda37a544623b5b8b4b1571001d55a980d2dc1b` | The value originates in the clipboard and must be carried to a literal phone-number destination across apps/pages. |
| EEST-P2B | positive | `MarkorTranscribeReceipt` | 2026080402 | `5581a0fc784750275e7495d5b4c20477b8114799c52c0c9dfa07aba63c30e8ca` | `8dabfb840bd5aae975fdb9b39bf0c517374e8231d05423ec975c9bf87421f70a` | Transactions must be read from a receipt in an image viewer and applied to the requested Markor file. |
| EEST-N2 | negative control | `ClockStopWatchRunning` | 2026080403 | `d19e223c9dfcc150cdccac3737ec6d176f7974934bfdc2d0cab143e2594e1d0b` | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` | Short reversible within-app navigation/action with no cross-page entity-field memory requirement. |

All three task-class strings had zero hits in the prior-artifact novelty scan. The positive templates are distinct and their exact goal/parameter hashes are deterministic across four independent regeneration probes.

## Frozen exact-span roles

- EEST-P2A: source `clipboard`; requested field `content`; destination `+19091144188`; rule `transfer_to_destination_with_source_field`.
- EEST-P2B: source `the receipt.png`; requested field `the transactions`; destination `a file in Markor, called receipt.md`; rule `create_destination_with_field_from_source`.
- EEST-N2: no transfer roles; fail-closed `opaque_closed_task` frame shared by all arms.

The role parser receives task text only. Template class, parameters, app identity, names, and coordinates are not inputs to parser dispatch.

## Blindness and schedule

The nine-cell order is frozen in `eest_ac_v0_2_blind_smoke.json` using schedule seed 2026080409. No task is adjacent to itself. From the first generation call until `batch_complete.json` records all nine final cells, no cell trajectory, screenshot, decision, evaluator result, or partial aggregate may be inspected and no code/config/prompt/schema may change.

The runner stops after nine cells and never expands automatically. SMS/Clock v0.1.1 instances remain development-only and are not reused here; the selected templates and parameter hashes are new.
