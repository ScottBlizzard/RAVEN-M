# EEST-AC v0.2.3 Preregistered Claim-Evidence Table

| ID | Claim under test | Required evidence | PASS condition | Explicitly excluded |
|---|---|---|---|---|
| O-C1 | Action classes require different outcome witnesses. | Single contract, generated schema, parser/oracle conformance matrix, property tests. | Swipe, open-app, and navigation policies expose distinct required/optional/veto/missing rules with no task/App branches. | Task-specific heuristics or a universal pixel rule. |
| O-C2 | Semantic transitions can be recognized without exact terminal pixel equality. | Frozen held-out positives with stable semantic witnesses and raw pixel/a11y/package/activity hashes. | Every held-out positive is accepted from authorized semantic witnesses. | Reclassifying v0.2.2 or counting DEV replay. |
| O-C3 | Pixel changes alone do not authorize success. | Dynamic-pixel/no-semantic held-out controls and DEV diagnostics. | Zero false accepts; pixel-only controls are reject/uncertain with provenance. | Treating visual churn as task effect. |
| O-C4 | Missing or contradictory critical evidence fails closed. | Held-out missing/unstable/wrong-target controls plus negative/property tests. | All such rows match frozen reject/uncertain labels; zero false accepts. | Silent inference from App names or screenshots. |
| O-C5 | Oracle provenance is complete and auditable. | Per-row input/output/label hashes, rule ID, witnesses, vetoes, missing fields, confidence, ordering/accounting. | Complete records for every held-out row. | Post-hoc labels or undocumented threshold changes. |
| O-C6 | The oracle is eligible for a separate live qualification. | One frozen held-out run over at least 12 traces. | 12/12 or more correct, 0 false accept, 0 false reject, per-class accept precision/recall 1.0, full coverage/audits. | Any memory, M-SLOTS, M-RISK, or task-efficacy claim. |
| O-C7 | DEV replay is isolated from held-out evidence. | Corpus hashes and row flags. | Every prior trace is `development_contaminated=true`, `held_out_eligible=false`; none contributes to metrics. | Calling a replay row held-out or using it to satisfy PASS. |
| O-C8 | v0.2.2 remains immutable. | Prior completion/report hashes and unchanged files. | Prior verdict remains FAIL and no trace/result is rewritten. | Retroactive relabelling of DEQ-BACK-03. |

Stopping verdicts:

- `PASS`: eligible only for a separately preregistered live oracle qualification.
- `FAIL_COLLECTION`: held-out coverage or ground truth could not be reliably frozen; no oracle evaluation.
- `FAIL_HELD_OUT`: at least one frozen row was wrong or incompletely audited; no second oracle version/evaluation.
- `FAIL_INFRASTRUCTURE`: required local evidence could not be collected or hashed; no live/model escalation.
