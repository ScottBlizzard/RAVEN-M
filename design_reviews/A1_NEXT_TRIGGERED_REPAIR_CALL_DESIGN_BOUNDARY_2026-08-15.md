# A1 Next Direction: Triggered Repair Call Design Boundary

Status: design boundary only; not an experiment arm, not implementation-qualified, and not authorized for live generation.

## Evidence basis

A1-R9 detected recurring routes and injected recovery text without productive divergence. R10–R11 showed that spatial instructions and explicit self-checks can be delivered and sometimes followed without completing the fixed first task. R12 removed repeated prompt history and reduced tokens, again without reward. The next test must therefore distinguish “better decision computation” from “more memory text.”

## Single proposed system

At the first frozen stagnation event in an episode, make one auxiliary call to the same frozen Qwen3-VL-32B revision. The event is controller-authored and task-agnostic: the same canonical action family has produced two no-material-RGB-progress transitions from strict-near visible states within four executed actions. No task name, app identity, UI tree, evaluator, future trace, OCR, or package/activity may enter the decision.

The auxiliary call receives only the goal, current model-visible screenshot, and the last four executed action summaries. Its fixed output is at most 96 tokens with exactly two fields:

```text
FAILURE_HYPOTHESIS: <one visible-evidence-grounded sentence>
RECOVERY_PRINCIPLE: <one task-agnostic next-decision principle; no tool call>
```

The result is injected into exactly the next ordinary executor request and then destroyed. It cannot directly issue, block, replace, retry, or terminate an action. There is at most one auxiliary call per episode, no retry, temperature/sampling/model revision are frozen, and executor native action budgets remain unchanged.

## Required three-way comparison

1. `TRIGGERED_REPAIR_FULL`: specialized prompt above.
2. `TRIGGERED_GENERIC_CONTROL`: identical trigger, screenshot, call count, model, token ceiling, and injection slot, but a generic “inspect and reconsider the next step” prompt without failure-role specialization.
3. `NO_AUX_BASE`: identical base composite and trigger audit, with no auxiliary call.

Specialized repair cannot be credited unless it beats the generic active control; otherwise any gain is attributable only to extra inference. Every auxiliary and executor call/token/second is reported separately.

## Advancement gates

- Offline: replay must establish at least one trigger opportunity on the frozen first task and bounded trigger rates on all A0-success tasks; zero generation.
- Live stage 1: run `ExpenseDeleteMultiple2` for Full and Generic Control in frozen order. Full must succeed, and the first post-injection action must diverge from the matched control with visible progress within four executed actions and no four-step relapse.
- Live stage 2: only then run the remaining five frozen capability tasks for both arms; Full must be 6/6 with no paired loss.
- Live stage 3: only then release the remaining 13 tasks. Accuracy, system cost, and causal-component verdicts remain separate.

A valid scientific failure is never rerun. Infrastructure-invalid attempts are retained and explicitly linked to at most one replacement. All 19 tasks are already observed, so the study is a matched prospective diagnostic, not held-out generalization.

## Stop rule

If specialized Full fails the first task, or does not outperform the call-matched generic control at the first productive opportunity, stop this direction. Do not increase call count, alter the trigger, lengthen output, or add a planner under the same identity.
