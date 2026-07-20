# Master Prompt for GPT Pro

You are acting as a senior faculty mentor, research scientist, and research engineering lead in multimodal large language models (MLLMs), mobile GUI agents, agent memory, and empirical machine learning. Your task is to produce one exceptionally detailed, actionable, and technically rigorous Markdown research plan for the summer-camp assessment described below.

Do not treat this as a generic brainstorming exercise. The plan must be specific enough that a capable undergraduate researcher can execute it without having to redesign the project from scratch.

## 1. Candidate profile and expected level

The candidate is applying for a direct PhD track at Zhejiang University and should not be treated as a research novice.

Relevant background:

- First/co-first author and corresponding author of an accepted IJCAI-ECAI 2026 AI & Health Special Track paper on heterogeneous-teacher knowledge distillation, selective trust, orthogonal feature separation, lightweight deployment, and out-of-distribution medical-image generalization.
- First author of an accepted ACM Multimedia 2026 Main Track paper on open-vocabulary audio-visual event localization, reliability-aware asymmetric distillation, supervision-path separation, orthogonal representation learning, multimodal robustness, cross-dataset transfer, and systematic ablation studies.
- Experienced in problem formulation, model implementation, controlled experiments, ablations, robustness evaluation, qualitative analysis, and academic writing.

Calibrate the project accordingly:

> The target is paper-grade reasoning and experimental rigor, but research-prototype-scale scope.

The final work should be substantially stronger than a beginner-level demo and should demonstrate direct-PhD research potential. However, it does not need to become a submission-ready paper, establish a new state of the art, build a large new benchmark, or exhaustively evaluate every possible model.

The project must first satisfy every requirement in the official assessment. Research ambition must not displace required deliverables.

## 2. Official assessment topic

### Topic

**Memory Management for MLLM-Driven Mobile-Use Agents**

### Motivation

Modern mobile GUI agents can interpret screenshots, locate GUI elements, plan actions, and operate smartphones through actions such as tapping, swiping, typing, going back, and switching applications. They work reasonably well on short tasks but often fail on long-horizon tasks involving many pages, multiple applications, and more than 20 interactions.

Typical failures include:

- forgetting which subtasks have already been completed;
- losing important intermediate variables;
- failing to track the current application or page state;
- repeating actions or entering loops;
- using stale or irrelevant history;
- failing to recover from mistakes;
- prematurely claiming task completion;
- being overwhelmed by long raw trajectories.

The project should investigate explicit memory management and multi-role collaboration for improving long-horizon mobile GUI-agent reliability.

### Mandatory official requirements

The plan must fully cover all of the following:

1. Conduct a literature review of memory mechanisms for GUI Agents, Mobile-Use Agents, and MLLM Agents. The review must classify existing work, explain the core ideas of different memory mechanisms, compare their strengths and weaknesses, and identify the project's research entry point and innovation space.
2. Deploy the AndroidWorld benchmark environment.
3. Build an end-to-end GUI Agent baseline using **Qwen3-VL-32B-Instruct**.
4. Evaluate the baseline primarily on **AndroidWorld Hard tasks** and record task success rate.
5. Design and implement a multi-agent or multi-role framework with explicit memory management. Suggested logical roles include:
   - Planner;
   - Executor;
   - Memory Manager;
   - Reflector/Critic.
6. Study task-history management, state summarization, experience reuse, memory retrieval, multi-round planning, error recovery, and long-term dependency modeling.
7. Evaluate the memory-enhanced system on the same Hard-task protocol and report:
   - task success rate;
   - improvement over the baseline;
   - representative successful cases;
   - representative failed cases;
   - error analysis.
8. If time permits, conduct an optional Medium-task generalization experiment.
9. Deliver complete and reproducible:
   - source code;
   - run scripts;
   - configuration files;
   - environment and execution instructions;
   - experiment logs and results;
   - a system architecture diagram;
   - a complete experimental report;
   - method documentation.

