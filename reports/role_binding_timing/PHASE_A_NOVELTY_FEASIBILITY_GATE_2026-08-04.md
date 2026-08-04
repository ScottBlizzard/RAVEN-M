# Phase A — Novelty and Feasibility Gate

Date: 2026-08-04  
Study namespace: `role_binding_timing`  
Generation calls in this phase: **0**

## Frozen primary question

> With the exact same correct source fact, model, screenshot/UI state, calls, tokens, and action budget, does exposing that fact before destination grounding (versus after destination grounding) interact with source/destination role ambiguity to increase `WrongTarget@FirstTargetingAction`?

This replaces the former objective of proving that the full RAVEN-M stack is superior. RAVEN-M may be reused only as causal instrumentation and failure-chain logging. This phase makes no memory-efficacy, controller-efficacy, or novelty claim.

## Repository and source boundary

- Starting HEAD: `3d97abfe58773c2db48d75f7cdc264791079b8da`
- Research-direction source: `D:/ZJU/Summer_Camp/RAVEN-M_GPTPro_answer.md`
- Research-direction SHA-256: `BC251ACD4A781B43D1858CF857FD75776CF244AEEC76F776535A7BDA5071B020`
- Machine-readable source and snapshot manifest: `PHASE_A_SOURCE_MANIFEST_2026-08-04.json`
- The three protected legacy r79 WIP files were read/hash-audited only and were not staged or modified by this phase.
- Prior protocol/result/tag/verdict and contaminated/held-out labels remain immutable. The formal LaTeX report was not modified.

## Verification method

The audit read the complete supplied PDFs, including appendices and prompt material, for the seven required works. It also inspected official repositories where one could be identified, searched the arXiv primary-source index for exact adjacent terms, and read two additional primary-source papers surfaced by the `premature commitment` search. Search scope and absence statements below are therefore bounded to this verified corpus; they are not claims that no equivalent work exists anywhere.

Primary-source index queries included exact phrases for `source destination` + `GUI agent`, `fact timing` + `agent`, `premature commitment` + `agent`, `entity binding` + `agent`, and `role ambiguity` + `agent`. The first, second, and fifth queries returned no substantive matching paper. The `entity binding` query returned the two required binding papers. The `premature commitment` query surfaced arXiv:2606.22936 and arXiv:2607.28815, which were added to this audit rather than ignored.

## Overlap–distinction ledger

