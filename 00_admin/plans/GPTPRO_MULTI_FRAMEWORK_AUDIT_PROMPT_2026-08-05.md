# Prompt for GPT Pro: multi-framework AndroidWorld Hard audit

You are the senior research architect and final protocol authority for this
project. Do not propose a new method merely to preserve novelty, and do not stop
the whole research program merely because the latest intervention received a
novelty NO-GO.

Open the GitHub repository `ScottBlizzard/RAVEN-M`, branch
`protocol-v2-exploratory`, and read every file below in full before giving any
recommendation:

1. `2026_08_05_17_36.md`
2. `RAVEN-M_GPTPro_full_plan_2026-08-05.md`
3. `reports/research_direction/MULTI_FRAMEWORK_HARD_BENCHMARK_HANDOFF_2026-08-05.md`
4. `04_protocols/multi_framework_hard_benchmark_v0_1.md`
5. `05_project/configs/experiments/multi_framework_hard_benchmark_v0_1.json`
6. `03_code/manifests/multi_framework_candidates_v0_1.csv`
7. `05_project/configs/task_manifests/androidworld_hard_v1.json`
8. `04_protocols/environment_lock.yaml`
9. `reports/breadth_forensic_analysis_2026-07-26.md`

The student's objective is now concrete: reproduce and compare several
important modern mobile-GUI systems on the same AndroidWorld Hard tasks, then
use task and process evidence to test the project's evolving hypotheses about
memory qualification, correct-memory/wrong-target failures, action-effect
verification, loop recovery, and feedback-to-policy binding. Existing Hard
results are dominated by failure, so a comparison must remain informative even
when official task success is zero.

Audit the proposal aggressively. Independently verify the current official
repositories, checkpoint availability, AndroidWorld runners, licenses,
observation privileges, and reported evaluation settings. In particular,
distinguish:

- exact official reproduction;
- configuration-equivalent reproduction;
- common-backbone adapter comparison;
- mechanism port;
- paper-only reported reference.

Do not let results from stronger backbones, accessibility/UI-tree access,
external tools, different action spaces, larger step budgets, or hidden task
knowledge be misattributed to framework design. At the same time, do not make
the protocol so restrictive that no informative experiment can run.

Decide whether the candidate pool should include or exclude M3A, RAVEN-B0,
RAVEN-M0, GUI-Owl-1.5, Mobile-Agent-v3.5, MobileUse MultiAgent,
ColorMobileAgent, DroidRun, ScaleCUA, UI-TARS-1.5, VLAA-GUI, K2-Agent,
VeriGUI, and BacktrackAgent. Add any stronger, genuinely runnable public
AndroidWorld system that was missed. Prefer official primary artifacts.

Then produce the final executable research design. It must specify:

1. the prioritized arm list and the exact artifact/model revision for each;
2. which arms belong in a same-backbone diagnostic lane and which belong only
   in a native-system or privileged-observation table;
3. a frozen non-Hard integration smoke followed by the 19-task Hard breadth
   stage and, if justified, two-seed confirmation;
4. non-performance-based qualification and expansion gates;
5. task, seed, step, token, model-call, reset, rerun, contamination, and stop
   rules;
6. normalized task and process metrics, including exact-action loops,
   feedback-to-next-action change, wrong-target/destination errors,
   action-effect failures, and evaluator-rejected finish claims;
7. a realistic day-by-day execution schedule using one Windows Android host
   and an eight-RTX-4090 model server;
8. the exact conclusions permitted if success becomes non-zero, remains zero
   but process metrics improve, or remains zero with no process improvement;
9. the minimum set of code/adapters/log schemas that Codex must implement next;
10. a final `GO`, `GO_WITH_REVISIONS`, or `NO_GO` verdict for launching model
    calls.

Preserve every old frozen result. Do not authorize edits to the protected r79
working files listed in the JSON protocol. No failed smoke or repeatedly
debugged Hard task may later be presented as held-out evidence.

Return exactly one self-contained Markdown document. Put all analysis,
corrected tables, the final protocol, execution order, and verdict in that one
document. Do not ask follow-up questions and do not output any text outside the
Markdown document.
