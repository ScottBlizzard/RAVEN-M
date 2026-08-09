# PUBLIC_FRAMEWORK_DECISION.md

## 1. Decision record

| Field | Frozen value |
|---|---|
| Decision | **Select MadeAgents MobileUse MultiAgent, using its current official AndroidWorld template and only its hierarchical-reflection core** |
| Selected public framework | **MadeAgents MobileUse** |
| Selected upstream configuration | `MobileUseMultiAgent` AndroidWorld template |
| Frozen target model | `Qwen/Qwen3-VL-32B-Instruct` |
| Model revision | `0cfaf48183f594c314753d30a4c4974bc75f3ccb` |
| Target benchmark | Frozen 19-task AndroidWorld Hard first-seed suite |
| Experiment seed | `20260806` |
| Baseline reference | Existing frozen first-seed result: **4/19 full successes**, total reward **4.5** |
| Decision type | First public-framework reproduction and adaptation |
| Decision status | **FINAL** |
| Alternative frameworks allowed in this arm | **None** |
| New original RAVEN-M method allowed | **None** |
| Post-start scientific tuning allowed | **None** |

## 2. Unambiguous winner

The first public framework to reproduce and adapt is:

> **MadeAgents MobileUse MultiAgent, restricted to the released AndroidWorld template’s hierarchical-reflection core: `Operator`, `AnswerAgent`, `Reflector`, `TrajectoryReflector`, `GlobalReflector`, and `Progressor`.**

The following MobileUse components are explicitly excluded:

- `Planner`
- `NoteTaker`
- proactive exploration, external knowledge, or retrieval-augmented generation
- reflection on demand
- `ColorMobileAgent`
- hierarchical task classifiers, orchestrators, extractors, or rewriters
- any MobileUse component not named in the six-module inclusion list above

Every retained role must use the same frozen Qwen3-VL-32B model revision, inference engine, sampling configuration, and coordinate convention. No second model, proprietary API, trained verifier, external grounding model, optical character recognition service, accessibility-tree input, or task-specific helper is permitted.

This selection is not a prediction that MobileUse will improve the 4/19 baseline. It is the framework that best satisfies the joint requirements of:

1. broad coverage of the observed failure chain;
2. a public, inspectable implementation;
3. compatibility with a same-backbone frozen experiment;
4. sufficiently faithful adaptation without replacing the framework’s central algorithm;
5. completion within the remaining compute and engineering budget.

MobileUse receives an **87/100 decision score** under the frozen rubric:

| Criterion | Weight | MobileUse score |
|---|---:|---:|
| Coverage of the measured failure chain | 35 | 28 |
| Faithfulness of frozen-Qwen adaptation | 25 | 24 |
| Primary-source empirical evidence | 20 | 18 |
| Public reproducibility | 10 | 9 |
| Time and compute feasibility | 10 | 8 |
| **Total** | **100** | **87** |

This is a framework-selection score, not an estimate of AndroidWorld success.

---

## 3. Evidence boundary and independence declaration

This decision uses only the current default `main` snapshot of `ScottBlizzard/RAVEN-M`. Historical Git commits were not inspected. Earlier GPT analyses and excluded historical author reports were not used as scientific authority.

The current decision packet explicitly requests a fresh judgment based on the current repository snapshot, its frozen measurements, current implementation, current protocols, and independently verified public framework sources. 

The repository evidence examined includes:

- `GPT_DECISION_REQUEST.md`
- `ARTIFACT_MANIFEST.md`
- `FRAMEWORK_SELECTION_RUBRIC.md`
- `README.md`
- `VALIDATION.md`
- the frozen model and runtime configuration
- the 19-task manifest and execution order
- the 57-run, three-seed baseline summary
- all 1,175 eligible diagnostic records and aggregate diagnostics
- the recorded intervention reports
- implementation and evaluation code
- the original summer-camp assignment

Public framework claims were checked against official papers, official repositories, released configuration files, and released implementation paths rather than survey summaries or leaderboard-only claims.

---

## 4. Frozen empirical problem

### 4.1 Baseline

The current baseline contains all **57/57** planned runs: 19 tasks across three seeds. It achieved:

- **7/57 full successes**
- **9/57 runs with positive reward**
- **2/57 partial-reward runs**
- total reward **8.0**
- mean reward **0.140**
- **1,175 eligible model calls**
- **471.9 minutes** of recorded model time
- **21 false-success terminations**
- **39 repeated-state events**
- **14 stagnation events**
- **385 nearly unchanged actions**
- **4 protocol errors**
- **0 execution failures** 

The frozen first seed used for the public-framework comparison produced:

- **4/19 full successes**
- total reward **4.5**
- **329 model calls**

The four full-success tasks were:

- `H04 ExpenseDeleteMultiple2`
- `H14 RetroSavePlaylist`
- `H16 SimpleCalendarAddOneEvent`
- `H19 SportsTrackerTotalDurationForCategoryThisWeek`

`H05 MarkorCreateNoteAndSms` received partial reward `0.5`.

This 4/19 result is the sole task-level comparator. It must not be rerun or re-estimated during framework development.

### 4.2 Measured failure vector

The diagnostics identify a failure chain substantially broader than visual grounding or single-step action selection:

1. The correct initial app was reached in **49/57** runs.
2. A wrong initial app was entered and later recovered from in **6/57** runs.
3. The appropriate initial app was never reached in only **2/57** runs.
4. Of **27 cross-application tasks**, the destination app was reached in **16**, but full success was **0/27**.
5. Among **26 expected objects** in destination-reaching trajectories, only **3 identifying values** were typed into the destination.
6. In the Markor subset:
   - Markor was reached in **9/9** runs;
   - the required document was reached in **8/9**;
   - any relevant object was captured in **5/9**;
   - the complete object set was captured in **3/9**;
   - any object was typed into the destination in **2/9**;
   - full success was **0/9**.
7. There were **13 object-role mismatch** cases.
8. False completion, state repetition, and stagnation remained material: **21**, **39**, and **14** cases respectively. 

The principal problem is therefore not failure to launch an app. It is degradation along a multi-stage information and control chain:

\[
\text{source selection}
\rightarrow
\text{source coverage}
\rightarrow
\text{object retention}
\rightarrow
\text{cross-app handoff}
\rightarrow
\text{destination binding}
\rightarrow
\text{action-effect verification}
\rightarrow
\text{completion closure}.
\]

A qualifying framework must cover several adjacent stages of this chain. A framework aimed only at clicking accuracy, scrolling, or terminal verification is insufficient.

### 4.3 Unsuccessful interventions

The repository’s interventions provide adverse evidence that isolated patches are inadequate:

- An evidence-qualified progress intervention produced **0/3 improvements**, increased calls from **36 to 49**, actions from **33 to 47**, and execution time from approximately **718.7 to 1,554.3 seconds**.
- Transition attestation reduced some looping but substituted earlier false success in some cases. Detecting a visual transition did not establish semantic task progress.
- A detached completion critic rejected **19/21** false-success candidates but accepted only **2/6** true completions, yielding **61.9% balanced accuracy**, below its qualification threshold.
- A coverage gate increased forward scrolling from **0 to 64** events but achieved only **1/8 object recall**, recovered no complete object set, and increased calls from **82 to 141**.
- A visible-object extractor produced structurally valid output in **13/13** cases and 100% precision on emitted objects, but only **11/21 recall** and complete recovery in **3/8** applicable cases.

These results rule out choosing a framework merely because it adds a progress summary, a transition verifier, a completion verifier, forced scrolling, or a standalone extractor. The selected framework must provide an integrated control cycle in which state interpretation, progress, action verification, trajectory-level reflection, and completion review are connected.

---

## 5. Selection rule

A candidate is ineligible if any of the following is true:

1. no publicly inspectable implementation exists;
2. faithful reproduction requires a proprietary model or unavailable service;
3. its central algorithm depends on accessibility trees, hidden application state, direct application APIs, arbitrary shell commands, or a richer action interface than the frozen RAVEN-M arm;
4. replacing its original model with Qwen3-VL-32B would remove or redesign a defining part of the framework rather than mechanically substitute a backbone;
5. it requires new training, online reinforcement learning, collection of successful trajectories, or a new model checkpoint;
6. it cannot be implemented and run within the remaining time and compute;
7. it addresses only one narrow downstream symptom while leaving the source–object–handoff chain unrepresented.

Candidates passing the hard gate are compared using the repository’s weighted rubric:

\[
35\% \text{ failure coverage}
+
25\% \text{ faithful adaptation}
+
20\% \text{ evidence}
+
10\% \text{ reproducibility}
+
10\% \text{ feasibility}.
\]

The framework with the highest score among hard-gate survivors is selected. 

---

## 6. Independently constructed candidate pool

### 6.1 Candidate comparison

| Candidate | Public code | Central mechanism | AndroidWorld evidence | Frozen-Qwen adaptation | Decision |
|---|---|---|---|---|---|
| **MadeAgents MobileUse MultiAgent** | Yes, MIT | Operator plus action-, trajectory-, and global-level reflection with persistent progress | Paper reports 62.9 on AndroidWorld for its full configuration; official AndroidWorld template is released | High: all selected roles can use the same OpenAI-compatible Qwen endpoint; no training is required | **SELECT** |
| Minitap `mobile-use` | Yes, Apache-2.0 | Multi-agent decomposition, accessibility-driven perception, deterministic post-validation, metacognition, scratchpad | Paper reports 100% AndroidWorld and substantial ablations | Low under this protocol: released core uses UI accessibility hierarchy, direct device/app tools, and a larger preferred context for a key role | Reject: hard fairness and fidelity failure |
| AgentProg | Yes, Apache-2.0 | Semantic task program, explicit variables, execution tree, global belief | Paper reports 78.0 on AndroidWorld; strong ablations | Low: release explicitly depends on Gemini 2.5 Pro and UI-TARS-1.5; replacing both with one Qwen model changes its defining dual-model system | Reject: model-stack fidelity failure |
| Mobile-Agent-v3 | Yes | Hierarchical multi-agent system coupled to GUI-Owl | Strong mobile benchmark results | Low: algorithm and released agent are closely tied to a trained GUI-Owl stack | Reject: checkpoint and architecture confound |
| Agent S3 | Yes, Apache-2.0 | Planning, grounding, verification, and desktop/mobile computer-use modules | Reported AndroidWorld results around the high 60s or low 70s depending on setup | Low: relies on external main and grounding APIs, desktop-oriented ACI modules, and additional perception components | Reject: adaptation scope and time |
| AndroidWorld M3A | Yes, Apache-2.0 | Reactive multimodal agent with screenshot, accessibility, or set-of-marks variants | Official AndroidWorld baseline | Medium | Reject: insufficient coverage of persistent source/object/handoff failures |
| V-Droid | Public implementation | Generative action-effect verification and recovery | Paper reports 59.5 on AndroidWorld | Low-to-medium: verifier training and checkpoint are part of the method | Reject: narrow verifier plus training dependency |
| Mobile-Agent-E | Public code | Multi-agent self-evolution for mobile interaction | Mobile-agent evidence | Low: no clean, current, same-Qwen AndroidWorld reproduction path | Reject: reproduction ambiguity |
| ATMem-UI | Paper/project material | Agent trajectory memory | Emerging evidence | Low: code/model availability and online-learning path were not sufficiently complete | Reject |
| TSR | Paper material | Test-time self-reflection | Emerging evidence | Low: no complete official implementation path verified | Reject |
| K2 | Limited public project | C-GRPO-trained mobile agent | Mobile benchmark claims | Low: requires a separately trained Qwen2.5-VL-7B checkpoint and training method | Reject |
| MAGNET | Paper/project material | Memory construction from trajectories | Mobile benchmark claims | Low: successful-trajectory and memory-construction requirements create a new training/data arm | Reject |
| LearnAct | Paper/project material | Online action learning | Emerging evidence | Low: implementation availability and online adaptation violate the frozen arm | Reject |
| MobileRL | Yes, MIT | Staged warm-up and online reinforcement learning | Mobile benchmark evidence | Low: requires training and online RL | Reject |

### 6.2 Why the strongest headline competitor is not selected

Minitap’s `mobile-use` is the strongest paper-level challenger. Its official material reports a 100% AndroidWorld result and attributes large contributions to multi-agent decomposition, deterministic post-validation, hybrid perception, metacognition, scratchpad, and its device-control stack. The reported ablations reduce performance to 79% without multi-agent decomposition, 85% without post-validation, 89% without hybrid perception, 91% without metacognition, and 92% without scratchpad. 

It nevertheless fails this experiment’s hard gate. The released framework uses the UI accessibility hierarchy as a principal perception source, with the screenshot as an additional visual source. Its current controller retrieves both screenshots and UI elements through UIAutomator2. Its tool surface also contains direct application and device operations such as launching or stopping applications, opening links, focus manipulation, and text-field operations. 

Removing accessibility data and replacing the direct tool surface would eliminate or materially alter several of the exact components to which its reported gains are attributed. Its configuration also indicates that a central reasoning role preferably requires a 256,000-token context, whereas the frozen Qwen runtime is capped at 65,536 tokens. The paper further shows severe sensitivity to role-model assignment, including collapse on a reported subset when a central role is downgraded to a smaller Qwen vision-language model. 