Do not omit or quietly downgrade any mandatory requirement.

## 3. Required source verification

Before producing the plan, browse the web and verify the current official repositories, documentation, model interfaces, benchmark definitions, and paper details. Prefer primary sources only:

- official GitHub repositories;
- official project pages;
- official model documentation;
- arXiv or publisher paper pages;
- the researcher's or laboratory's official publication page.

At minimum, verify and use:

- AndroidWorld repository and paper;
- Qwen3-VL official repository, model card, and mobile-agent prompting example;
- SeeClick;
- HAR-GUI / History-Aware Reasoning for GUI Agents;
- LAMO;
- MobileAgent-V3 or the latest relevant Mobile-Agent version;
- PG-Agent: An Agent Powered by Page Graph;
- HYMEM or the latest available version of the cited self-evolving/hybrid memory work;
- Agent-S2;
- relevant recent GUI-agent memory, episodic reasoning, structured memory, page-graph, trajectory summarization, and process-evaluation work;
- Zhou Sheng and Eagle Lab's recent GUI Agent research, especially PG-Agent, HAR-GUI, and ProBench.

Important verification rules:

- Do not fabricate repository commands, model names, dataset splits, evaluation scripts, or paper conclusions.
- Verify whether "Hard task" is an official AndroidWorld split in the current repository. If it is not formally defined, say so explicitly and propose a reproducible, defensible operational definition or task-selection protocol instead of pretending that an official split exists.
- Verify that the exact Qwen3-VL-32B-Instruct checkpoint and its GUI/mobile-agent interface are currently available. If naming or access has changed, explain the discrepancy and give the closest compliant option while preserving the teacher's requested model whenever possible.
- Put a direct link next to each important source and include an access date.
- Clearly distinguish verified facts from your recommendations.

### 3.1 Mandatory current top-venue literature search

Do not limit the literature review to the papers listed in the assessment. Conduct a new, reproducible, multi-source search covering the literature available **through the date on which you execute this prompt**, with special emphasis on 2025-2026 work. The assessment document may be incomplete or already behind the frontier.

Search at least the following publication channels when relevant:

- NeurIPS, ICML, and ICLR;
- CVPR, ICCV, and ECCV;
- ACL, EMNLP, and NAACL;
- AAAI and IJCAI;
- KDD, The Web Conference (WWW), and SIGIR;
- ACM Multimedia;
- CHI and UIST;
- other top HCI, mobile-computing, software-engineering, or agent venues only when directly relevant;
- arXiv/OpenReview for very recent preprints that have not yet appeared in proceedings.

Use multiple discovery and verification sources rather than one web search:

- DBLP for computer-science venue and author verification;
- OpenReview for ICLR and other OpenReview-hosted venues;
- arXiv for current preprints and version history;
- ACL Anthology for ACL-family papers;
- IEEE/CVF Open Access for CVPR/ICCV papers;
- ACM Digital Library for ACM MM, CHI, UIST, and related ACM venues;
- official AAAI, IJCAI, ICML, NeurIPS, and conference proceedings pages;
- Crossref, OpenAlex, or Semantic Scholar for broad discovery and citation chaining;
- official GitHub repositories and project pages for implementation status.

Search using multiple query families, including combinations and synonyms of:

- "GUI agent memory";
- "mobile GUI agent memory";
- "mobile-use agent long-horizon";
- "MLLM GUI agent history";
- "history-aware GUI agent";
- "episodic memory GUI agent";
- "structured memory mobile agent";
- "hierarchical memory GUI automation";
- "self-evolving memory agent";
- "page graph GUI agent";
- "knowledge graph GUI agent";
- "trajectory compression GUI agent";
- "state summarization GUI agent";
- "reflection error recovery GUI agent";
- "process-aware GUI agent evaluation";
- "AndroidWorld memory";
- "Android agent long-term dependency";
- "OS agent memory";
- "computer-use agent memory";
- "agentic memory multimodal agent";
- "retrieval augmented GUI agent".

