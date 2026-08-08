# Decision request: choose the first public framework to reproduce

## 1. Decision boundary

Make exactly one research decision:

> Which existing public framework should be reproduced first as a broad upgrade
> over the official-style Qwen3-VL-32B mobile-agent baseline on AndroidWorld Hard?

The selected framework should address as much of the observed end-to-end failure
chain as possible. Do not choose a paper merely because it targets one isolated
error. Do not design a second-stage framework combination, and do not propose our
own new method in this response. Those decisions must wait for the first public
framework's measured L0-L5 results.

## 2. Why this decision is now evidence-based

The project previously reported all-zero Hard outcomes under a home-built
controller. That evidence was confounded by framework and interface errors. The
current baseline instead freezes Qwen's public mobile-agent prompt, tool schema,
coordinate semantics, message history, recommended sampling values, one exact
32B revision, native task budgets, and the AndroidWorld evaluator.

The corrected result is 7/57 successes. On the first task seed it is 4/19, which
matches the informal expectation that this 32B setup can solve roughly three or
four of the 19 task classes in one sweep. The other two task seeds are robustness
evidence, not 38 additional task classes.

Every one of the 1,175 valid steps contains:

- L0 model/runtime evidence;
- L1 screenshot/perception-grounding evidence;
- L2 parser, protocol, and coordinate evidence;
- L3 actual action-execution evidence;
- L4 before/after transition evidence;
- L5 terminal claim and native evaluator evidence.

This makes it possible to test whether a public framework changes the intended
layer rather than merely producing a longer trajectory.

## 3. Observed failure vector to cover

The first framework should cover many of these jointly:

1. **Long-horizon planning and progress state.** The model repeats pages and
   actions, loses subgoal state, or terminates without completing all clauses.
2. **Source identity and full source coverage.** It may open the correct app but
   not the correct file, leave before reading the document, or treat one visible
   screen as the complete source set.
3. **Object-set capture and structured retention.** The correct objects, fields,
   dates, categories, or transient values frequently never enter the executable
   action stream.
4. **Cross-app handoff and destination binding.** Reaching the destination app
   does not ensure that the captured values are written to the right object or
   field.
5. **Typed action-effect verification.** A real GUI transition can prove a weaker
   fact than the task requires: Favorite is not Marker, visiting a place is not
   adding a waypoint, and a copy toast does not prove the correct directory.
6. **Recovery after loops, ambiguity, or failed effects.** Acknowledging that an
   action failed is insufficient if the framework has no alternative strategy.
7. **Completion closure.** The model frequently declares success without native
   task completion evidence.

The strongest whole-suite measurements are:

- correct first task-app entry: 49/57; wrong then recovered: 6/57; never reached:
  2/57. App launch is not the dominant bottleneck.
- explicit cross-app tasks: 27 trajectories; 16 reached the destination app,
  but 0/27 fully succeeded.
- multi-object create tasks: among 26 expected objects whose trajectories reached
  the destination, only 3 correct identifiers appeared in target-app text input.
- Markor source funnel: 9/9 entered Markor, 8/9 opened the specified document,
  5/9 exposed at least one recoverable correct object, 3/9 exposed the full set,
  2/9 typed any correct object in the destination, and 0/9 fully succeeded.
- clean object-role evidence mismatch: 13 episodes across five task classes and
  four app families.
- false terminal success: 21 trajectories; repeated states: 39; consecutive
  stagnation: 14.

## 4. What has already been tried

Do not recommend these as if they were untested solutions:

- a generic instruction to remember transient observations;
- L4 history correction when an action produces no observable transition;
- a generic evidence-qualified progress instruction;
- a screenshot-based offline completion critic;
- a prompt-only instruction to read the complete source document;
- an external source-document scrolling gate;
- object-role evidence prompting without first satisfying the frozen prevalence
  and protocol boundaries.

The interventions mostly changed local behavior but did not produce a qualified
task-level gain. In particular, the external coverage gate increased forward
scrolls from 0 to 64 but recovered only 1/8 target objects and found the full set
in 0/3 tasks. Its only bottom attestation was contradicted by six later
same-direction page changes.

