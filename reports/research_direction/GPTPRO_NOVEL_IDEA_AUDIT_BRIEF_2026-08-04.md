# Independent Novel-Idea Audit Brief for the Next RAVEN-M Research Direction

- **Date:** 2026-08-04
- **Purpose:** external deep-research review by GPT Pro or a senior researcher
- **Required stance:** search for a better research question, not a more elaborate defense of the current framework
- **Evidence policy:** distinguish direct evidence, inference, and untested hypotheses

## 1. The decision that this audit must support

The project needs to decide what to study next after a long sequence of
AndroidWorld experiments and controller diagnostics. The old direction treated
memory reliability, stale memories, conflict, verification, suppression, and
multi-role control as one large problem. That direction produced an auditable
system, but it has not produced a task-level advantage over a strong simple
summary baseline.

The audit should identify one small, interesting, falsifiable research question
that is:

1. grounded in a recurring failure mechanism in real GUI-agent tasks;
2. meaningfully different from existing structured, episodic, procedural,
   graph-based, retrieval, and self-evolving memory work;
3. testable with a small controlled study before a large implementation;
4. robust to compute-, prompt-, call-, and task-selection confounds;
5. useful even if the first experiment is negative.

The desired outcome is not a list of fashionable modules. It is one recommended
research direction with a clear causal hypothesis and a decisive minimum test.

## 2. What RAVEN-M did, in plain terms

RAVEN-M gave a mobile GUI agent a more explicit notebook, a dispatcher, and a
checker. It decomposed a task, stored page transitions and task facts, retrieved
possibly relevant memories, checked proposed actions, and attempted to distinguish
verified facts from hypotheses, alerts, or suppressed memories. It also explored
stale-memory handling, conflict, supersession, recovery, and completion checks.

For a contact-creation task, the intended loop was roughly:

1. decompose the task into finding the entry point, filling required fields,
   saving, and verifying;
2. observe the current screen and select an action;
3. record the action, state transition, extracted values, and pending goals;
4. retrieve relevant records for the next decision;
5. block unsupported requirements or insufficiently supported completion claims;
6. update or suppress old records when stronger evidence arrives.

This architecture is understandable, but it bundled together several questions
that may require different benchmarks and different evidence.

## 3. What has actually been observed

### 3.1 Legacy evidence before EEST-AC

In a four-task non-Hard paired comparison, the simple-summary baseline B3
completed 4/4 tasks, whereas the full RAVEN-M M0 completed 3/4. M0 also used more
actions, model calls, prompt tokens, and completion tokens. In the failed contact
task, the guard correctly rejected an invented `Company` field, but the controller
did not recover to the valid `Save` path. The local guard decision was defensible;
the task-level effect was still negative.

The frozen Hard breadth run was dominated by low-level failures. Supported cells
had only 1 success in 80. Repeated actions, unchanged screens, unsupported answer
paths, long contexts, controller loops, and completion deadlocks were common.
RAVEN-M used more calls, tokens, and wall time than B3. This run cannot isolate a
memory effect because the shared agent was near the controller floor.

### 3.2 EEST-AC v0.1.1: the most informative live mechanism signal

The minimum paired smoke contained two tasks and four arms, for eight cells. All
four arms completed 1/2 tasks: the negative control succeeded and the positive
cross-page SMS task failed. M-SLOTS had zero net paired wins over B3-MATCH, so the
pre-registered expansion criterion failed.

The positive signal was narrow but real. M-SLOTS and M-RISK admitted four records,
and all four correctly preserved the source binding:

`Petar Muller -> event_address -> 968 Spruce St, Hartford, CT, 06103`

However, neither arm navigated to the required destination entity, Gabriel
Fernandez. B3 and B3-MATCH retained the correct address but sent or attempted to
send it in the source conversation. The structured arms stored the correct source
fact but executed the wrong navigation plan. This separates three layers that
must not be collapsed:

1. fact capture;
2. retention and entity-role binding;
3. destination-correct action and task completion.

The same smoke also exposed delayed UI transitions misclassified as no-effect,
incorrect grounding, duplicated evidence that exceeded a 256-token response
budget, and weak completion control. These were shared controller defects rather
than evidence that memory alone was the dominant bottleneck.

### 3.3 v0.2 to v0.2.4: why later rounds are not efficacy evidence

- **v0.2 blind smoke:** all nine cells stopped before any environment action
  because model action forms did not cross the frozen schema/adapter boundary.
- **v0.2.1:** the first real-model swipe decision still failed the complete
  decision schema because an `intent` string exceeded a 24-character limit.
- **v0.2.2:** all three actions became schema-valid and executable, but one of
  three failed an exact terminal-pixel agreement rule even though semantic state
  had stabilized. This showed a measurement-contract problem.