Apply backward and forward citation chaining from the closest papers, especially PG-Agent, HAR-GUI, ProBench, MP-GUI, MobileAgent, Agent-S2, and the most recent memory-agent papers found during the search. Inspect papers that cite or are cited by these works when they address memory representation, retrieval, planning, process evaluation, error recovery, or long-horizon interaction.

The search must distinguish:

- formally published or accepted papers;
- workshop papers;
- technical reports;
- arXiv-only preprints;
- repositories or project pages without a corresponding archival paper.

Do not describe an arXiv preprint as a top-conference paper unless its acceptance is verified from an official proceedings, OpenReview, author, or conference source. Record the latest version date and venue status.

Use the following search targets:

- retrieve approximately 25-40 deduplicated candidate papers;
- select approximately 15-25 core papers for detailed comparison;
- prioritize at least 8 highly relevant works from 2025-2026 when available;
- retain older papers only when they are foundational or necessary to explain the evolution of the field.

These counts are guidance, not a reason to include irrelevant work. Relevance and methodological proximity take priority.

For every core paper, record:

- title;
- authors;
- year;
- verified venue/status;
- DOI/arXiv/OpenReview identifier;
- official paper link;
- official code/project link if available;
- task and benchmark;
- base model;
- memory representation;
- memory write/consolidation policy;
- retrieval policy;
- whether memory is short-term, episodic, semantic, procedural, graph-based, or self-evolving;
- whether the method is training-free, fine-tuned, or RL-based;
- main contribution;
- strongest evidence;
- limitations;
- relationship to the proposed project;
- whether it is a baseline, inspiration, overlap risk, or orthogonal work.

### 3.2 Mandatory Zhou Sheng and Eagle Lab publication audit

Perform a dedicated author- and laboratory-centered search for **Sheng Zhou (周晟), Zhejiang University, Eagle Lab / Zhejiang Key Laboratory of Accessible Perception and Intelligent Systems**, carefully disambiguating him from researchers with similar names.

Start from:

- Sheng Zhou's official Zhejiang University profile;
- his official personal publication page;
- Eagle Lab's official website and GitHub organization;
- DBLP, Google Scholar, Semantic Scholar, OpenAlex, or ORCID only as secondary discovery/verification sources.

Search his recent publications by both author name and coauthor network. Pay special attention to work coauthored with Jiajun Bu and the GUI-agent collaborators appearing in PG-Agent, HAR-GUI, ProBench, and MP-GUI.

At minimum, locate, verify, and read the full paper where available for:

- **PG-Agent: An Agent Powered by Page Graph**;
- **History-Aware Reasoning for GUI Agents (HAR-GUI)**;
- **ProBench: Benchmarking GUI Agents with Accurate Process Information**;
- **MP-GUI: Modality Perception with MLLMs for GUI Understanding**;
- any newer 2026 work by Sheng Zhou or Eagle Lab on GUI agents, mobile agents, MLLMs, memory, structured reasoning, process evaluation, accessibility, or graph-based agent knowledge that is available when this prompt is executed.

Do not stop at abstracts. Inspect the method, experiments, ablations, limitations, and future-work sections of the closest papers. For each relevant Sheng Zhou/Eagle Lab paper, explain:

- the exact research problem;
- the central mechanism;
- the benchmark and experimental protocol;
- what has already been solved;
- what remains unresolved;
- what this assessment project can reuse legitimately;
- what would merely reproduce prior work;
- where a clearly differentiated extension is possible;
- how the proposed project aligns with the professor's current research trajectory.

Create a dedicated **Sheng Zhou/Eagle Lab alignment matrix** with columns:

- paper;
- year/venue/status;
- Sheng Zhou's authorship role when verifiable;
- problem;
- method;
- memory/history/graph component;
- benchmark;
- closest overlap with this project;
- reusable asset;
- differentiation requirement;
- concrete design implication.

