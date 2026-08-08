# Framework selection rubric

## Hard gate

A candidate is ineligible if it lacks usable public code, cannot accept the
frozen Qwen3-VL-32B without changing the research question, requires unavailable
training or proprietary services, cannot execute through the AndroidWorld action
interface, or addresses only one narrow symptom while leaving the rest of the
long-horizon controller unchanged.

## Weighted comparison after the hard gate

| Dimension | Weight | What earns a high score |
|---|---:|---|
| Failure-chain coverage | 35 | Jointly addresses planning, persistent state, source coverage, cross-app use, recovery, and completion rather than one isolated guard |
| Faithful adaptation feasibility | 25 | Core released algorithm can use Qwen3-VL-32B and our screenshot/action interface without reimplementing missing research logic |
| Match to observed evidence | 20 | Mechanisms correspond to failures measured in the 57-instance L0-L5 data, with explicit predictions for layer metrics |
| Reproducibility and provenance | 10 | Official code, pinned commit, license, clear dependencies, released prompts/configuration, and inspectable evaluation procedure |
| Remaining-time and compute cost | 10 | Can be qualified and run on one 19-task seed without new large-scale training or uncontrolled services |

The score is a decision aid, not a substitute for checking the implementation.
A high paper score cannot override a failed hard gate.

## Required capability matrix

Each candidate must be marked `implemented`, `claimed only`, `absent`, or
`unclear` for:

1. hierarchy/subgoal planning;
2. persistent or structured task state;
3. source identity and coverage tracking;
4. object/field/role binding across pages and apps;
5. loop detection and alternative-path recovery;
6. action-effect verification with typed evidence;
7. native or external completion verification;
8. cost control and context compression;
9. public Qwen-compatible visual grounding/action output;
10. AndroidWorld or comparable long-horizon benchmark support.

## Selection logic

- Prefer one mature, broad framework over a collection of isolated prompts.
- Reuse capabilities already solved in public work; do not reserve easy modules
  merely to make the later in-house method appear novel.
- Select the framework for broad expected coverage and reproducibility, not for
  compatibility with a preconceived RAVEN-M story.
- If the broad framework improves the intended layers but leaves a stable
  residual bottleneck, only then begin the next public-method decision.
- If it does not improve even its claimed layers, do not stack another method on
  top; return to candidate selection.

## Evidence standard for later progression

The first public framework is allowed to advance only if:

- all 19 scored episodes are scientifically eligible;
- final success and partial reward are reported with exact denominators;
- L0-L5 coverage remains complete;
- infrastructure and implementation invalidity remain separate from model or
  controller failure;
- the framework improves at least one preregistered mechanism metric without
  worsening final success through early stopping or budget inflation;
- costs are fully reported;
- no post-result tuning is folded back into the same scored result.