- **v0.2.3:** the action-conditioned outcome oracle had offline directional
  signals, but the collection qualification did not produce a valid completed
  held-out trace corpus.
- **v0.2.4:** AndroidEnv initialization failed because the booted device exposed no
  Android `settings` service. Readiness, intended actions, and post observations
  were all zero.

These rounds improved auditability and localized failure layers. They provide no
new task-level evidence for M-SLOTS, M-RISK, RAVEN-M, or memory efficacy.

## 4. What must not be claimed

The existing evidence does not establish that:

- RAVEN-M improves AndroidWorld success;
- structured memory improves success, despite the valid capture signal;
- stale or conflicting memories are a frequent natural AndroidWorld failure;
- action-conditioned verification reduces task errors;
- a graph, ledger, confidence score, or multi-role architecture is novel by
  itself;
- repeatedly debugged tasks demonstrate out-of-domain generalization;
- all-failure ties show two methods are equivalent;
- controller and infrastructure failures count as negative memory results.

## 5. Why “structured memory” is not an adequate new contribution

The novelty audit must directly compare against at least the following nearby
families and their latest versions:

- page and transition graphs, including PG-Agent;
- reusable workflow induction, including Agent Workflow Memory;
- hybrid graph/trajectory memory, including HyMEM;
- stationary and procedural memory, including MAGNET;
- executable knowledge-graph memory, including Executable Agentic Memory;
- history-aware reasoning, including HAR-GUI;
- procedural tips and shortcuts from success and failure, including
  Mobile-Agent-E;
- memory-focused GUI benchmarks, including MemGUI-Bench;
- process-aware GUI evaluation, including ProBench;
- relevant RAG, agent-memory, test-time learning, and computer-use-agent work
  published or posted through 2026-08-04.

An `entity -> field -> value -> source` record is useful engineering, but it is not
new merely because it is smaller than earlier memory systems. Reliability scores,
provenance, recency, confidence, conflict resolution, critic roles, and risk gates
also have broad prior art. The audit must reject proposals that only rename these
elements.

## 6. Candidate empirical reframing to challenge

The current candidate judgment is:

> Task length is not the same as memory difficulty. Memory difficulty may be
> determined more directly by the information-dependency structure between
> observing a fact and using it.

This judgment has three candidate dimensions:

### 6.1 Information-dependency distance

Count or model the operations, distinct pages, application switches, intervening
subgoals, and elapsed interaction time between acquiring a task-relevant fact and
using it. A 20-step task in which every decision is local may require less memory
than a six-step task that transfers one value across applications.

### 6.2 Interference and role permutation

Measure how many similar entities, fields, values, rows, conversations, or input
targets compete during the dependency interval. The v0.1.1 failure suggests a
possible role-permutation error: the agent preserved the correct value but applied
it to the wrong destination entity. More memory may even make such an error more
confident if the source/destination roles are not maintained.

### 6.3 Outcome-observability gap

Measure how far the evidence for task completion is from the final action. A tap
may visibly enter a form, while successful database mutation may require returning
to a list, reopening a detail page, or consulting the benchmark evaluator. A
method that improves fact retention can still fail because completion is only
weakly observable.

These dimensions are not yet validated constructs. GPT Pro should search for the
closest prior formulations in partially observable control, program synthesis,
workflow reasoning, information-flow graphs, GUI testing, long-horizon agents,
and memory benchmarks. If the same construct has already been formalized, the
audit must say so and either narrow the distinction or reject the direction.

## 7. A task-level information chain

For each usable trajectory, consider the chain:

`acquire evidence -> bind entity/role/field -> retain across state changes -> retrieve at the decision -> ground the destination -> execute -> observe the effect -> verify the postcondition`

The proposed analysis should identify the first broken edge, not merely label the
whole episode a memory failure. Candidate annotations include:

- dependency distance in actions, pages, and applications;
- number and similarity of competing entities/fields/values;
- source and destination role identity;
- whether current screenshots, OCR, accessibility trees, and action feedback are
  temporally synchronized;
- whether the effect is immediate, delayed, hidden, or evaluator-only;
- whether failure occurs before capture, after correct capture, during retrieval,
  during grounding, during action execution, or during completion verification.

This analysis may show that the memory framing is wrong. That is an acceptable and
useful outcome.

## 8. Counterintuitive possibilities worth testing, not accepting

The following are prompts for criticism, not final contributions:

1. **Dependency topology may matter more than trajectory length.** Step count may
   be a poor proxy for memory demand after controlling for controller difficulty.
2. **More accurate memory may increase wrong-action confidence.** A perfectly
   retained value can strengthen an action toward the wrong entity if role binding
   or destination grounding is wrong.