The final method must be frozen only after this audit. Explicitly show that the proposed contribution is not a superficial reimplementation of PG-Agent or HAR-GUI and does not duplicate ProBench's evaluation contribution.

### 3.3 Reproducible literature-search record

Include a literature-search appendix in the final Markdown plan containing:

- search date;
- database/source;
- exact query string;
- year and venue filters;
- number of results inspected;
- number retained;
- inclusion criteria;
- exclusion criteria;
- deduplication rule;
- citation-chaining procedure;
- unresolved metadata or access limitations.

Produce a recommended artifact list containing:

- `docs/literature_review.md`;
- `docs/literature_search_log.md`;
- `docs/related_work_matrix.md` or `.csv`;
- `docs/sheng_zhou_eaglelab_alignment.md`;
- `references/references.bib`.

The literature search is a required research work package, not optional background reading. Add a go/no-go gate: **the method and experiment matrix must not be frozen until the top-venue search, citation chaining, and Sheng Zhou/Eagle Lab audit are complete**.

## 4. Available computing resources

The candidate can use:

- one NVIDIA GeForce RTX 4090, normally 24 GB VRAM;
- one NVIDIA A40, normally 48 GB VRAM.

Do not assume they have NVLink or that both GPUs are installed in the same machine. Give:

1. a recommended single-machine allocation if both GPUs are locally available;
2. an alternative client-server allocation if the Android emulator and GPUs are on different machines;
3. a fallback plan using only the A40;
4. a fallback plan using only the RTX 4090.

Assess, with current tool support, how to serve Qwen3-VL-32B-Instruct under these memory limits. Compare relevant options such as BF16/FP16, 8-bit, 4-bit, tensor parallelism, CPU offload, vLLM, SGLang, Transformers, or other currently supported serving stacks. Do not recommend a serving stack unless official or highly reliable current documentation supports the required multimodal model.

The core assessment should not depend on expensive fine-tuning or reinforcement learning. Prefer a training-free/test-time memory-management method for the main deliverable. Small learned components or parameter-efficient training may be listed only as optional extensions if they provide clear value.

Assume Linux is preferred for AndroidWorld unless current official documentation supports another environment equally well. State OS, CPU RAM, storage, CUDA, driver, emulator, ADB, and networking requirements explicitly. Explain how the Android environment communicates with a local or remote model server.

## 5. Working research direction to evaluate and refine

Use the following as the initial research direction, but critically evaluate it against current literature before finalizing it:

### Working title

**Reliability-Aware Hierarchical Memory for Long-Horizon Mobile GUI Agents**

### Core insight

Not all memories are equally useful or trustworthy. A GUI agent can be harmed by stale states, incorrect summaries, failed actions, irrelevant episodes, or hallucinated completion records. Memory should therefore be selected and routed according to reliability, relevance, recency, provenance, and verification status rather than appended indiscriminately to the prompt.

### Candidate memory hierarchy

- **Working memory:** the most recent observations, actions, and immediate subgoal.
- **Structured episodic memory:** completed steps, current task state, intermediate variables, page transitions, and action outcomes within the current episode.
- **Semantic/page-graph memory:** reusable page states, GUI elements, action-to-page transitions, and cross-task procedural knowledge.
- **Failure and recovery memory:** failed actions, detected loops, rollback points, corrective actions, and verified recovery strategies.

Each memory item may contain:

- content;
- memory type;
- source observation/action;
- timestamp or step index;
- task/subgoal association;
- application and page identity;
- confidence;
- relevance score;
- recency;
- verification status;
- observed action outcome;
- success/failure label;
- provenance pointer to raw logs or screenshots.

### Candidate reliability-aware routing policy

- high-confidence, verified memory may directly support planning and action selection;
- uncertain memory should be treated only as an auxiliary hypothesis and verified against the current screen before use;
- stale or contradicted memory should be suppressed or revised;
- failure memories should inform recovery and loop avoidance but should not be copied blindly across incompatible applications or states.