Minitap is therefore not rejected because its result is weak. It is rejected because a fair screenshot-only, same-Qwen reproduction would not remain a faithful reproduction of the released method.

### 6.3 Why the best mechanistic match is not selected

AgentProg most directly represents the source/object/handoff problem. Its semantic task program, explicit variables, dynamic execution tree, and global belief are structurally aligned with retaining object identities and transferring them between applications. The paper reports 78.0 on AndroidWorld, with substantial ablations when global belief, the execution tree, or explicit variables are removed. 

However, the released implementation explicitly requires both Gemini 2.5 Pro and UI-TARS-1.5 credentials. Replacing a dual-model semantic-programming and grounding stack with one frozen Qwen3-VL-32B endpoint is not a mechanical adaptation. It would create a new AgentProg-inspired system whose result could not be attributed cleanly to the public framework. The paper’s reported successful-run cost is also high, with approximately 1.026 million static input tokens, 301,000 dynamic input tokens, 180,000 output tokens, and 2,662 seconds per task on its extended evaluation. 

AgentProg is therefore rejected on faithful adaptation and cost, despite its strong conceptual fit.

---

## 7. Failure-chain coverage audit

Legend:

- `I`: directly implemented in released framework logic
- `P`: partial, indirect, or represented through free-form state
- `A`: absent as a distinct mechanism
- `†`: candidate has a disqualifying fidelity or fairness dependency

| Framework | Plan/progress | Source identity and coverage | Object-set capture and retention | Cross-app handoff and destination binding | Action-effect verification | Recovery and loop escape | Completion closure |
|---|---:|---:|---:|---:|---:|---:|---:|
| **MadeAgents MobileUse** | P | P | P | P | P | I | I |
| Minitap `mobile-use` | I | P | I | P | I | I | I† |
| AgentProg | I | I | I | I | I | I | P† |
| Mobile-Agent-v3 | I | P | P | P | P | I | P† |
| Agent S3 | I | P | P | P | P | I | P† |
| AndroidWorld M3A | P | A | A | A | P | P | P |
| V-Droid | P | A | A | A | I | I | P† |
| Mobile-Agent-E | I | P | P | P | P | I | P† |

MobileUse does not explicitly encode a source ledger, typed object set, or source-to-destination binding graph. Its coverage of those stages is only partial because progress and trajectory state are free-form language. This limitation is material and must remain visible in the final interpretation.

Its comparative advantage is that it connects several adjacent controls in one released loop:

1. the `Operator` chooses one action from the current observation and retained framework state;
2. the `Reflector` compares the pre-action and post-action observations;
3. the `Progressor` updates persistent task progress after the action;
4. the `TrajectoryReflector` periodically examines the accumulated trajectory and detects error or repetition;
5. the `AnswerAgent` handles answer-producing tasks;
6. the `GlobalReflector` reviews the first completion attempt and can return control to the agent.

The official template exposes these components directly, while the public repository supports Qwen-family models and AndroidWorld execution. 

---

## 8. Primary-source evidence for the selected framework

The official MobileUse repository is public under the MIT license, includes Qwen-family support, and provides an AndroidWorld path and a released multi-agent template. 

The MobileUse paper describes a hierarchical reflection framework and reports:

- **62.9** on AndroidWorld for its reported full system;
- **44.2** on AndroidLab. 

The paper also reports material model sensitivity:

- the reported full system using Qwen2.5-VL-72B reached 62.9;
- a Qwen2.5-VL-32B full-system variant reached 44.4.

Its hard-task ablations report a progression from:

- base `Operator + Progressor`: 13.7;
- plus action reflection: 22.7;
- plus trajectory reflection: 24.7;
- plus global reflection: 31.6.

The reflection-on-demand and proactive variants do not uniformly improve the hard subset, which supports excluding them from the first reproduction rather than enabling every available module. 

These published numbers must not be treated as expected results for RAVEN-M. The selected arm differs in model family and revision, sampling, task suite, step budgets, environment integration, action adapter, and enabled module subset.

---

## 9. Relationship to the unsuccessful RAVEN-M interventions

The selected framework overlaps with several failed interventions:

| Prior failed intervention | MobileUse overlap | Material difference |
|---|---|---|
| Evidence-qualified progress | `Progressor` | Progress is embedded in a recurring operator–reflection loop and is fed back into future action selection |
| L4 transition attestation | `Reflector` comparing before/after observations | Reflection is followed by progress revision and periodic trajectory review rather than treated as a sufficient progress certificate |
| Detached completion critic | `GlobalReflector` | The global review is part of the released termination control flow and can resume the same agent trajectory |
| Loop/stagnation diagnostics | `TrajectoryReflector` | The released module jointly observes trajectory history, error indicators, and repeated actions/screens |
| Standalone coverage/extraction | Free-form progress and trajectory state | MobileUse does **not** add a structured object extractor; this remains a likely weakness |

This distinction is sufficient to justify testing MobileUse, but not sufficient to presume improvement. The prior failures are direct adverse evidence against the hypothesis that reflection or progress summaries alone will solve the task set.

The experiment qualifies only if the integrated MobileUse loop improves at least one core source–object–handoff metric, not merely if it reduces repeated actions.

---

## 10. Selected MobileUse algorithm

### 10.1 Enabled modules

Exactly these six roles are enabled:

```text
Operator
Reflector
Progressor
TrajectoryReflector
AnswerAgent
GlobalReflector
```

### 10.2 Frozen control schedule

For each native agent decision:

1. `Operator` receives:
   - the user task;
   - the current screenshot;
   - the framework’s own current progress and permitted trajectory state;
   - the frozen action schema.

2. `Operator` emits one action or a finish/answer signal.

3. The output parser receives at most **three total attempts**:
   - one original generation;
   - at most two format-repair generations using the released format-correction behavior.

4. If a valid nonterminal action is emitted:
   - execute at most one native Android action;
   - capture the resulting screenshot;
   - invoke `Reflector` on the ordered pre-action and post-action screenshots;
   - invoke `Progressor`;
   - invoke `TrajectoryReflector` only when the released schedule calls for it.

5. The trajectory defaults remain:

```yaml
trajectory_reflector:
  interval: 5
  cold_start: 3
  detect_error: true
  max_repeat_action: 3
  max_repeat_action_series: 2
  max_repeat_screen: 3
  max_fail: 3
```

6. On an answer-producing task, invoke `AnswerAgent` and submit through the existing RAVEN-M answer path.

7. On the first finish signal:
   - invoke `GlobalReflector`;
   - provide the permitted recent framework history and at most the latest three screenshots;
   - a failed global verdict clears the finish state and returns control to the same trajectory.

8. No additional global-verification cycle is inserted beyond the released first-finish behavior.