Earlier RAVEN-M planner/executor/memory/critic prototypes are useful historical
negative evidence, not a fair current comparator. A heavier controller did not
automatically improve task success, and early all-zero Hard results were not a
clean model-capability baseline.

## 5. Hard eligibility constraints for the selected framework

The winner must satisfy all of the following:

1. Publicly inspectable implementation or enough official code to reproduce the
   core controller without inventing missing behavior.
2. A stable repository and identifiable commit/license.
3. Feasible replacement or adaptation of its foundation model with the frozen
   Qwen3-VL-32B revision.
4. Feasible AndroidWorld integration through screenshot input and the existing
   tap/swipe/type/back/home/answer/terminate action interface.
5. No mandatory proprietary service, unavailable training corpus, or new
   large-scale model training.
6. Broad coverage of the failure vector, not a single-purpose patch.
7. A design whose extra model calls, tokens, actions, and wall-clock cost can be
   measured and fairly reported.
8. Compatibility with non-invasive L0-L5 logging and the native evaluator.
9. A plausible path to one fixed 19-task seed within the remaining summer-camp
   time.

If no framework satisfies all hard constraints, say so and select the closest
feasible one only after explicitly naming the failed constraints and the smallest
faithful adaptation needed.

## 6. Fair comparison that the decision must support

The next official comparison will use one fixed 19-task seed. The existing
official baseline result for that seed is 4/19 and will not be rerun. The public
framework must use the same:

- task instances and parameters;
- Qwen model and revision;
- sampling values;
- native maximum action budgets;
- AndroidWorld reset and evaluator;
- screenshot observation and action coordinate semantics.

Framework-required auxiliary calls are allowed but must be counted. Do not force
call matching if doing so destroys the published algorithm; instead report model
calls, prompt/completion tokens, actions, latency, and success together.

Before the 19-task run, only offline tests, trace replay, a zero-call preflight,
and a non-scoring connectivity smoke are allowed. Freeze the code, prompt,
adapter, model revision, manifest, metrics, contamination boundary, and stop rule
before the first scored generation call. Do not tune on the completed 19-task
result and report it as held-out.

## 7. Required research work

Use current web and primary sources, not memory alone. Audit at least the methods
named in the assignment and prior reviews, including relevant candidates such as
HAR-GUI, LAMO, MobileAgent-V3, PG-Agent, HYMEM, Agent-S2, Mobile-Agent-E,
Agent-SAMA, and strong public state/recovery/verification frameworks discovered
after them. Verify paper claims against official repositories and actual code.

For every serious candidate, distinguish:

- paper-reported capability;
- capability present in released code;
- capability that survives replacing the original model with Qwen3-VL-32B;
- capability that can be measured on our AndroidWorld interface;
- overlap with mechanisms already tested here.

## 8. Required output

Return exactly one Markdown document named conceptually
`PUBLIC_FRAMEWORK_DECISION.md`, containing:

1. a one-paragraph executive decision naming exactly one framework;
2. a candidate table with paper, official repository, license, model dependency,
   training dependency, AndroidWorld evidence, and implementation status;
3. a failure-coverage matrix against all seven observed capability groups;
4. a closest-prior and overlap audit explaining why the winner dominates the
   alternatives for this project;
5. an exact component-by-component adaptation plan to Qwen3-VL-32B and our action
   interface, explicitly separating faithful adaptation from algorithm changes;
6. a list of files/dependencies/weights still required;
7. a zero-call qualification plan and a non-scoring smoke plan;
8. a frozen one-seed 19-task experimental contract with cost accounting;
9. preregistered success, mechanism, failure, and stop gates;
10. the strongest reasons the choice may fail and the evidence that would falsify
    it;
11. a realistic engineering and GPU-time estimate;
12. unresolved information gaps that must be checked before implementation.

Do not design the second public augmentation. Do not design our final method. Do
not claim that the selected framework will improve the score before it is run.