### Candidate logical roles

- **Planner:** decomposes the goal, selects the current subgoal, and requests relevant memory.
- **Executor:** observes the current screen and emits the next Android action.
- **Memory Manager:** writes, consolidates, retrieves, updates, invalidates, and scores memory.
- **Reflector/Critic:** checks action outcomes, detects contradictions or loops, verifies completion, and triggers recovery or replanning.

These roles may share one Qwen3-VL-32B-Instruct endpoint with different role prompts. Do not require four separate copies of the model. Explicitly compare the benefits and overhead of logical-role separation versus a single-agent implementation.

### Candidate research questions

- **RQ1:** Does explicit structured memory improve success on long-horizon AndroidWorld tasks compared with no memory, raw full-history prompting, and simple summarization?
- **RQ2:** Which memory components contribute most to task completion, loop avoidance, error recovery, and cross-page/cross-app dependency handling?
- **RQ3:** Does reliability-aware memory routing reduce memory-induced errors compared with relevance-only retrieval or indiscriminate history injection?
- **RQ4 (optional):** Does the method generalize across task difficulty, task length, application category, and alternative base MLLMs?

### Candidate hypotheses

- Structured episodic memory will outperform raw full-history prompting at similar or lower context cost.
- Failure/recovery memory will primarily improve error recovery and reduce repeated-action loops.
- Page-graph or semantic memory will primarily improve navigation and cross-page dependency handling.
- Reliability-aware filtering will reduce stale-memory and false-completion errors compared with relevance-only retrieval.
- Benefits will grow with trajectory length and task complexity.

You may refine, narrow, rename, or partially reject this method if the literature or implementation constraints justify a better choice. If you change it, explain exactly why. Preserve one clear, testable method contribution instead of producing an unfocused collection of Agent modules.

## 6. Scope discipline

The plan must explicitly separate:

- **Must-have compliance layer:** everything required by the teacher.
- **Strong research core:** the smallest set of additional components needed to demonstrate direct-PhD research potential.
- **Optional extensions:** only after the core is complete.
- **Out of scope:** features that should not consume time during the assessment.

The plan must prevent these common failure modes:

- building a large front-end demo that is not required;
- spending most of the schedule on infrastructure without a controlled experiment;
- merely concatenating prompts and calling it a multi-agent method;
- using different prompts, models, step budgets, or task subsets for baseline and proposed method;
- cherry-picking successful tasks;
- changing the method after inspecting test outcomes without documenting the decision;
- reporting only aggregate success rate without explaining mechanisms or failures;
- claiming that memory helps when improvements may be caused by extra context length, more model calls, or a larger inference budget;
- implementing too many memory types without isolating their contributions;
- attempting full RL training before the required training-free prototype works.

## 7. Required output

Return exactly one self-contained Markdown document. Write the document in **Chinese**, but retain canonical English names for models, benchmarks, methods, metrics, repositories, and technical terms. Define abbreviations at first use and use terminology consistently.

Do not ask the user follow-up questions before generating the plan. When information is unknown, make an explicit assumption, explain its impact, and provide a decision checkpoint.

The Markdown document must be detailed, concrete, and operational. Avoid generic advice such as "read papers," "run experiments," or "optimize prompts" without specifying what to read, what to run, what to record, and how to decide whether the step succeeded.

Use clear headings, tables, checklists, Mermaid diagrams, formulas or pseudocode where useful. Commands and configuration examples must be labeled as either verified or schematic.

## 8. Mandatory structure of the Markdown plan

### 0. Document metadata

Include:

- project title;
- candidate level;
- target standard;
- assumed project duration;
- hardware;
- core benchmark and model;
- document version and date;
- a short terminology ledger.

### 1. Executive summary

Explain in plain Chinese:

- what problem is being solved;
- why current GUI agents fail;
- what the proposed method changes;
- what the minimum successful outcome looks like;
- what a strong final result looks like.