| Work | Direct overlap | Exact-intervention check | Distinction relevant to this study |
|---|---|---|---|
| [ATMem, arXiv:2606.31612](https://arxiv.org/abs/2606.31612) | Mobile cross-app memory, entity/status structure, confusable distractors | **No equivalent found.** Memory is execution state supplied before each action; DataScope changes target/distractor count. | Does not expose the same correct fact before versus after a separately elicited destination commitment under a matched 2×2 timing × ambiguity design. |
| [Entity Binding Failures, arXiv:2606.30531](https://arxiv.org/abs/2606.30531) | Measures correct tool/wrong entity under ambiguity and structured gates | **No equivalent found.** Single-step synthetic enterprise tool use. | No mobile screenshot/UI state, no fact-timing intervention, and no first GUI target action. |
| [Binding Drift, arXiv:2607.18316](https://arxiv.org/abs/2607.18316) | Source/entity identity propagation and early binding errors in multi-step agents | **No equivalent found.** Controlled injection is at fixed step 1 and is deliberately wrong. | Does not move one correct fact across an explicit destination-grounding boundary; the paper itself lists fixed injection position/phrasing as a limitation. |
| [Salience Induction, arXiv:2607.17535](https://arxiv.org/abs/2607.17535) | Closest conceptual prior: true facts, position/proximity/emphasis manipulations, compatibility/ambiguity, first post-exposure binding error, token controls | **No exact mobile intervention found.** | RAG/text multi-hop setting; manipulates document salience rather than presenting the same fact before/after an explicit destination-grounding call with identical mobile critical state and target oracle. Position/recency remains a mandatory alternative explanation here. |
| [Naive Visual Memory Is Not Enough, arXiv:2606.14106](https://arxiv.org/abs/2606.14106) | GUI action-error taxonomy; memory may reduce state errors while increasing hidden-operation/grounding errors | **No equivalent found.** | No source/destination role factor and no early/late correct-fact intervention. |
| [AndroTMem, arXiv:2603.18429](https://arxiv.org/abs/2603.18429) | Mobile cross-app structured anchors with type/content/evidence/links | **No equivalent found.** History/ASM is available during action generation. | No two-call destination commitment and no matched timing manipulation. |
| [AgentProg, arXiv:2512.10371](https://arxiv.org/abs/2512.10371) | Explicit variables/dataflow and mobile contact/value transport | **No equivalent found.** | Program/workflow generation and execution tree do not manipulate when the same fact is exposed relative to destination grounding. |
| [When Agents Commit Too Soon, arXiv:2606.22936](https://arxiv.org/abs/2606.22936) | Token-matched intervention at a commitment juncture; separates commitment from correctness | **No equivalent found.** | Text QA; the intervention is an instruction to commit to a reasoning strategy, measured using cross-run hidden-state/trajectory convergence. It has no source/destination entities, mobile target oracle, or correct-fact timing manipulation. |
| [ECLoop, arXiv:2607.28815](https://arxiv.org/abs/2607.28815) | Evidence-conditioned gating at action-specific commitment boundaries | **No equivalent found.** | Coding/SWE-bench; gates edits/submission until evidence requirements are met. It does not test fact timing, role ambiguity, or wrong mobile targets. |

### Official artifact check

Official repositories were verified for Entity Binding Failures, Binding Drift, AndroTMem, AgentProg, and Salience Induction; immutable repository heads and selected prompt/runner hashes are in the source manifest. ATMem states that code/model will be made available, but no official public repository was identified in this audit. No official repository was identified for Naive Visual Memory from its PDF or repository search. Lack of an identified repository is recorded as an artifact-availability limit, not as evidence about novelty.

## Exact-equivalence checklist

An earlier study would count as exactly equivalent only if it jointly satisfied all of the following:

1. the fact is correct and byte/semantic-identical across compared conditions;
2. the fact appears exactly once;
3. early versus late placement is defined relative to an explicit destination-grounding commitment;
4. high versus low source/destination role ambiguity is factorially manipulated or matched;
5. screenshot bytes and UI state are identical within each matched base instance;
6. model revision, decoding, calls, prompt-token budget, and action budget are matched;
7. outcome is the first target-bearing GUI action with an entity/widget oracle;
8. position/recency and semantic-role-swap explanations are controlled.

No work in the verified corpus satisfies all eight. Several satisfy important subsets, especially Salience Induction (1, position controls, post-exposure binding outcome), Entity Binding Failures (role ambiguity and wrong entity), and ATMem/AndroTMem/Naive Visual Memory (mobile memory or GUI grounding). Their conjunction makes the proposed diagnostic scientifically motivated but also narrows what can be claimed.

## Novelty verdict

**EXACT OVERLAP NOT FOUND IN THE VERIFIED PRIMARY-SOURCE CORPUS; PROVISIONALLY DISTINCT, NOT A NOVELTY CLAIM.**

The proposed experiment is sufficiently distinguished to justify a falsifiable diagnostic. It must not be described as the first such study or as novel in publication-facing text until a broader systematic search and author-artifact check are repeated near submission. A positive result would initially support only a narrow causal claim about timing, role ambiguity, and the first target action.

## Existing-snapshot feasibility audit

Eight existing critical states were visually inspected and hash-frozen as **development-contaminated candidates**:

| DEV candidate | Critical state | Ambiguity utility | Oracle feasibility from stored artifacts | Boundary |
|---|---|---|---|---|
| H05 SMS recipient entry | Empty `Add Contact or Number` destination field | Low-ambiguity/field control | Visible field can be manually boxed; no raw UI-tree sidecar | DEV only |
| H11 Broccoli new-recipe form | `Title`, `Categories`, `Description` fields | High field-role interference | Candidate target fields visible; no raw UI-tree/node IDs | DEV only |
| H15 Gallery folder chooser | Current source path/file versus destination folder controls | Strong source/destination role conflict | Visual controls present, but correct `Download` destination is not on-screen and no UI tree is stored | DEV negative/corruption only |
| H04 Expense list | Many same-format rows; target row `Video Games` | High entity-list interference | Row visible and manually boxable; no stable node oracle sidecar | DEV only |
| H13 Recipe list | Repeated identical titles/descriptions | Very high entity/value interference | Multiple same-title rows are visible; task parameters provide row objects, but screenshot alone cannot uniquely bind hidden directions to a row | DEV corruption/ambiguity only |
| H16 Calendar event form | `Title`, `Location`, `Description`, start/end time | High field-role interference | Fields visible and manually boxable; no UI-tree/node IDs | DEV only |
| H06 Markor file list | Three source files plus create-new affordance | High source-order/destination-file interference | Rows visible and manually boxable; no raw UI-tree/node IDs | DEV only |
| H14 Playlist page | Created destination playlist versus menu/navigation affordances | Low/moderate entity-role control | Playlist card visible; truncated label and no raw node sidecar weaken exact oracle | DEV only |

Direct evidence:

- all eight screenshot files exist and their byte hashes match the manifest;
- the corresponding episodes and task parameters identify intended source/destination roles;
- none of the eight episode directories contains a raw a11y/UI-tree/XML/observation sidecar tied to the inspected frame;
- every candidate was generated or inspected in prior runs and is therefore contaminated for this new hypothesis.

Inference:

- the screenshots are adequate for parser, prompt-layout, blinding, corruption, and manual-oracle tooling tests;
- they are not adequate to certify a fresh held-out 8-template qualification pilot, because stable target IDs and unseen condition assignment cannot be reconstructed without extra judgment.

## Feasibility verdict and stop/continue decision

**Phase A: CONDITIONAL PASS for zero-call implementation; LIVE PILOT NOT YET ELIGIBLE.**

- Literature gate: pass within the bounded verified corpus; no exactly equivalent intervention was found.
- DEV snapshot gate: pass; at least eight distinct critical-state candidates exist without relying on EEST-P1 alone.
- Held-out qualification gate: fail/not yet tested; current candidates are contaminated and lack raw per-frame UI-tree target IDs.
- Decision: continue to Phase B only. Build the new independent protocol/tooling namespace, use the eight frozen frames only for DEV tests, and require newly collected/frozen snapshots with oracle qualification at or above 95% before any generation call.
- If the infrastructure cannot produce eight fresh critical states with stable screenshot/UI-tree pairing and unambiguous destination target IDs, stop before Phase C rather than silently reusing these frames as held-out evidence.

## Claim–evidence table

| Claim | Evidence | Verdict |
|---|---|---|
| The exact 2×2 mobile intervention is already established | No exact match in nine fully read primary papers and inspected official artifacts | **NOT SUPPORTED** |
| The proposed diagnostic is distinct enough to preregister | Exact-equivalence checklist has no satisfying work in the verified corpus | **SUPPORTED WITH CORPUS BOUNDARY** |
| Existing data can support offline development | Eight visually inspected, hash-frozen critical states | **SUPPORTED** |
| Existing data can serve as held-out qualification evidence | All eight are contaminated; raw per-frame UI-tree/node IDs absent | **NOT SUPPORTED** |
| Timing causes wrong-target actions | No experiment has been run | **UNTESTED** |
| RAVEN-M/M-SLOTS is effective | Outside the new question and unsupported here | **UNTESTED / OUT OF SCOPE** |

## Next gate

Phase B must freeze the factorial protocol, schemas, deterministic prompt builders, token audit, blinding, parser, oracle format, replay manifests, and zero-call runtime preflight in a new namespace. Generation remains forbidden until all offline tests pass, the model revision is locked, token matching meets the preregistered tolerance, and at least eight newly collected base templates achieve at least 95% snapshot/oracle qualification.
