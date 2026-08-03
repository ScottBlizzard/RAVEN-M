# EEST-AC Minimal Paired Smoke Protocol v0.1.1 Amendment

Status: **frozen before any model call**  
Supersedes only the conflicting negative-control gate wording in v0.1. All tasks, seeds, arms, budgets, schedule cells, hypotheses, metrics, and stopping rules otherwise remain unchanged.

## Reason for amendment

During deterministic controller tests, the v0.1 text was found to contain two incompatible requirements:

1. terminal `Done` is explicitly a consequential M-RISK trigger; and
2. one claim-table sentence expected EEST-N1 to have zero gates.

An agent that opens the requested app and then declares `Done` necessarily satisfies (1). This is a protocol wording defect discovered before task generation and before model use, not a response to an experimental outcome.

## Frozen interpretation

- On EEST-N1, `open_app`, taps used only to clear a required pop-up, Back, and other reversible navigation must trigger **zero** gates.
- A later terminal `Done` may trigger exactly one M-RISK gate. Its call, tokens, and wall time are counted as negative-control overhead.
- `unnecessary-verification rate` counts any gate on a detector-ineligible candidate as unnecessary. The preregistered terminal `Done` gate is reported separately as terminal-verification overhead, not silently removed from cost.
- If this one terminal gate pushes M-RISK cost above 15% without reducing a high-risk error, the preregistered removal rule still applies.

## Trigger precision clarification

The shared risk detector reads the candidate action type and active action-intent wording in `decision_summary`. It must not trigger on incidental past-tense content in task facts or expected outcomes—for example, “open the message Avery sent.” This clarification prevents a lexical false positive on low-risk navigation and adds no task-, app-, coordinate-, date-, or layout-specific rule.
