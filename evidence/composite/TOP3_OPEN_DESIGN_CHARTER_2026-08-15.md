# Top-3 Open Design Charter

Date: 2026-08-15

Status: supersedes the overly prescriptive algorithm details in the first Top-3 request drafts. The three problem families remain selected, but their proposed mechanisms are hypotheses, not mandatory implementations.

## Why this correction is necessary

The first Top-3 requests correctly froze leakage, attribution, cost accounting, and prospective gates, but they prematurely fixed details such as exact auxiliary roles, output schemas, trigger shapes, and call caps. That risks asking GPT Pro to optimize an investigator-authored solution instead of independently solving the evidence-grounded problem.

The revised process freezes **the research problem and scientific contract**, while leaving **the mechanism** open to independent design.

Every Pro should produce the complete research blueprint described in
`evidence/composite/TOP3_COMPLETE_DESIGN_OUTLINE_REQUIREMENTS_2026-08-15.md`.
It should be structured and detailed, but final implementation contracts remain
the research team's responsibility.

## Hard boundaries that remain fixed

1. Audit the commit-pinned repository and distinguish formal, post-hoc, inferred, and missing evidence.
2. Preserve the same Qwen model/revision, AndroidWorld task instances, task seed, generation seed, sampling, evaluator, and native action budgets unless a proposed auxiliary call is explicitly part of the intervention and fully costed.
3. Never expose evaluator/reward, hidden UI/accessibility, activity/package, future frames, task/app whitelists, or known task outcomes to runtime decisions.
4. Do not modify historical A-series evidence or relabel a failed arm as repaired.
5. Define one prospective system per Pro output, with exact source, state, prompt, call, capacity, and failure boundaries frozen before generation.
6. Compare the specialized Full system with a no-component base and an appropriate resource-matched active control whenever extra inference is used.
7. Separate system accuracy, component causality, and cost.
8. Use fail-fast capability preservation before full-suite expansion; scientific failures are not rerun.
9. Do not claim held-out generalization on the already observed task/seed suite.
10. Missing raw evidence must be materialized with a zero-generation, hash-bound audit rather than guessed.

## Design choices deliberately left open

Each Pro may independently decide and justify:

- whether the initial named component is actually the right intervention;
- whether to rename or replace it with a better mechanism in the same problem family;
- which memory arm or primitive is the correct parent, with A1-R2 as the default positive reference rather than a mandatory code parent;
- whether the system needs zero, one, or several bounded auxiliary calls;
- whether triggering should be event-based, phase-based, uncertainty-based, or absent;
- the role decomposition, state representation, prompt schema, update rules, and control flow;
- the minimum fair active control and ablation;
- resource limits justified from trace distributions rather than inherited from the investigator's guess;
- whether repository evidence supports implementation at all.

If a Pro rejects the initial critic/planner/verifier framing, it may propose the nearest evidence-supported alternative, but must keep its output centered on the assigned problem family and explain overlap with the other two tracks.

## Three problem families, not three predetermined algorithms

### Track A: recovery after recognized failure

Question: once the system has visible evidence that its current approach is failing or recurring, what additional computation or control mechanism most reliably produces a better decision?

“Triggered critic” is only an initial hypothesis. Alternatives may include structured diagnosis, counterfactual recovery, replanning, action arbitration, uncertainty escalation, or a justified deterministic mechanism.

### Track B: long-horizon decomposition and coordination

Question: what additional computation or state organization helps the agent convert a long goal into stable, evidence-grounded phases without losing requirements or drifting locally?

“Hierarchical milestone planner” is only an initial hypothesis. Alternatives may include subgoal scheduling, phase control, adaptive replanning, workflow state, or another justified architecture.

### Track C: reliable action-outcome and completion judgment

Question: what additional computation prevents the agent from continuing after an unsupported action, forgetting an unconfirmed obligation, or terminating on insufficient visible evidence?

“Visible outcome verifier” is only an initial hypothesis. Alternatives may include delayed confirmation, confidence-calibrated evidence checks, dual-pass decisions, selective verification, or another justified architecture.

## Selection after Pro outputs

The three designs will be reviewed for evidence fit, preservation risk, leakage, implementation feasibility, resource cost, attribution quality, and expected value. At most three may proceed, and fewer—including zero—may be selected. Components are not combined merely because they were designed in parallel.
