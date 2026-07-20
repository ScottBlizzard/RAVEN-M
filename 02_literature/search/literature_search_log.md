# Literature Search Log

## 2026-07-20 — repository bootstrap audit

- Scope: GUI/mobile/computer-use agents; memory/history/planning/reflection/retrieval/process evaluation; AndroidWorld; Sheng Zhou/Eagle Lab.
- Time emphasis: 2025–2026, retaining foundational 2023–2024 work.
- Primary sources used: AndroidWorld official repository/task page, Qwen official repository/model card, ACL Anthology, AAAI proceedings, IEEE/CVF Open Access, NeurIPS proceedings, Sheng Zhou official homepage, Eagle Lab.
- Deduplication: DOI first, then ACL/OpenReview/proceedings ID, arXiv ID, normalized title + first author.
- Status rule: proceedings/publisher/OpenReview is archival evidence; arXiv alone is `preprint_only`; GitHub README alone does not establish venue.
- Output: 34 works from the master plan plus 3 direct lab-alignment papers, divided into P0/P1/P2 in `metadata/papers.csv`.

### Queries represented in the master plan

```text
"GUI agent memory" OR "mobile GUI agent memory"
"mobile-use agent" AND (long-horizon OR memory OR history)
"MLLM GUI agent history" OR "history-aware GUI agent"
"episodic memory" AND (GUI agent OR computer-use agent)
"structured memory" AND (mobile agent OR GUI automation)
"hierarchical memory" AND GUI
"self-evolving memory" AND agent
"page graph" AND GUI agent
"trajectory compression" AND GUI agent
"state summarization" AND GUI agent
"reflection" AND "error recovery" AND GUI agent
"process-aware" AND GUI agent evaluation
AndroidWorld AND (memory OR history OR long-horizon)
"retrieval augmented" AND GUI agent
"procedural memory" AND computer-use agent
```

### Current limitations

- This bootstrap audit verifies the named core sources; it is not yet a systematic-review result-count export.
- OpenReview may require browser verification, so AndroidWorld paper identity should also be cross-checked against arXiv and the official repository.
- Code not linked from a paper/author/project source remains `manual_needed`.
- Before the final report, rerun a delta search for work published after 2026-07-20.

