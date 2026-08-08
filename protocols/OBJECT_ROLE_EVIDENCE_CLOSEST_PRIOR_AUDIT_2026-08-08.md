# Object-role evidence qualification: closest-prior audit

Date: 2026-08-08  
Status: frozen decision before any new implementation or generation call

## Question left by the L4 negative result

The matched L4 diagnostic showed that suppressing semantic claims after an observably unchanged action was insufficient. In the `OsmAndTrack` intervention, the agent produced genuine screen transitions while using ordinary place search, but later treated those visits as if the places had been inserted into the route editor. The residual question is therefore narrower than action-effect verification:

> When a GUI transition is real, does the observed transition have the correct object role and evidence type to prove the current subgoal predicate?

For example, `location_visited(place)` is not evidence for `waypoint_added(route, place)`, even though both actions may visibly open the same place.

## Closest prior work

### Task-State Representation (TSR)

[A Task-State Representation for Long-Horizon Mobile GUI Agents](https://arxiv.org/abs/2607.00502) already combines a global task summary, a four-field subgoal progress tracker, and transition-aware verification based on pre/post screenshots in a training-free wrapper. It is therefore the closest prior to any proposal framed merely as structured progress plus transition verification. Its own limitation section states that an updater can wrongly mark a subgoal complete and propagate the error. Its AndroidWorld ablation is also cautionary: the full representation reduces Qwen3.5-plus from 61.21% to 57.76%, while removing the transition component reaches 63.79%. Thus a generic TSR replication is valuable as a baseline, but not a new RAVEN-M contribution.

### VeriGUI action-effect verification

[Don't Act Blindly: Robust GUI Automation via Action-Effect Verification and Self-Correction](https://aclanthology.org/2026.acl-long.1335/) predicts an expected effect, verifies the following screen as `SUCCESS` or `NO_CHANGE`, and binds the result to recovery. This occupies the general claim that agents should not assume an action succeeded and should use the observed effect to guide the next action. The L4 intervention is best described as a much smaller diagnostic instance of this family, not a novel method.

### StepReflect

[StepReflect: Structured UI Transition Reflection for Mobile GUI Agents](https://arxiv.org/abs/2608.05587) treats per-step reflection as structured prediction from an explicit transition specification and paired visual evidence. It reports 82.16% transition-level accuracy on AndroidWorld and integrates the reflector with several agents. This further occupies generic structured transition reflection and shows that the main research frontier is already beyond binary pixel change.

### VeriSafe Agent

[VeriSafe Agent: Safeguarding Mobile GUI Agent via Logic-based Action Verification](https://arxiv.org/abs/2503.18492) translates user intent into logical constraints, obtains anticipated state transitions from developer instrumentation, and checks an action before execution. This occupies the broad claim that preconditions or action-intent consistency should be verified before allowing an action. Its developer-defined state interface is stronger than screenshot-only evidence but less portable.

### Subtask-level verifiability

[VeriGUI: Verifiable Long-Chain GUI Dataset](https://arxiv.org/abs/2508.04026) defines independently verifiable subtask goals for long trajectories. It occupies the broad evaluation claim that final reward alone is insufficient and that subgoals should have their own verifiable goal functions.

## Novelty boundary

The following claims are already occupied or too close to prior work:

- maintain a structured task summary and progress tracker;
- compare pre/post screenshots after each action;
- predict an expected visual effect and recover on mismatch;
- verify action preconditions or intent consistency;
- attach verification to individual subtasks.

The only residual hypothesis not established by the current audit is narrower:

> A transition should update a subgoal only when its evidence predicate is type-compatible with the required object role, not merely because the screen changed or a semantically related entity appeared.

This is not yet an innovation claim. It may collapse into TSR's updater, VeriSafe's logical state model, or a standard typed planning representation once inspected more deeply. It also has no prevalence estimate in the 57-key official baseline.

## Frozen decision

1. Do **not** implement or name a Destination-First Binding Gate.
2. Do **not** present object-role qualification as a method contribution.
3. First run a zero-generation retrospective prevalence audit over the frozen official 57-key trajectories.
4. Count only cases where:
   - a real transition occurred;
   - the agent's history or reasoning promoted a stronger subgoal predicate;
   - the observed transition only supported a weaker or differently typed predicate;
   - the mismatch is causally upstream of later failure or false completion.
5. Only if this pattern occurs in at least three task classes and at least two application families may a new matched diagnostic be preregistered.
6. Any later intervention must be compared against TSR, VeriGUI/StepReflect-style transition verification, and precondition checking; it cannot claim novelty from structure or verification alone.

## Immediate next artifact

Generate a review queue from the frozen 57-key logs, then manually label candidate steps with:

- required predicate;
- observed predicate;
- object role;
- whether the screen transition was genuine;
- whether the stronger progress claim entered history;
- whether that claim was causally used later;
- earliest broken layer.

No GPU generation is authorized by this audit.
