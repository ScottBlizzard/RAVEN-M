# Top-3 Complete Design Outline Requirements

Date: 2026-08-15

Status: authoritative output-depth requirement for the three Open V2 Pro studies.

The Pro output should be a complete research-design outline: detailed enough that the research team clearly understands the proposed system and can begin implementation planning, but it does not need to be a finished implementation contract.

## Required content

1. **Evidence understanding**
   - Summarize the most relevant repository results and failure patterns.
   - Separate established facts, interpretation, and missing evidence.
   - Explain why the selected problem is worth addressing.

2. **Alternative thinking**
   - Consider several plausible solution directions.
   - Explain why the final recommendation is preferred.
   - The initial critic/planner/verifier idea may be retained, changed, or rejected.

3. **One clear recommended design**
   - Give it a name and one-sentence hypothesis.
   - Explain its essential components and how they interact.
   - State what is inherited from existing work and what is genuinely new.

4. **End-to-end workflow**
   - Describe what happens before, during, and after an executor decision.
   - Explain what information each component can see.
   - Explain when the new component activates and how its output affects the executor.
   - A diagram or ordered workflow is encouraged.

5. **Prompt and state strategy**
   - Provide representative or recommended prompt templates for any new role.
   - Describe the important state or memory objects and their lifecycle.
   - Give reasonable initial budgets, trigger principles, expiry/cooldown ideas, and safety boundaries.
   - Exact production regexes, every schema field, and every threshold do not need to be finalized unless they are central to the scientific hypothesis.

6. **Integration direction**
   - Identify the main repository modules likely to change.
   - Describe the expected controller/component interfaces at a design level.
   - Flag difficult or risky integration points.
   - Do not write multi-file code or exhaustive function-by-function specifications.

7. **Experiment and comparison plan**
   - Define the base system, specialized system, fair active control, and useful ablation.
   - Describe the capability-preservation gate and full-suite progression.
   - Separate accuracy, cost, and component-causality questions.

8. **Evidence and audit plan**
   - State what offline trace audit is needed before implementation.
   - Describe what activation, behavioral change, visible progress, relapse, and final success evidence should be recorded.
   - Identify leakage and attribution risks.

9. **Expected benefits, risks, and falsification**
   - State why the proposal might improve over current systems.
   - Describe likely failure modes and preservation risks.
   - Give clear results that would reject the idea.

10. **Practical next steps**
    - Provide a staged implementation, review, offline validation, and live-test roadmap.
    - List the most important decisions the implementation team still needs to freeze.

## Desired depth

The document should answer the research team's major design questions without pretending that implementation has already been completed. It should avoid both extremes:

- too vague: only a concept name and a few paragraphs;
- too rigid: exhaustive JSON schemas, exact source closures, every function signature, and hundreds of premature test cases.

The target is a rigorous, structured blueprint for discussion and implementation planning. After receiving it, the research team will perform an independent design audit and write the final preregistration/implementation contract.
