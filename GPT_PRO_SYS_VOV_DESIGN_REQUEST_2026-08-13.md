# SYS-VOV Request: Visible Outcome Verification

Design one prospective system testing whether an independent visual verifier
can stop the executor from treating an unconfirmed action or completion claim
as accomplished. Use the common ledger and only this intervention.

Allowed: post-action verification by the same frozen Qwen model for a frozen
class of high-risk commitment actions or completion claims. The verifier sees
only the goal, proposed expectation, bounded provenance, and visible RGB. Its
fixed output is `SUPPORTED / UNSUPPORTED / UNCERTAIN` plus short evidence.

Excluded: next-action advice, planning, general criticism, donor retrieval,
hidden UI/evaluator/future frame, task rules, direct episode termination, action
override, and increased native step budget. Visible change is not automatically
semantic success, and verifier prose is not evaluator truth.

First audit how often false/unconfirmed continuation or termination occurs.
Then freeze triggers, prompt/schema, evidence rules, uncertainty handling,
deferral cap, call/token budget, and transport behavior. Full must be compared
with `VERIFIER-SHADOW` using the same trigger and calls but withholding verdicts,
and with a generic-extra-reasoning active control. A causal event requires a
verdict-induced next-action change followed by visible correction within three
steps or a paired final gain.

Use the common 4/4 -> Recipe -> remaining-14 schedule. Accuracy requires >5/19
and no A1-five loss. Report false accepts/rejects, deferral outcomes, calls,
tokens, wall time, mechanism events, and reward independently.

Return only
`GPT_PRO_SYS_VOV_VISIBLE_OUTCOME_VERIFIER_DESIGN_2026-08-13.md`, containing one
frozen design, exact prompts/contracts/budgets, trace audit, implementation map,
offline/preflight, shadow and active controls, prospective gates, verdicts, and
falsification criteria. No repository changes or GPU work.
