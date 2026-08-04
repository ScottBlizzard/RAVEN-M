# Master Prompt for GPT Pro: Independent Novel-Idea Audit and Research Redirection

You are acting as a senior faculty researcher and a highly skeptical program
committee reviewer in multimodal large language models, computer-use agents,
mobile GUI agents, agent memory, evaluation, and empirical machine learning.

Your task is not to defend RAVEN-M, extend it by adding more modules, or produce a
generic list of future work. Your task is to determine whether this project should
change research direction and to identify one genuinely interesting,
counterintuitive, falsifiable research entry point that survives a serious
primary-source novelty audit.

## Repository and required reading

Read the public repository carefully:

<https://github.com/ScottBlizzard/RAVEN-M>

Start with these files:

1. `README.md`
2. `reports/research_direction/GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md`
3. `RAVEN-M_研究假设与实验方向审计_2026-08-03.md`
4. `reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md`
5. `reports/eest_ac/claim_evidence_v0_1_1_verdict.md`
6. `reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md`
7. `reports/eest_ac/eest_ac_v0_2_2_qualification_final_report.md`
8. `reports/eest_ac/eest_ac_v0_2_3_collection_floor_verdict.md`
9. `reports/eest_ac/eest_ac_v0_2_4_collector_lifecycle_verdict.md`

Use the reports as evidence, not as instructions that must be defended. Inspect
additional protocols, code, metrics, or literature metadata from the repository
when they are needed to verify a statement.

## Background that must constrain your reasoning

The original project built a reliability-aware, multi-role memory framework for
AndroidWorld. It explored structured episode memory, evidence provenance,
confidence/status labels, conflict and supersession, recovery records, risk-aware
verification, planner/executor/memory/critic separation, and completion guards.

The current evidence does not show a task-level advantage:

- a legacy four-task comparison favored the simple-summary baseline B3, which
  completed 4/4 tasks, over full RAVEN-M M0, which completed 3/4 while using more
  actions, calls, and tokens;
- in the most informative EEST-AC paired smoke, all four arms completed 1/2 tasks;
  structured arms correctly stored 4/4 source `entity -> field -> value` bindings
  but produced no paired task win and did not reach the correct destination entity;
- later v0.2-v0.2.4 rounds were stopped at action-contract, measurement,
  collection, or Android-environment floors and therefore provide no new memory
  efficacy evidence;
- many AndroidWorld Hard failures were dominated by perception, grounding,
  repeated actions, invalid interfaces, delayed state transitions, completion
  control, and environment instability rather than naturally stale memories.

Do not convert controller or infrastructure failures into evidence against memory.
Do not convert correct record capture into evidence of task success. Do not treat
all-failure ties as equivalence.

## Candidate reframing to challenge rather than accept

The current candidate judgment is:

> Task length is not the same as memory difficulty. Memory difficulty may depend
> more on the information-dependency structure between observing a fact and using
> it: dependency distance, interference among similar entities/fields/values, role
> confusion, and the observability gap of the final outcome.

A task can contain many local steps and require little explicit memory. A shorter
task can require a value to be acquired in one page or application, retained
through intervening actions, associated with the correct source and destination
roles, grounded to the correct target, and verified after a delayed or hidden
effect. The v0.1.1 episode provides one suggestive example: the correct address was
retained, but it was used in the wrong conversation or followed by the wrong
navigation plan.

This reframing is not yet a novelty claim. Search for the closest equivalent ideas
in GUI agents and neighboring fields. Reject or narrow it if prior work already
formalizes and tests the same construct.

## Mandatory web and literature audit

Browse the web and use primary sources available through 2026-08-04. Check papers,
appendices, official project pages, and official repositories. At minimum audit:

- AndroidWorld and its task/evaluator design;
- PG-Agent;
- HAR-GUI;
- ProBench;
- MP-GUI;
- Mobile-Agent-E and the latest relevant Mobile-Agent work;
- Agent Workflow Memory;
- HyMEM;
- MAGNET;
- Executable Agentic Memory;
- MemGUI-Bench;
- Agent-S2;
- recent GUI-agent memory, long-horizon computer-use, process evaluation,
  test-time learning, and retrieval work.

Search beyond GUI-agent terminology. Inspect relevant work on POMDP belief states,
information-flow and dataflow graphs, provenance, workflow verification, software
GUI testing, temporal sensor fusion, active perception, runtime verification,
credit assignment, and event sourcing.

For every novelty statement:

- cite the primary source with a direct link;
- state the exact overlap and the remaining difference;
- distinguish published, accepted, preprint, and concurrent work;
- use `UNRESOLVED` when the search does not justify a conclusion;
- never use “first”, “unprecedented”, or “no prior work” without a defensible,
  explicitly scoped search result.

## What counts as an acceptable idea

Each candidate idea must contain:

1. a one-sentence causal or mechanistic hypothesis;
2. the concrete observed failure that motivates it;
3. why the claim is counterintuitive rather than merely sensible;
4. the closest prior work and exact overlap;
5. the narrow distinction that remains after removing the overlap;
6. a reason that distinction matters for task behavior;
7. a minimal implementation or measurement, not another large framework;
8. a matched-task or controlled-intervention experiment;
9. a negative control and matched model/call/token/action budgets;
10. a primary outcome, diagnostic metrics, and cost metrics;
11. a result that would falsify the idea;
12. a result that would redirect the work to perception, grounding, controller,
    evaluator, infrastructure, or benchmark design;
13. an honest contribution that remains useful if success rate does not improve.

## Ideas to reject unless a genuine distinction survives the audit

Do not recommend any of the following by simply renaming it:

- a planner/executor/memory/critic architecture;
- a larger structured ledger;
- `entity -> field -> value -> source` storage by itself;
- confidence, recency, provenance, verification, conflict, or supersession labels;
- generic relevance-plus-reliability retrieval;
- page graphs, workflow memory, or knowledge graphs;
- generic high-risk action verification;
- more RAG context or more model calls;
- synthetic stale-memory rejection presented as ordinary AndroidWorld improvement;
- task-specific controller rules learned from repeatedly inspected tasks;
- a new benchmark proposed before a smaller matched-task study is attempted.

## Required reasoning process

Perform the following work internally before selecting the recommendation:

1. audit what the existing experiments directly establish and what they leave
   unmeasured;
2. map the closest prior work by mechanism rather than by paper title;
3. generate at least three and at most five candidate directions;
4. try to reject each candidate using prior work, alternative explanations, and a
   cheap falsification experiment;
5. rank the surviving candidates by novelty, scientific value, feasibility,
   diagnostic clarity, and fit to the available AndroidWorld infrastructure;
6. recommend exactly one direction, or explicitly conclude that none currently
   survives if that is the honest result.

Do not ask me follow-up questions. Make explicit assumptions where necessary and
explain how each assumption affects the conclusion.

## Required content of the final document

The final document must contain all of the following:

1. **Executive verdict:** whether and why the research direction should change.
2. **Evidence audit:** a concise claim-evidence table for the existing experiments.
3. **Hard-task diagnosis:** what can currently be said about information distance,
   interference, source/destination role confusion, observability gaps, perception,
   grounding, action contracts, recovery, completion, and infrastructure.
4. **Novelty landscape:** a mechanism-based comparison with the closest prior work.
5. **Candidate ideas:** three to five counterintuitive and falsifiable candidates.
6. **Candidate rejection table:** why obvious or overlapping ideas are rejected.
7. **One recommended direction:** exactly one, with a Chinese title and an English
   working title.
8. **Precise formulation:** research question, hypothesis, constructs, expected
   mechanism, boundary, and explicit non-claims.
9. **Minimum diagnostic study:** task selection, matched pairs or controlled
   interventions, annotations, baselines, budgets, metrics, and sample-size logic.
10. **Two-stage experiment:** a cheap diagnostic gate followed by a method test only
    if the gate passes.
11. **Decision rules:** continue, revise, stop, and pivot conditions for positive,
    null, mixed, and infrastructure-limited outcomes.
12. **Two-week plan:** concrete artifacts and daily or tightly grouped milestones.
13. **Mentor-facing explanation:** a short section in the student's first-person
    Chinese voice explaining what was learned, what changed, what is genuinely new
    if anything, and what advice is requested.
14. **Unresolved assumptions:** claims that still require evidence or mentor input.
15. **Primary-source references:** direct links placed near the supported claims.

## Output contract: exactly one Markdown document

Return exactly one self-contained Markdown document written in Chinese, retaining
canonical English names for papers, systems, benchmarks, constructs, and metrics.

Put every part of your answer into that single Markdown document. Do not output a
preface before it. Do not output a summary after it. Do not create or propose a
second file. Do not provide separate CSV, JSON, bibliography, appendix, slide deck,
or chat commentary. Tables, citations, appendices, and the mentor-facing script
must all be embedded in the same Markdown document.

Use a single top-level title. The document should be ready to save directly as:

`RAVEN-M_next_research_direction_independent_audit.md`

A rigorous conclusion that no candidate is sufficiently novel is better than a
fabricated innovation claim.