The released implementation performs one operator prediction, supports bounded output correction, executes no more than one action before reflection, and schedules action-, progress-, trajectory-, and completion-level modules in this order. 

### 10.3 Image comparison

The released MobileUse `diff_image` preprocessing for before/after observations must be retained exactly. It must not be replaced by a RAVEN-specific transition classifier or threshold. 

---

## 11. Exact adaptation contract

### 11.1 Elements that must be preserved

The implementation must preserve:

1. the current upstream MobileUse source snapshot selected at implementation preflight;
2. the selected six modules;
3. upstream role prompts except for enumerated mechanical substitutions;
4. upstream role order;
5. upstream output parsing and bounded correction behavior;
6. upstream action reflection based on the ordered pre-action and post-action screenshots;
7. upstream progress update behavior;
8. upstream trajectory-reflection schedule and thresholds;
9. upstream first-finish global-reflection behavior;
10. one action per operator decision;
11. the same Qwen3-VL-32B model for every role;
12. the RAVEN-M L0–L5 diagnostic and evaluation pipeline;
13. AndroidWorld’s native task reset and evaluator.

### 11.2 Mandatory mechanical substitutions

Only the following adaptations are authorized.

#### A. Model transport

Replace the upstream client with an audited OpenAI-compatible vLLM client pointing to the frozen local Qwen endpoint.

All roles use:

```yaml
model: Qwen/Qwen3-VL-32B-Instruct
revision: 0cfaf48183f594c314753d30a4c4974bc75f3ccb
dtype: bfloat16
vllm_version: 0.26.0
tensor_parallel_size: 1
gpu_memory_utilization: 0.92
max_model_len: 65536
max_new_tokens: 32768
temperature: 0.7
top_p: 0.8
top_k: 20
presence_penalty: 1.5
repetition_penalty: 1.0
generation_seed: 3407
coordinate_range: [0, 999]
max_concurrency: 1
```

The sole server-level transport change is:

```yaml
limit_mm_per_prompt:
  image: 3
```

No other model or runtime field may change.

Image use remains role-bounded:

- `Operator`: exactly one current screenshot;
- `Reflector`: exactly two ordered screenshots, before then after;
- `GlobalReflector`: at most three recent screenshots in chronological order;
- text-only roles: no screenshot unless required by the selected upstream template.

No screenshot montage or composite image is allowed.

If the three-image preflight cannot run within the frozen model, runtime, context limit, and compute cap, the experiment stops. It must not fall back to image stitching, a different model, a smaller resolution policy invented for this arm, or text descriptions generated by another model.

#### B. Environment

Use the existing RAVEN-M AndroidWorld integration for:

- environment reset;
- task instantiation;
- application state;
- native step counting;
- evaluator calls;
- reward collection;
- task completion;
- action execution.

Do not use the MobileUse AndroidWorld fork’s modified reset behavior or its recommended 1.2× step allowance. The upstream guide’s budget extension is intentionally excluded to preserve comparison fairness. 

#### C. Action interface

The framework may emit only:

```text
tap
swipe
type
back
home
answer
terminate
```

Mechanical mappings are:

| Upstream expression | Frozen action |
|---|---|
| `click(x, y)` | `tap(x, y)` |
| `swipe(...)` | `swipe(...)` |
| `type(text)` | `type(text)` |
| `system_button("Back")` | `back` |
| `system_button("Home")` | `home` |
| `answer(text)` | `answer(text)` |
| `terminate(status)` | `terminate(status)` |

All coordinates use `[0,999]` normalization and the existing RAVEN-M adapter.

The following actions and capabilities must be removed from the prompt and rejected at runtime:

- direct `open_app` or `launch_app`
- `stop_app`
- `open_link`
- arbitrary shell or ADB commands
- direct application APIs
- `clear_text` as a privileged field operation
- focus manipulation
- `take_note`
- long press
- arbitrary waits
- direct UI-element references
- accessibility-node actions
- hidden state queries

Opening an app must occur visually through the same Android action interface available to the baseline.

#### D. Prompt substitutions

Prompt edits are limited to:

1. action names and their exact JSON schema;
2. coordinate range;
3. removal of unsupported tools;
4. model endpoint identifier;
5. environment-neutral terminology required for the RAVEN action adapter.

Role responsibilities, output sections, ordering, reflection logic, and decision semantics must remain unchanged.

Every prompt diff must be archived. Each changed line must be classified as one of the five allowed mechanical substitutions. Any other prompt change invalidates the implementation.

### 11.3 Information restrictions

No role may receive:

- evaluator reward;
- success/failure predicate internals;
- hidden task parameters;
- ground-truth source file names unless present in the user instruction;
- baseline trajectories;
- baseline rewards or diagnostic labels;
- accessibility trees;
- UI hierarchy;
- application database contents;
- OCR output from an external recognizer;
- test-set-specific hints;
- privileged app state.

`GlobalReflector` may inspect only:

- the task text;
- screenshots available to the framework;
- the framework’s own action and reflection history;
- the framework’s own progress state.

### 11.4 Explicitly prohibited modifications

The engineer must not add or enable:

- Planner
- NoteTaker
- proactive exploration
- external knowledge or RAG
- reflection on demand
- `ColorMobileAgent`
- task classifier
- hierarchy orchestrator
- source extractor
- object extractor
- structured memory
- source-completion gate
- destination-binding module
- new completion critic
- app-specific prompt clauses
- task-specific retries
- task-specific state machines
- application-name routing hints
- external OCR
- accessibility data
- a second model
- proprietary APIs
- fine-tuning
- reinforcement learning
- successful-trajectory retrieval
- framework ensembling
- any code copied from a rejected candidate

---

## 12. Source and dependency lock

### 12.1 Required source lock

Before implementation, create:

```text
implementation/third_party/mobile_use/SOURCE_LOCK.json
```

It must contain:

```json
{
  "repository": "MadeAgents/MobileUse",
  "branch_at_resolution": "main",
  "resolved_commit_sha": "<exact current upstream SHA>",
  "resolved_tree_sha": "<exact tree SHA>",
  "retrieved_at_utc": "<timestamp>",
  "license": "MIT",
  "selected_template": "<exact template path>",
  "selected_source_files": [
    {
      "path": "<path>",
      "sha256": "<hash>"
    }
  ],
  "selected_prompt_files": [
    {
      "path": "<path>",
      "sha256": "<hash>"
    }
  ]
}
```

The engineer must resolve the exact upstream SHA at preflight and then vendor or pin that immutable snapshot. No later pull from moving `main` is permitted.

This is a mechanical provenance check, not a remaining scientific choice.

### 12.2 Required license files

Copy the upstream license into:

```text
implementation/third_party/mobile_use/LICENSE
```

Create a dependency and license inventory for every imported package.

### 12.3 Dependencies

No new model weights are required.

Permitted runtime dependencies are limited to:

- Python 3.10 or later, matching the current environment;
- existing RAVEN-M and AndroidWorld dependencies;
- existing vLLM stack;
- an OpenAI-compatible client;
- `numpy`;
- `Pillow`;
- `opencv-python`;
- `scikit-image`;
- `pydantic`;
- `PyYAML`;
- `jsonlines`;
- minimal transitive dependencies strictly required by the selected MobileUse path.

All versions must be pinned after a successful preflight.

Optional MobileUse dependencies for web interfaces, embeddings, retrieval, proactive knowledge, Gradio, external APIs, or unselected agents must not be installed unless unavoidable for import isolation. If an optional package is unavoidable, its code path must be proven unreachable during the scored run.

No external network request is allowed during the scored experiment.

---

## 13. Required implementation layout

Create exactly the following framework-specific files:

```text
implementation/
├── third_party/
│   └── mobile_use/
│       ├── SOURCE_LOCK.json
│       ├── LICENSE
│       └── <vendored selected upstream files>
├── configs/
│   └── mobileuse_multiagent_qwen3_vl_32b_hard_seed20260806.yaml
├── scripts/
│   ├── preflight_mobileuse.py
│   ├── run_mobileuse_hard.py
│   └── audit_mobileuse_arm.py
├── src/
│   └── raven_m/
│       ├── models/
│       │   └── vllm_multi_image_client.py
│       └── public_frameworks/
│           └── mobileuse/
│               ├── action_adapter.py
│               ├── controller.py
│               └── logging.py
└── tests/
    └── public_frameworks/
        └── mobileuse/
            ├── test_action_adapter.py
            ├── test_controller_schedule.py
            ├── test_image_order.py
            ├── test_parser_retry.py
            ├── test_prompt_diff.py
            ├── test_information_isolation.py
            └── test_logging_completeness.py

protocols/
├── MOBILEUSE_QWEN3VL32B_HARD_SEED20260806_PREREG.md
└── MOBILEUSE_QWEN3VL32B_HARD_SEED20260806_PREREG.json
```

Final outputs must include:

```text
reports/public_framework/
├── PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1.json
├── PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1.md
├── PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1_VALIDATION.json
└── PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1_COST.json
```

---

## 14. Implementation order

The engineer must execute these steps in order:

1. Resolve and lock the exact upstream MobileUse source SHA, tree SHA, selected files, prompts, and MIT license.
2. Create the frozen configuration and preregistration skeleton.
3. Implement and test the one-, two-, and three-image vLLM transport without changing any frozen inference field except `limit_mm_per_prompt.image`.
4. Implement the strict action adapter and rejection behavior.
5. Apply and archive the permitted prompt-schema substitutions.
6. Wrap the vendored upstream controller without rewriting its role schedule.
7. Implement role-aware L0–L5 logging.
8. Integrate RAVEN-M reset, native step counting, answer submission, and evaluator calls.
9. Implement deterministic mechanism-metric extraction.
10. Run all unit tests and offline replay tests.
11. Run the single authorized non-scoring smoke test.
12. Freeze source, prompt, configuration, dependency, container, and test hashes.
13. Run the 19 scored tasks in the frozen order.
14. Execute the frozen analyzer exactly once.
15. Produce the validation, cost, and scientific-decision reports.

No scientific choice is delegated to the engineer at any step.

---

## 15. Logging requirements

Every model request must record:

- arm identifier;
- task identifier;
- task seed;
- native decision index;
- role;
- retry index;
- model identifier and revision;
- sampling configuration hash;
- prompt template hash;
- fully rendered prompt hash;
- ordered input-image hashes;
- raw response hash;
- parsed response;
- parser result;
- action-adapter result;
- token counts;
- latency;
- exception status.

Every action record must include:

- normalized action;
- native AndroidWorld action;
- pre-action screenshot hash;
- post-action screenshot hash;
- environment response;
- native step number;
- whether the action altered the screenshot;
- L0–L5 diagnostic fields.

The logger must distinguish:

1. model requests;
2. operator decisions;
3. native environment actions;
4. auxiliary reflection calls;
5. parser retries;
6. answer submissions;
7. termination attempts;
8. evaluator calls.

Auxiliary model calls do not consume native task steps. Each operator decision consumes one native decision slot, even when all parser attempts fail.

---

## 16. Zero-scored-call preflight

All checks below must pass before any H01–H19 model call.

### 16.1 Provenance checks

- exact MobileUse commit SHA resolved;
- tree and selected-file hashes recorded;
- license copied and verified;
- selected template confirmed present in the locked snapshot;
- no moving branch reference used at runtime.

### 16.2 Module checks

Assert that the enabled role set is exactly:

```text
Operator
Reflector
Progressor
TrajectoryReflector
AnswerAgent
GlobalReflector
```

Assert that all prohibited modules are disabled and unreachable.

### 16.3 Model freeze checks

Assert all frozen model, revision, dtype, vLLM, context, sampling, coordinate, and concurrency fields.

The only accepted diff from the baseline server transport is:

```diff
- limit_mm_per_prompt.image: 1
+ limit_mm_per_prompt.image: 3
```

### 16.4 Multi-image checks

Test:

- one-image operator request;
- two-image reflector request with deterministic before/after ordering;
- three-image global-reflector request in chronological order;
- image-hash preservation through serialization;
- no automatic montage;
- no image duplication;
- context and memory fit;
- reproducible responses under the frozen generation seed to the extent supported by the runtime.

Failure of the three-image path is a stop condition.

### 16.5 Prompt-diff checks

Generate a machine-readable diff from each locked upstream prompt.

Every changed line must be labelled as:

```text
ACTION_NAME
ACTION_SCHEMA
COORDINATE_RANGE
UNSUPPORTED_TOOL_REMOVAL
ENDPOINT_IDENTIFIER
```

Any unclassified prompt change fails preflight.

Scan prompts for:

- benchmark answers;
- task identifiers H01–H19;
- baseline outcomes;
- app-specific instructions;
- evaluator details;
- accessibility references;
- hidden-state references.

### 16.6 Action-adapter checks

Unit-test:

- coordinate boundary values `0` and `999`;
- coordinate round trips;
- tap conversion;
- all swipe directions and lengths supported by the current adapter;
- text escaping and Unicode;
- back and home;
- answer;
- terminate;
- rejection of every prohibited action;
- rejection of multiple actions in one operator output;
- rejection of direct app launch and link opening.

### 16.7 Schedule checks

With mocked model outputs and environment states, verify the exact normal sequence:

```text
Operator
Environment action
Reflector
Progressor
Optional TrajectoryReflector
```

Also verify:

- maximum three total operator parse attempts;
- no action after an invalid output;
- no more than one action per operator decision;
- first finish invokes `GlobalReflector`;
- a failed global verdict clears finish;
- resumed execution returns to `Operator`;
- a later finish follows the locked upstream behavior;
- `AnswerAgent` is used only for answer-producing tasks.

### 16.8 Information-isolation checks

Prove by runtime assertions that no role can access:

- reward;
- evaluator internals;
- ground-truth task parameters;
- Android accessibility hierarchy;
- baseline trajectories;
- baseline diagnostic labels;
- application databases;
- hidden emulator state.

### 16.9 Offline replay checks

Replay all 19 existing first-seed baseline trajectories without making a model call or modifying an emulator.

The replay is used only to validate:

- parser compatibility;
- logging completeness;
- action normalization;
- task ordering;
- mechanism-metric calculation;
- reference-hash generation.

It must not be used to add prompts, hints, or task-specific behavior.

Generate and freeze the baseline mechanism-reference file before the scored arm begins.

### 16.10 Dependency checks

Produce:

- exact package versions;
- package hashes where available;
- license inventory;
- import graph for the selected path;
- proof that external API clients and unselected MobileUse modules are unreachable.

---

## 17. Authorized smoke test

Exactly one live non-scoring smoke task is authorized:

```yaml
task: ContactsAddContact
seed: 20260805
maximum_native_decisions: 3
score_used_for_science: false
```

`ContactsAddContact` must be outside H01–H19 and must not share a hidden parameter instance with the frozen hard suite.

The smoke must exercise:

- `Operator` with one screenshot;
- a valid native action;
- `Reflector` with two ordered screenshots;
- `Progressor`;
- role-aware logging;
- AndroidWorld reset;
- native step counting.

Synthetic role fixtures must additionally exercise:

- `TrajectoryReflector`;
- `AnswerAgent`;
- `GlobalReflector` with three screenshots;
- failed first-finish veto and return to the operator;
- parser retry exhaustion.

The live smoke may be rerun only after an infrastructure or generic mechanical-adapter failure that occurred before a scientifically usable trajectory was produced.

A permitted pre-score patch must:

1. be generic rather than task-specific;
2. change only the frozen mechanical adaptation layer;
3. be documented;
4. trigger a complete rerun of zero-call preflight and the smoke;
5. occur before any H01–H19 call.

Once the smoke passes, all source, prompt, configuration, dependency, container, and test hashes are frozen.

---

## 18. Frozen scored experiment

### 18.1 Arm identifier

```text
PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1
```

### 18.2 Benchmark lock

Use:

- the repository’s frozen AndroidWorld commit;
- experiment seed `20260806`;
- the exact current task-goal and parameter hashes;
- the exact evaluator;
- the exact baseline native step budgets;
- the exact execution order below.

The AndroidWorld source lock recorded by the project is commit:

```text
3e50888527ef9f29b9157ecd537e408008bb1c85
```

The existing manifest contains the authoritative task parameters, hashes, and budgets. 

### 18.3 Execution order

Run the tasks in exactly this order:

```text
H06
H04
H03
H15
H11
H13
H02
H05
H10
H12
H08
H16
H14
H19
H09
H18
H17
H01
H07
```

This is the frozen comparison order. 

### 18.4 Task and budget table

| Order-independent ID | Task | Native budget | Baseline first-seed calls | Baseline reward |
|---|---|---:|---:|---:|
| H01 | BrowserMultiply | 22 | 13 | 0 |
| H02 | ExpenseAddMultipleFromGallery | 60 | 16 | 0 |
| H03 | ExpenseAddMultipleFromMarkor | 60 | 13 | 0 |
| H04 | ExpenseDeleteMultiple2 | 34 | 18 | 1 |
| H05 | MarkorCreateNoteAndSms | 18 | 17 | 0.5 |
| H06 | MarkorMergeNotes | 78 | 32 | 0 |
| H07 | MarkorTranscribeVideo | 20 | 20 | 0 |
| H08 | OsmAndMarker | 20 | 11 | 0 |
| H09 | OsmAndTrack | 120 | 19 | 0 |
| H10 | RecipeAddMultipleRecipesFromImage | 60 | 60 | 0 |
| H11 | RecipeAddMultipleRecipesFromMarkor | 60 | 13 | 0 |
| H12 | RecipeAddMultipleRecipesFromMarkor2 | 60 | 14 | 0 |
| H13 | RecipeDeleteMultipleRecipesWithConstraint | 40 | 15 | 0 |
| H14 | RetroSavePlaylist | 50 | 32 | 1 |
| H15 | SaveCopyOfReceiptTaskEval | 16 | 10 | 0 |
| H16 | SimpleCalendarAddOneEvent | 34 | 17 | 1 |
| H17 | SportsTrackerActivitiesOnDate | 20 | 3 | 0 |
| H18 | SportsTrackerTotalDistanceForCategoryOverInterval | 22 | 3 | 0 |
| H19 | SportsTrackerTotalDurationForCategoryThisWeek | 16 | 3 | 1 |
| **Total** |  | **810** | **329** | **4.5** |

### 18.5 Native-step accounting

- One `Operator` decision consumes one native decision slot.
- At most one Android action may occur in that slot.
- `Reflector`, `Progressor`, `TrajectoryReflector`, `AnswerAgent`, and `GlobalReflector` calls consume no native AndroidWorld steps.
- Parser retries consume model requests but not additional native AndroidWorld steps.
- If all three operator-output attempts are invalid:
  - record `operator_output_invalid`;
  - execute no environment action;
  - consume the current native decision slot;
  - continue until the task budget is exhausted.

### 18.6 No adaptive intervention

During the scored run, do not:

- inspect interim aggregate performance to change the implementation;
- change prompts;
- change reflection frequency;
- change thresholds;
- change role context;
- add task-specific handling;
- reorder tasks;
- change step budgets;
- change model parameters;
- rerun a scientifically valid failed task;
- stop because results appear poor.

All 19 tasks must be attempted unless an invalidity or emergency stop condition is met.

---

## 19. Invalidity and rerun policy

### 19.1 Scientifically valid task failure

The following are valid framework outcomes and must not be rerun:

- wrong action;
- app-selection error;
- loop;
- stagnation;
- false completion;
- parser exhaustion;
- context-management failure generated by valid framework code;
- task-budget exhaustion;
- incorrect answer;
- failure to recover;
- model refusal;
- failure caused by the selected framework’s own prompt or control logic.

### 19.2 Infrastructure-invalid task

A task is infrastructure-invalid only for:

- emulator crash unrelated to the selected action;
- AndroidWorld process crash;
- model server process crash;
- endpoint disconnection before a response is recorded;
- filesystem exhaustion;
- corrupted log;
- hardware failure;
- task reset failing its existing validation;
- evaluator unavailability;
- task or environment hash mismatch.

An infrastructure-invalid task may be rerun once from an exact clean reset with unchanged source and configuration.

If the rerun is also invalid, mark the arm incomplete and nonqualifying.

### 19.3 Implementation-invalid arm

After the first scored H01–H19 model call, discovery of any of the following invalidates and stops the whole arm:

- wrong model or revision;
- wrong sampling configuration;
- unauthorized module enabled;
- evaluator or reward leakage;
- accessibility hierarchy leakage;
- action-interface violation;
- task hash drift;
- prompt drift;
- incomplete role/action logging;
- incorrect native-step accounting;
- scientific code bug requiring a semantic patch.

Do not patch and resume under the same arm identifier. Preserve all data and issue an invalid-arm report.

---

## 20. Evaluation metrics

### 20.1 Primary task metric

The primary metric is:

\[
\text{Full task success count out of 19}.
\]

The frozen comparator is:

\[
4/19.
\]

Because this is one paired seed, a one-task increase is a descriptive advancement signal, not a general statistical claim.

### 20.2 Core mechanism metrics

For each task, compute the same deterministic, paired mechanism metrics for the frozen baseline trajectory and MobileUse trajectory.

#### Source acquisition

- correct source app reached;
- correct source file, note, image, or record opened;
- source coverage before leaving the source;
- full source-object set observed before source exit.

#### Object retention

- number of expected relevant objects represented in framework-visible state;
- object recall;
- complete object-set retention;
- object-role mismatch count.

#### Cross-application handoff

- destination app reached;
- correct destination entity or form reached;
- number of correct identifiers typed;
- any correct identifier transferred;
- complete identifier set transferred;
- full cross-app task success.

#### Action and completion integrity

- action-effect verification event;
- corrected action after negative reflection;
- false terminal success;
- rejected true completion;
- recovery after wrong app or wrong screen.

### 20.3 Secondary metrics

Report:

- total reward and partial reward;
- model requests by role;
- parser retries;
- native decisions;
- native actions;
- tokens by role;
- latency by role;
- total model-GPU hours;
- repeated-state events;
- repeated-action events;
- stagnation events;
- nearly unchanged actions;
- trajectory-reflection invocations;
- global-completion vetoes;
- post-veto success;
- infrastructure-invalid runs.

Loop reduction, lower latency, or fewer actions cannot independently qualify the framework.

---

## 21. Qualification gates

### 21.1 Task-qualified broad upgrade

Label the result:

```text
TASK-QUALIFIED BROAD UPGRADE
```

only if all conditions hold:

1. all 19 tasks are scientifically valid;
2. full success is at least **5/19**;
3. at least one core source-, object-, handoff-, or completion-integrity metric strictly improves over the paired baseline;
4. false-success count does not increase.

This label means only that MobileUse is a qualified first public-framework upgrade on the frozen first seed. It is not evidence of generalization across seeds or benchmark distributions.

### 21.2 Mechanism-qualified non-regression

Label the result:

```text
MECHANISM-QUALIFIED NON-REGRESSION
```

only if:

1. all 19 tasks are scientifically valid;
2. full success remains exactly **4/19**;
3. at least one core mechanism metric strictly improves;
4. false-success count does not increase.

This outcome supports the relevance of a mechanism but does not establish task-level improvement.

### 21.3 Framework failure

Label the result:

```text
PUBLIC FRAMEWORK FAIL
```

if any of these holds:

- full success is **3/19 or lower**;
- full success is 4/19 with no core-mechanism improvement;
- false success increases without an increase in full success;
- only loop or efficiency metrics improve;
- the arm exceeds its resource ceiling;
- the arm is incomplete;
- the implementation is scientifically invalid.

A result of 5/19 or higher with worse false-success behavior must be reported descriptively but does not receive the broad-upgrade label unless the false-success gate passes.

Partial rewards remain secondary and cannot convert a failed task into a full success.

---

## 22. Stopping rules

### 22.1 Before scored execution

Stop before H01–H19 if any of the following fails:

- source provenance;
- license verification;
- exact module-set assertion;
- frozen model assertion;
- three-image transport;
- prompt-diff audit;
- strict action mapping;
- role schedule tests;
- information isolation;
- offline replay;
- dependency audit;
- live smoke.

No fallback framework is selected by this document.

### 22.2 During scored execution

Do not stop for poor scientific performance.

Emergency stop is allowed only for:

- wrong model, revision, or sampling;
- task/evaluator/reset drift;
- privilege leakage;
- unrecoverable logging gap;
- repeated infrastructure failure;
- hardware or disk failure;
- model-request ceiling reached;
- GPU-time ceiling reached.

### 22.3 Resource ceilings

Stop and mark the arm incomplete if either limit is reached:

```text
3,000 total model requests
24 model-GPU hours
```

These ceilings include all roles and parser retries.

---

## 23. Cost estimate

The frozen baseline averaged:

\[
\frac{471.9 \text{ minutes}}{1175 \text{ calls}}
=
0.4016 \text{ minutes/call}
\approx
24.10 \text{ seconds/call}.
\]

At the baseline’s 329 operator decisions, a central MobileUse request estimate is:

\[
329\ \text{Operator}
+
329\ \text{Reflector}
+
329\ \text{Progressor}
+
\left\lceil \frac{329}{5}\right\rceil\ \text{TrajectoryReflector}
+
19\ \text{AnswerAgent}
+
19\ \text{GlobalReflector}
=
1091
\]

model requests before parser retries and repeated completion attempts.

At the baseline mean request duration:

\[
1091 \times 24.10\text{ s}
\approx
7.3\text{ model-GPU hours}.
\]

Because reflector and global calls use multiple images and several roles carry longer histories, the operational reservation is:

```text
8–12 model-GPU hours
```

for a normal run.

A conservative structural ceiling at the total native budget \(A=810\), assuming an operator, reflector, and progress call per decision, one trajectory call per five decisions, and one answer/global pair per task, is:

\[
3A+\left\lceil A/5\right\rceil+38
=
2430+162+38
=
2630
\]

requests before parser retries.

The hard operational cap remains 3,000 requests or 24 model-GPU hours.

Expected engineering effort is:

```text
20–30 focused engineering hours
```

or approximately two to four working days for one engineer already familiar with the repository.

No external API fee is permitted. Monetary compute cost must be reported as:

\[
\text{measured GPU hours}
\times
\text{actual local or provider GPU-hour rate}.
\]

No unsupported dollar estimate should be inserted in advance.

---

