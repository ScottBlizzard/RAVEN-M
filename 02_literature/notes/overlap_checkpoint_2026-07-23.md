# RAVEN-M overlap checkpoint — 2026-07-23

Status: **proceed with narrowed claims**

## Decision

RAVEN-M remains suitable as a high-quality summer-camp research prototype, but
the refreshed 2026 literature makes a broad paper-style novelty claim
untenable. Training-free GUI memory, multi-role orchestration, state tracking,
trajectory retrieval, utility-based pruning, and graph/executable memory are
all occupied by close prior work.

The project therefore evaluates a deliberately narrower question:

> Under a frozen AndroidWorld protocol and identical model, action, context,
> and call budgets, does episode-local memory with item-level evidence,
> verification, explicit invalidation, and reliability routing reduce harmful
> memory use relative to raw history and simple summary?

The result is valuable even if Task Success Rate does not improve, because the
protocol measures why memory helps or harms rather than treating memory as an
unqualified benefit.

## Highest-overlap works

| Work | Occupied contribution | Consequence for RAVEN-M |
|---|---|---|
| Darwinian Memory (2026 preprint) | training-free self-regulating GUI memory; utility selection; pruning stale/high-risk experience | do not claim training-free updating or stale-memory pruning as novel |
| EchoTrail-GUI (CVPR 2026 Findings) | critic-validated successful trajectory memory; retrieval and injection; AndroidWorld | do not claim critic-validated experience retrieval as novel |
| CES (CVPR 2026) | Coordinator–Executor–State Tracker; context compression and task-state coherence | do not claim role separation or state tracking as novel |
| MAGNET (ACL 2026) | stationary/procedural dual memory and evolution under UI changes | avoid dual/hierarchical memory novelty and UI-evolution claims |
| HyMEM (ACL 2026 Findings) | hybrid symbolic/continuous graph memory, multi-hop retrieval, evolving updates | keep the implementation bounded and non-latent; no global graph |
| UI-Copilot (ACL 2026) | learned invocation of memory and calculation copilots; AndroidWorld | distinguish deterministic routing and matched call budget |
| D-Artemis (ACL 2026 Findings) | training-free tips, pre-action correction, post-action reflection | distinguish item provenance/lifecycle and memory-harm audit |
| Executable Agentic Memory (2026 preprint) | structured KG, executable routines, value-guided search; AndroidWorld | do not claim executable graph planning or structured KG novelty |
| ExpAct (ICML 2026) | structural/procedural experience construction, refinement, retrieval; AndroidWorld | keep cross-episode procedural reuse outside the core |
| MemGUI-Bench (2026 preprint) | memory taxonomy, memory-centric tasks and hierarchical metrics | use it to justify diagnostics; do not claim a new memory benchmark |
| HAR-GUI (AAAI 2026) | trained history-aware reasoning and action-summary supervision | emphasize fixed-model, external, training-free comparison |
| PG-Agent (ACM MM 2025) | Page Graph and graph-based mobile GUI planning | Page-State Index must remain a small episode-local index, not a Page Graph contribution |

## Defensible project contribution

The core is an auditable experimental package, not a claim to have invented
memory for GUI agents:

1. every active memory item has a source screenshot/action pointer, status,
   scope, reliability score, and append-only lifecycle events;
2. memory can be marked contradicted, stale, superseded, or invalidated by
   observable events, and these states affect retrieval;
3. Hard-task memory is strictly episode-local, preventing reward or trajectory
   leakage across scored episodes;
4. stale/contradictory memory use, memory-induced errors, loops, premature
   completion, and recovery are first-class outcomes;
5. B0/B1/B2/B3/RAVEN comparisons share the same task instance, native action
   budget, 8192 context cap, model checkpoint, evaluator, and explicitly
   matched context/call controls.

## Required method constraints

- No global Page Graph, latent memory encoder, or MCTS executable knowledge
  graph.
- No Hard-derived procedural memory reused in another scored Hard episode.
- Deterministic Memory Manager first; model calls are event-triggered and fully
  counted.
- The screenshot remains the primary evidence. Memory is a fallible,
  auditable hypothesis unless independently verified.
- Claims must be conditioned on the frozen 19-class protocol and report paired
  uncertainty; no "first", "general", or universal reliability wording.

## Eagle Lab alignment

Sheng Zhou's official publication list shows a coherent GUI line: MP-GUI
(perception), PG-Agent (structured page representation), HAR-GUI (history),
ProBench (process evidence), and LAMO (multi-role orchestration). The
accessibility work additionally emphasizes reliable, actionable, user-facing
evidence. RAVEN-M should therefore prioritize a complete auditable artifact,
controlled evaluation, and process-level explanation over architectural
complexity or inflated novelty.

## Source status

- Official proceedings/source metadata verified for EchoTrail-GUI and CES.
- Official Sheng Zhou homepage rechecked on 2026-07-23.
- Darwinian Memory, Executable Agentic Memory, and MemGUI-Bench are clearly
  labeled preprints.
- ExpAct's ICML 2026 OpenReview metadata is recorded; local PDF retrieval is
  blocked by HTTP 403 and is not marked downloaded.