Give one recommended project direction, not a list of disconnected possibilities.

### 2. Official-requirement traceability matrix

Create a table with:

- official requirement;
- implementation work package;
- evidence of completion;
- final artifact/file;
- acceptance criterion;
- priority;
- risk if omitted.

Every official requirement must appear exactly once or be explicitly cross-referenced.

### 3. Scope and completion standard

Define:

- minimum compliant submission;
- recommended strong submission;
- optional publication-oriented extensions;
- explicit out-of-scope items;
- stop conditions that prevent uncontrolled expansion.

### 4. Research problem formulation

Provide:

- precise problem statement;
- definitions of state, observation, action, trajectory, task, subgoal, memory item, memory write, consolidation, retrieval, invalidation, and verification;
- research questions;
- falsifiable hypotheses;
- expected contribution;
- explicit non-claims;
- a claim-evidence matrix showing which experiment supports each intended claim.

### 5. Literature-review plan and taxonomy

Create a literature taxonomy covering at least:

- end-to-end GUI Agents;
- single-agent history prompting;
- trajectory compression and state summarization;
- episodic, semantic, procedural, and working memory;
- vector/RAG memory;
- graph-structured or Page Graph memory;
- self-reflection and error-recovery memory;
- multi-agent memory management;
- self-evolving memory;
- GUI-agent benchmarks and process-aware evaluation.

For each category, specify:

- representative papers;
- central idea;
- memory representation;
- write policy;
- retrieval policy;
- whether it is trained or training-free;
- evaluated benchmarks;
- strengths;
- weaknesses;
- relationship to this project.

End with:

- the reproducible multi-source search log;
- a deduplicated recent-top-venue paper table;
- a full Sheng Zhou/Eagle Lab alignment matrix;
- a concrete gap statement;
- a novelty/overlap risk map;
- an explicit explanation of how the proposed work differs from PG-Agent, HAR-GUI, ProBench, MP-GUI, and the closest 2025-2026 memory-agent papers;
- a "method changes caused by the literature audit" subsection explaining which parts of the initial idea were retained, revised, or rejected after reading the latest work.

### 6. Benchmark and task protocol

Explain:

- verified AndroidWorld version and repository state;
- environment architecture;
- task reset and reproducibility;
- exact meaning or operational definition of Hard tasks;
- task inclusion/exclusion rules;
- how many tasks to use and why;
- whether to run the full set or a fixed representative subset;
- task-length and category stratification;
- random seed and repeated-trial policy;
- maximum-step budget;
- completion criteria;
- handling of emulator crashes and invalid runs;
- prevention of task leakage and prompt overfitting;
- optional Medium-task protocol.

Provide a frozen task-manifest schema and a run-log schema.

### 7. Qwen3-VL baseline

Specify:

- verified model/checkpoint;
- serving stack;
- quantization and context-window recommendation;
- GPU placement;
- screenshot preprocessing;
- action space;
- prompt structure;
- observation/action loop;
- history policy;
- completion signal;
- retry and timeout behavior;
- token and latency logging;
- baseline variants needed to separate memory effects from compute-budget effects.

At minimum distinguish:

1. current-screen-only or minimal-history baseline;
2. sliding-window baseline;
3. raw full-history baseline;
4. simple LLM-summary baseline.

Explain how all methods will be matched for model, task set, action budget, temperature, and allowed model-call budget.

### 8. Proposed system architecture

Give:

- one overall Mermaid architecture diagram;
- one per-step sequence diagram;
- module responsibilities;
- data flow;
- memory write/retrieve/update/invalidate lifecycle;
- planner-executor-memory-critic interaction;
- completion verification;
- loop detection;
- rollback/recovery policy;
- model-call accounting.

Clearly distinguish:

- logical agents;
- model instances;
- deterministic controller code;
- LLM/VLM calls;
- AndroidWorld environment;
- persistent storage;
- experiment logger.