## 24. Risks

### 24.1 Paper-to-arm configuration mismatch

The paper’s reported full configuration and model are not identical to this arm. The selected official AndroidWorld template, enabled subset, Qwen3-VL revision, sampling, action interface, and native budgets differ. Published scores are therefore not transferable.

### 24.2 Correlated role errors

All roles use the same Qwen model. Reflection may repeat the operator’s misunderstanding rather than correct it. Multi-agent role separation does not imply independent judgment.

### 24.3 Free-form state may lose exact object sets

`Progressor` and trajectory state are language summaries, not a structured ledger. They may omit one item, merge object roles, or lose source provenance—the dominant measured failure modes.

### 24.4 Visual change is not semantic progress

The prior transition-attestation experiment showed that a visible state change can accompany semantically wrong behavior. `Reflector` may recognize that something changed without proving that the intended object was transferred.

### 24.5 Completion reflection may reproduce critic errors

The prior detached critic rejected many false completions but also rejected most true completions. `GlobalReflector` can likewise reject valid success or accept visually plausible failure.

### 24.6 Multi-image runtime pressure

Two- and three-image calls may increase memory use, prompt latency, or context pressure. The three-image preflight is therefore a hard gate.

### 24.7 Native-budget fairness may reduce upstream performance

The upstream AndroidWorld instructions permit or recommend a 1.2× step allowance in some configurations. This arm deliberately removes that advantage. The result may be lower but will remain comparable to the frozen RAVEN-M baseline.

### 24.8 Request and latency multiplication

A normal action can generate operator, reflector, and progress calls, plus periodic trajectory review. The method may consume approximately three or more requests per native decision.

### 24.9 Frozen high-temperature parsing

The frozen temperature is 0.7. Structured-output instability may raise parser retries. The upstream bounded repair path must be retained rather than silently lowering temperature.

### 24.10 No explicit source/destination binding

MobileUse has broad reflective coverage but lacks AgentProg-like explicit variables or a semantic execution program. It may improve recovery and completion while leaving the central cross-app binding failure unchanged.

---

## 25. Falsification criteria

The selected framework is falsified as the first broad public-framework upgrade on this setup if any of the following occurs:

1. a valid run achieves **3/19 or lower**;
2. it achieves **4/19** without improvement in a core mechanism metric;
3. it does not improve correct object typing, cross-app transfer, or false-completion integrity despite its additional request cost;
4. any apparent gain is attributable only to looping reduction, partial reward, task-budget drift, or privileged information;
5. the released hierarchy cannot run under the frozen three-image Qwen runtime within the request and GPU-time ceilings;
6. a qualifying result requires an excluded module, app-specific prompt, accessibility hierarchy, external model, training stage, or increased step budget.

Falsification ends this arm. It does not authorize the engineer to select another framework, combine candidates, or design an original method.

---

## 26. Remaining mechanical checks

The following items must be resolved at preflight but require no further scientific judgment:

- exact current MobileUse `main` commit and tree SHA;
- exact selected template and prompt hashes;
- confirmation that the current template still matches the audited six-role schedule;
- three-image Qwen runtime fit;
- output parsing under frozen sampling;
- action-coordinate round trips;
- answer-path compatibility;
- isolation of `GlobalReflector` from evaluator state;
- complete dependency and license inventory;
- baseline mechanism-reference hashes.

Each has only two permitted outcomes:

```text
PASS
STOP
```

No alternative design choice is delegated.

---

## 27. Engineer execution handoff

The engineer must perform the following checklist without making additional scientific decisions.

### Phase A — Lock

- [ ] Pin the exact current upstream MobileUse snapshot.
- [ ] Vendor only the selected implementation and prompt paths.
- [ ] Record source, tree, file, and prompt hashes.
- [ ] Copy and verify the MIT license.
- [ ] Pin the dependency environment.
- [ ] Create the preregistration files.
- [ ] Set arm ID to `PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1`.

### Phase B — Adapt mechanically

- [ ] Implement the audited one-/two-/three-image vLLM client.
- [ ] Keep every model field frozen except image transport capacity.
- [ ] Implement the seven-action allowlist.
- [ ] Reject every privileged or unsupported tool.
- [ ] Apply only enumerated prompt-schema substitutions.
- [ ] Preserve the six-role schedule and upstream defaults.
- [ ] Use native AndroidWorld reset, steps, answer path, and evaluator.
- [ ] Keep auxiliary calls outside native step counting.
- [ ] Integrate complete role-aware L0–L5 logging.

### Phase C — Validate without scored calls

- [ ] Pass source and license checks.
- [ ] Pass module-set assertions.
- [ ] Pass model freeze assertions.
- [ ] Pass multi-image tests.
- [ ] Pass prompt-diff classification.
- [ ] Pass action-adapter tests.
- [ ] Pass schedule and retry tests.
- [ ] Pass information-isolation tests.
- [ ] Replay all 19 baseline trajectories offline.
- [ ] Generate and hash paired baseline mechanism references.
- [ ] Complete dependency and license reports.

### Phase D — Smoke and freeze

- [ ] Run only the authorized `ContactsAddContact` smoke.
- [ ] Exercise synthetic trajectory, answer, and global-reflection fixtures.
- [ ] Resolve only generic pre-score mechanical failures.
- [ ] Rerun the entire preflight after any permitted patch.
- [ ] Freeze all hashes after the smoke passes.

### Phase E — Execute

- [ ] Run the 19 tasks in the exact frozen order.
- [ ] Keep native budgets unchanged.
- [ ] Do not inspect results to alter the arm.
- [ ] Do not rerun valid failures.
- [ ] Apply only the frozen infrastructure-invalid rerun rule.
- [ ] Stop only for an explicit emergency or resource ceiling.

### Phase F — Analyze once

- [ ] Run the frozen analyzer once after execution.
- [ ] Compare full success against 4/19.
- [ ] Compute all paired core mechanism metrics.
- [ ] Report false success, loops, requests, tokens, latency, and GPU hours.
- [ ] Apply the qualification gates exactly.
- [ ] Produce the four required result artifacts.
- [ ] Do not recommend or implement a subsequent method in the execution report.

---

## 28. Final directive

Proceed with **MadeAgents MobileUse MultiAgent’s official AndroidWorld hierarchical-reflection template**, restricted to:

```text
Operator
Reflector
Progressor
TrajectoryReflector
AnswerAgent
GlobalReflector
```

Use the frozen Qwen3-VL-32B model for every role, the native RAVEN-M AndroidWorld environment and budgets, the seven-action screenshot-only interface, the exact preregistered task order, and the qualification gates in this document.

No other public framework, framework combination, original RAVEN-M module, training stage, privileged observation, or post-start scientific modification is authorized.