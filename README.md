# RAVEN-M Research Repository

This repository records a summer-camp research project on memory management for
MLLM-driven mobile GUI agents. It contains the implemented baselines, RAVEN-M
prototypes, frozen protocols, tests, audit reports, and negative results. It is
not a repository in which every implemented component has been shown to improve
task success.

## Start here: research redirection

The project has reached a point where adding more memory modules is not justified
by the available evidence. For an independent novelty audit and a possible change
of research direction, read:

- [`reports/research_direction/GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md`](reports/research_direction/GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md)
- [`00_admin/plans/GPTPro_master_prompt.md`](00_admin/plans/GPTPro_master_prompt.md)

That brief is self-contained. It separates direct evidence from inference,
summarizes the strongest negative and mechanism-level results, identifies ideas
that are already covered by prior work, and defines the standard that a genuinely
interesting next direction must meet.

## Current evidence boundary

The main empirical finding is not that RAVEN-M has succeeded. It is that the
original research question was too broad and was not well matched to the dominant
failure modes observed in AndroidWorld.

| Stage | Direct result | Valid conclusion |
|---|---|---|
| Legacy non-Hard paired check | Simple summary B3 completed 4/4; full RAVEN-M M0 completed 3/4 and used more calls, tokens, and actions | A heavier memory/controller framework was not automatically better |
| EEST-AC v0.1.1, 8 cells | All four arms completed 1/2 tasks; typed memory captured 4/4 source bindings but produced no paired task win | Structured capture showed a mechanism signal, not a success-rate gain |
| EEST-AC v0.2, 9 blind cells | All cells stopped before an environment action because the action interface was incompatible | Controller floor; no memory comparison was possible |
| v0.2.1 qualification | The first real-model decision still violated the frozen decision schema after one repair | Prompt/schema contract remained unqualified |
| v0.2.2 qualification | Three commands were schema-valid and executable; one of three failed the overly strict terminal-pixel rule | Action contract improved, while outcome measurement remained unresolved |
| v0.2.3 collection | No valid completed held-out trace corpus was collected | The action-conditioned oracle remained an offline candidate |
| v0.2.4 lifecycle qualification | AndroidEnv failed because the device exposed no `settings` service; readiness and action counts were zero | Infrastructure failure, not evidence for or against memory efficacy |

The strongest positive signal is narrow: explicit records can preserve a
cross-page `source entity -> field -> value` binding. The strongest counter-signal
is equally important: preserving the value did not make the agent reach the
correct destination entity or finish the task. Perception, grounding, transition
measurement, action contracts, recovery, and completion verification can dominate
the memory effect.

## Candidate research shift

The current candidate hypothesis is:

> Task length is not the same as memory difficulty. Memory difficulty may be
> better predicted by the information-dependency structure between observing a
> fact and using it: dependency distance, interference among similar entities or
> fields, and the observability gap of the final outcome.

This is a hypothesis to audit, not a novelty claim. The next step is to analyze
real failed tasks and compare matched tasks. It is not to rename ordinary
structured memory as a new method.

## Evidence entry points

- [`RAVEN-M_研究假设与实验方向审计_2026-08-03.md`](RAVEN-M_研究假设与实验方向审计_2026-08-03.md): broad audit of the original research assumptions and benchmark fit.
- [`reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md`](reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md): the most informative live paired smoke, including the correct-value/wrong-destination failure.
- [`reports/eest_ac/claim_evidence_v0_1_1_verdict.md`](reports/eest_ac/claim_evidence_v0_1_1_verdict.md): claim-by-claim boundary for the v0.1.1 smoke.
- [`reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md`](reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md): blind controller-floor diagnosis.
- [`reports/eest_ac/eest_ac_v0_2_2_qualification_final_report.md`](reports/eest_ac/eest_ac_v0_2_2_qualification_final_report.md): action-contract and terminal-state measurement evidence.
- [`reports/eest_ac/eest_ac_v0_2_3_collection_floor_verdict.md`](reports/eest_ac/eest_ac_v0_2_3_collection_floor_verdict.md): trace-collection failure and oracle boundary.
- [`reports/eest_ac/eest_ac_v0_2_4_collector_lifecycle_verdict.md`](reports/eest_ac/eest_ac_v0_2_4_collector_lifecycle_verdict.md): latest frozen infrastructure verdict.

## Repository map

```text
RAVEN-M-Research/
├── 00_admin/                 # plans, requirement trace, and decisions
├── 01_sources/               # source ledger and provenance policy
├── 02_literature/            # metadata, notes, search logs, and local manifests
├── 03_code/                  # third-party repository manifests
├── 04_protocols/             # frozen and amended experiment protocols
├── 05_project/               # agent implementations, schemas, configs, and tests
├── reports/                  # analyses, claim-evidence verdicts, and direction audits
├── runs/                     # local raw traces; most are intentionally not in Git
└── checksums/                # local integrity records
```

## Interpretation rules

- A passing unit test is implementation evidence, not task-efficacy evidence.
- A valid memory record is capture evidence, not proof that the agent used it
  correctly.
- A blocked unsafe or invented action is a local guard success, not necessarily a
  task-level success.
- All-failure ties are not equivalence evidence.
- Development-contaminated tasks and repeatedly debugged seeds must not be reported
  as held-out generalization.
- Frozen negative results must not be rewritten after the fact.

## Working-tree boundary

Three legacy r79 files may remain intentionally modified or untracked in the local
working tree. Their hashes are protected by the later frozen protocols. They are
not part of the new research-direction document and must not be overwritten,
silently staged, or used to repair a later result.