### 9. Memory design specification

Provide:

- exact memory types selected for the core;
- memory-item JSON examples;
- task-state schema;
- page-state schema;
- failure-memory schema;
- page-graph node/edge schema if used;
- write triggers;
- consolidation triggers;
- retrieval query construction;
- retrieval scoring;
- reliability scoring;
- contradiction detection;
- stale-memory handling;
- capacity limits;
- deletion or archival policy;
- provenance and screenshot linkage.

Give an implementable retrieval/routing formula or pseudocode. Separate heuristic components from learned components. Explain all hyperparameters and how they will be chosen without test-set tuning.

### 10. Experiment matrix

Create a prioritized experiment table containing:

- experiment ID;
- research question;
- system variant;
- task subset;
- number of repetitions;
- controlled variables;
- metrics;
- expected observation;
- interpretation if the result is positive;
- interpretation if the result is negative;
- approximate compute/time cost;
- Must/Should/Optional label.

Include at least:

- required baseline versus full method;
- raw history versus summary versus structured memory;
- relevance-only versus reliability-aware retrieval;
- working-memory ablation;
- episodic-memory ablation;
- failure/recovery-memory ablation;
- page-graph/semantic-memory ablation if included in the core;
- critic/completion-verification ablation;
- context-budget-matched comparison;
- model-call-budget-matched comparison;
- task-length stratification;
- representative successful and failed trajectories;
- optional Medium-task generalization;
- optional alternative-model transfer only if time permits.

### 11. Metrics and statistical analysis

Define exact calculations for:

- task success rate;
- absolute improvement;
- relative improvement;
- confidence intervals;
- paired significance testing or paired bootstrap;
- average and median steps;
- valid-action rate;
- repeated-action or loop rate;
- error-recovery rate;
- premature-completion rate;
- memory retrieval precision or utility;
- stale/contradictory-memory usage rate;
- token consumption;
- number of model calls;
- wall-clock latency;
- peak GPU memory;
- cost-normalized success.

State which metrics are primary, secondary, and diagnostic. Explain how to avoid overstating small improvements.

### 12. Failure taxonomy and qualitative analysis

Define a coding scheme for at least:

- perception/grounding failure;
- action-format or execution failure;
- planning failure;
- forgotten subgoal;
- forgotten intermediate variable;
- stale state;
- irrelevant retrieval;
- incorrect memory;
- memory contradiction;
- repeated-action loop;
- failed recovery;
- premature completion;
- environment/infrastructure failure.

Explain:

- how trajectories will be annotated;
- how many cases to inspect;
- how to distinguish reasoning failure from environment failure;
- how to select representative cases without cherry-picking;
- how to present screenshot-action-memory timelines in the report.

### 13. Implementation roadmap

Provide:

- recommended repository structure;
- module/file responsibilities;
- configuration strategy;
- experiment naming convention;
- seed management;
- checkpoint and cache management;
- logging format;
- screenshot/trajectory storage;
- result aggregation;
- test strategy;
- reproducibility checklist;
- minimal continuous-integration or smoke-test plan.

Do not write the entire implementation. Provide interfaces, pseudocode, and file-level responsibilities sufficient to begin coding.

### 14. Hardware and deployment plan

Give a concrete allocation for:

- A40;
- RTX 4090;
- Android emulator;
- Qwen3-VL server;
- embedding/retrieval components;
- concurrent experiment workers;
- storage and logs.

Include:

- expected VRAM pressure points;
- safe quantization choices;
- context-length trade-offs;
- whether tensor parallelism is practical;
- networking layout for remote model serving;
- fallback if the 4090 and A40 cannot be used together;
- monitoring commands and failure symptoms;
- reproducibility implications of changing inference backends.

### 15. Timeline

Provide two schedules:

1. a recommended **28-day plan**;
2. a compressed **14-day contingency plan**.

For each day or tightly grouped set of days, specify:

- objective;
- concrete tasks;
- required output;
- validation gate;
- dependency;
- fallback if blocked.

The order must prioritize:

1. requirement verification;
2. environment smoke test;
3. baseline;
4. frozen evaluation protocol;
5. minimal memory method;
6. full method;
7. ablations;
8. report and reproducibility.

Do not postpone report writing and logging until the final day.

### 16. Milestones and go/no-go gates

Define measurable gates such as:

- AndroidWorld task can be reset and completed manually;
- one scripted agent trajectory executes end to end;
- Qwen3-VL produces valid actions at an acceptable rate;
- baseline results are reproducible;
- memory writes and retrievals can be inspected;
- full method completes a smoke-test subset;
- experiment protocol is frozen;
- required comparisons are finished;
- all teacher requirements are traceable to artifacts.

Give a fallback action for every failed gate.

### 17. Risk register

Create a table covering:

- Android emulator instability;
- benchmark-version mismatch;
- lack of an official Hard split;
- Qwen checkpoint or serving incompatibility;
- VRAM/context overflow;
- slow sequential evaluation;
- task nondeterminism;
- invalid action formats;
- unreliable automatic evaluators;
- memory hallucination;
- stale memory;
- confounding from extra model calls;
- insufficient sample size;
- no performance gain;
- excessive scope;
- report/reproducibility debt.

For each risk give probability, impact, early warning, mitigation, and fallback.

### 18. Final deliverables

Provide an exact deliverable checklist with proposed filenames and completion criteria, including:

- literature review;
- reproducible literature-search log;
- deduplicated related-work matrix;
- Sheng Zhou/Eagle Lab publication-alignment matrix;
- verified BibTeX bibliography;
- environment guide;
- baseline implementation;
- memory-enhanced implementation;
- experiment configs;
- frozen task manifest;
- raw logs;
- aggregated results;
- success/failure cases;
- architecture diagram;
- experimental report;
- reproducibility instructions;
- final presentation material if useful.

Explicitly map the checklist back to the official assessment.

### 19. Experimental report outline

Provide a report structure resembling a strong research paper while remaining appropriate for a summer-camp assessment:

- Abstract;
- Introduction;
- Related Work;
- Problem Formulation;
- Method;
- Experimental Setup;
- Main Results;
- Ablation Studies;
- Efficiency Analysis;
- Case Study and Error Analysis;
- Limitations;
- Conclusion;
- Reproducibility Statement.

For every section, state what evidence, figures, and tables should appear there.

### 20. First 72 hours

End with an extremely concrete first-72-hour checklist:

- exact top-venue, repository, and proceedings sources to verify;
- exact literature-search queries to run;
- a first-pass deduplicated paper inventory;
- full-text reading of PG-Agent, HAR-GUI, ProBench, and MP-GUI;
- an initial Sheng Zhou/Eagle Lab alignment matrix;
- a method-overlap and novelty-risk checkpoint;
- repositories to clone;
- environment tests;
- one AndroidWorld manual task;
- one model-serving smoke test;
- one screenshot-to-action test;
- one end-to-end baseline trajectory;
- files and logs that must exist after 72 hours;
- decision points that determine the next step.

### 21. Final compliance audit

Finish the Markdown document with:

- a one-page compliance checklist;
- a "definition of done";
- a list of unresolved assumptions;
- decisions that genuinely require mentor confirmation;
- the top five actions that most improve the probability of a strong assessment.

## 9. Quality requirements

The final plan must:

- be internally consistent;
- recommend one coherent main method;
- remain executable with the stated hardware;
- distinguish mandatory, recommended, and optional work;
- contain no fabricated facts;
- use citations near relevant claims;
- include concrete acceptance criteria;
- include negative-result interpretations and fallbacks;
- emphasize fair comparisons and reproducibility;
- preserve a manageable scope;
- demonstrate research maturity without pretending that a complete publishable paper is required.

Do not end with vague encouragement. End with the compliance audit and prioritized actions requested above.