3. **The hardest memory problem may occur after the final action.** Postcondition
   evidence and delayed effects may dominate fact retention in some task classes.
4. **More modalities can reduce reliability when they describe different moments.**
   A screenshot, OCR result, accessibility tree, and action-effect record can each
   be locally correct but jointly inconsistent because of temporal skew.
5. **Memory benefit may have a threshold rather than a monotonic relation to task
   length.** Below a dependency/interference threshold, memory adds an attention
   and latency tax; above it, explicit binding may become useful.

GPT Pro must determine whether these ideas are already known, whether they are
actually counterintuitive, and whether existing evidence can discriminate among
them. It should not preserve them merely because they came from this brief.

## 9. Minimum standard for a proposed new idea

Every proposed idea must include all of the following:

1. a one-sentence causal or mechanistic hypothesis;
2. the specific observed failure that motivates it;
3. the closest prior work and exact overlap;
4. the remaining difference after the overlap is removed;
5. an explicit reason the difference matters;
6. a minimal implementation that does not require another large framework;
7. a matched-task or controlled-intervention experiment;
8. a negative control;
9. a primary metric and cost metric;
10. a result that would falsify the idea;
11. a result that would redirect the work to perception, grounding, controller,
    measurement, or benchmark design instead;
12. a scope that can produce a meaningful summer-camp result even without a
    positive success-rate gain.

## 10. Ideas that should be rejected unless a real distinction is found

- another four-role planner/executor/memory/critic architecture;
- storing more fields in a structured ledger;
- attaching confidence, recency, provenance, or verification labels without a new
  testable mechanism;
- generic relevance-plus-reliability retrieval;
- a page graph or workflow memory under a new name;
- calling the verifier only on high-risk actions without defining a new and
  evidence-backed risk construct;
- injecting synthetic stale memories and reporting rejection accuracy as ordinary
  AndroidWorld task improvement;
- adding task-specific rules after repeatedly observing the same tasks;
- increasing calls or context without a matched-compute baseline;
- proposing a new benchmark before showing that existing traces cannot answer the
  smaller question.

## 11. Required literature and novelty audit

Use web search and primary sources. Cover work available through 2026-08-04. For
each candidate direction:

- search exact and neighboring terminology rather than only the proposed name;
- inspect papers, appendices, and official repositories where available;
- distinguish published, accepted, preprint, and concurrent work;
- quote no marketing claims without checking the paper's experiment;
- state whether the proposed distinction is new, a combination of known ideas, an
  application-specific adaptation, or not novel;
- provide direct links and a compact comparison table;
- mark novelty as `UNRESOLVED` when the search is insufficient.

The audit should search beyond GUI-agent memory. Relevant neighboring fields may
include POMDP belief-state representations, dataflow and provenance, workflow
verification, software GUI testing, active perception, temporal sensor fusion,
credit assignment, event sourcing, and runtime verification.

## 12. Required final recommendation

GPT Pro should first generate and stress-test several candidate ideas internally,
then recommend exactly one. The chosen direction should include:

- a short Chinese title and an English working title;
- the surprising observation;
- the research question;
- the falsifiable hypothesis;
- the closest three to six prior works;
- the narrow novelty claim that survives comparison;
- the minimum diagnostic dataset or task subset;
- the minimum method or measurement needed;
- baselines and matched budgets;
- metrics and failure annotations;
- a two-stage experiment, beginning with a cheap diagnostic gate;
- decision rules for continue, revise, or stop;
- a two-week execution plan;
- what can honestly be told to the mentor before the hypothesis is validated.

## 13. Output contract for GPT Pro

Return exactly one self-contained Markdown document in Chinese, retaining
canonical English names for papers, systems, datasets, and metrics. Put every
part of the response inside that one document. Do not provide a separate chat
summary, preface, appendix file, CSV, JSON, or second document.

The document must contain:

1. an executive verdict on whether the project should change direction;
2. an evidence-grounded diagnosis of the existing experiments;
3. a novelty map of the nearest prior work;
4. three to five candidate ideas, each stress-tested and falsifiable;
5. a rejection table explaining why obvious ideas are not novel enough;
6. exactly one final recommended direction;
7. a minimal experiment and matched controls;
8. negative-result interpretations and stop rules;
9. a two-week implementation and evaluation schedule;
10. a mentor-facing explanation in the student's first-person voice;
11. a final section listing unresolved assumptions and claims that still require
    evidence.

Do not claim that an idea is unprecedented unless the primary-source novelty
search supports that statement. A rigorous conclusion that none of the candidate
ideas is sufficiently novel is preferable to a fabricated innovation claim.
