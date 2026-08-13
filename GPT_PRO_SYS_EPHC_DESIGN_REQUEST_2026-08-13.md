# SYS-EPHC Request: Evidence-Preserving History Compression

Design one prospective system testing whether bounded, faithful compression of
long action history reduces context cost without losing unconfirmed commitments
or task capability. Compression benefit and reasoning benefit are separate.

Allowed: the same frozen Qwen model as a summarizer only after a trace-derived
token threshold; at most three summary calls per episode; claims with source-step
references; current RGB and recent raw history remain authoritative.

Excluded: next-action advice, strategy judgment, success verification, new
facts, donor retrieval, planning, criticism, hidden UI/evaluator/future data,
task rules, unbounded recursive summaries, or increased native step budget.

Freeze trigger threshold, exact summarizer prompt/schema, source-grounding
checks, retained raw window, commitment preservation, merge/replacement rules,
hallucination fail-closed behavior, and call/token/storage budgets. Two controls
are mandatory: `SUMMARY-SHADOW`, which generates but does not use the summary,
and token-budget-matched mechanical truncation/compression. The former isolates
summary semantics; the latter isolates shorter context. Audit every summary
claim against cited source steps.

Use the common gates. Accuracy requires >5/19 and no A1-five loss. A compression
pass requires preserved capability plus lower total tokens; token reduction
alone is not accuracy improvement. Report summarizer costs and executor savings
separately.

Return only
`GPT_PRO_SYS_EPHC_EVIDENCE_PRESERVING_HISTORY_COMPRESSION_DESIGN_2026-08-13.md`,
with one frozen design, exact prompt/schema/faithfulness rules, budgets,
integration, offline audits, both controls, prospective schedule, independent
verdicts, and falsification conditions. No code or GPU.
