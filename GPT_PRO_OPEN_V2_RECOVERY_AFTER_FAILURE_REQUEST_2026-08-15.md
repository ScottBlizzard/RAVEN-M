# Open V2 Pro Request — Recovery After Recognized Failure

You are in a fresh research-design conversation. First audit <https://github.com/ScottBlizzard/RAVEN-M>, branch `a2-verified-progress-audit-20260810`, at frozen evidence commit `b5635939acd628156f8c8e36aa8219834a3e6ad8`.

Read `evidence/composite/TOP3_OPEN_DESIGN_CHARTER_2026-08-15.md`, `evidence/composite/TOP3_COMPONENT_SELECTION_2026-08-15.md`, `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`, the A1-R2 implementation/result, and formal plus diagnostic A7–A12 evidence. Verify repository facts independently.

Your final document must satisfy every section of `evidence/composite/TOP3_IMPLEMENTATION_READY_OUTPUT_CONTRACT_2026-08-15.md`. Design selection is open, but the selected design must be implementation-ready with no behavior-affecting decisions deferred.

Research problem: once the agent has visible evidence that its current approach is failing, recurring, or not producing progress, what additional computation or control mechanism most reliably produces a better next decision without destroying previously successful behavior?

A triggered recovery critic is only the investigator's initial hypothesis. You may retain, redesign, rename, or reject it. You may instead propose structured diagnosis, counterfactual recovery, localized replanning, action arbitration, uncertainty escalation, a deterministic policy component, or another evidence-supported mechanism in this problem family. Do not merely optimize the initial critic prompt.

A1-R2 is the default positive reference because it scored 6/19 with zero paired loss versus A1, but you may select a different explicit parent or minimal primitive if repository evidence supports it. You must explain why the chosen parent is safer and how its existing successes are preserved. Do not inherit a failed arm wholesale or relabel it as repaired.

You decide the trigger, role decomposition, state, prompt, number of auxiliary calls, call budget, output schema, control flow, and active control from trace evidence. Prefer the smallest falsifiable intervention, but do not accept an arbitrary investigator-authored limit if it prevents a sound design. If extra inference is used, include a fair resource-matched active control that can distinguish specialized mechanism value from generic additional reasoning.

Hard boundaries: no evaluator/reward, hidden UI/accessibility, activity/package, future frames, task/app whitelist, cross-episode leakage, increased native action budget, or unreported calls/tokens/time. Preserve historical evidence. Freeze all decisions before live generation. Scientific failure is not rerun. All tasks are already observed, so no held-out claim.

Before selecting a mechanism, perform or specify a zero-generation, hash-bound cross-task audit. Do not design only from `ExpenseDeleteMultiple2`. Quantify the proposed failure condition in successful and failed tasks, alternatives considered, counterexamples, expected preservation risk, and why the problem requires more than memory availability.

The live protocol must preserve the six A1-R2 successes before releasing the remaining thirteen. Final accuracy improvement requires at least 7/19, reward >6.5, and no loss on the R2 six. Accuracy, resource cost, and component causality are separate verdicts. Define an ablation/control structure appropriate to your chosen mechanism rather than mechanically copying the investigator's first draft.

If evidence does not support this problem family, say so and return a no-go plus the minimum missing-evidence audit. Do not manufacture complexity.

Only design; do not modify the repository or run GPU experiments. Return exactly one self-contained Markdown document named `GPT_PRO_OPEN_V2_RECOVERY_AFTER_FAILURE_DESIGN_2026-08-15.md`. It must include evidence audit, alternative comparison, one final recommended system, exact algorithms/prompts/contracts/budgets, integration blueprint, preservation analysis, offline/preflight/live protocol, controls, verdicts, and falsification rules.
