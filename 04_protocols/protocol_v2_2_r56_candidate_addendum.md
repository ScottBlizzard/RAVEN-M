# Protocol-v2.2 r56 development-candidate addendum

Date: 2026-07-31  
Source: `24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`  
Tag: `protocol-v2-2-r56-local-candidate`

## Motivation

The valid r55 M0 Files development smoke reached a search-results grid in
which accessibility exposed the exact task-literal filename
`nature_sounds.mp3`, while the screenshot clipped several same-prefix
filenames. Four unsafe neighbor long presses were blocked. On the final
decision, the model's repair toggled Search again and was correctly rejected
as part of an A-B no-progress cycle.

The failure is narrower than general file selection: the exact target is
known to exist, but the current visual layout does not safely bind its full
accessibility label to the model's proposed coordinate. A reversible layout
change can make the text easier to distinguish without selecting or mutating
any file.

## Trigger

r56 specializes the sole model repair only when every condition below holds
on the unchanged screenshot:

1. protocol-v2.2 and `FilesMoveFile` selection semantics are active;
2. the initial response is a long press rejected by `EXACT_TARGET_GUARD`;
3. the exact task-literal filename is visible in accessibility;
4. at least two extension-matched file candidates are visible;
5. the proposed coordinate is not bound to the exact filename; and
6. exactly one visible, enabled, clickable, noneditable Android DocumentsUI
   control is semantically identified as the list/grid view-mode toggle.

The control must belong to `com.google.android.documentsui`. Recognition is
based on a bounded list/grid label or action/menu/mode/view resource identity,
and duplicate nodes sharing one bounding box count as one control. Zero or
multiple distinct controls do not qualify.

## Repair contract

The qualified repair must:

- use `status=continue`;
- contain exactly one pure `tap` action with only `type`, `x`, and `y`;
- hit the sole accessibility-grounded view-mode control;
- keep `state_delta`, `memory_citations`, and `completion_evidence` empty; and
- observe a fresh screen before any later file-selection attempt.

The repair cannot Search, type, swipe, long-press, select a file, navigate,
commit, finish, or claim that the layout has already changed. The controller
does not calculate or disclose a replacement coordinate; the model must bind
its tap from the unchanged screenshot, and the controller independently
checks the returned coordinate against accessibility.

## Preserved boundaries

r56 does not:

- authorize a long press whose coordinate is not bound to the exact full
  filename;
- bypass the existing loop guard or grant an extra model repair;
- treat a task intention, model statement, or memory hypothesis as proof that
  a file is selected;
- weaken text provenance, field-role, destination-picker, post-destination,
  or consequential-action adjudication;
- act when the exact target is offscreen or the view-mode control is absent or
  ambiguous;
- reuse, resume, or relabel the immutable r55 trajectory; or
- authorize formal Gate E or any automatic Gate F transition.

When the trigger is not fully satisfied, the existing conservative
`EXACT_TARGET_GUARD` repair path remains unchanged.

## Validation requirement

Before any live model call, r56 must pass:

- the exact r55 ambiguity shape with a view-mode repair;
- rejection of Search within the specialized repair;
- rejection of an otherwise correct view tap that claims unobserved progress;
- fallback when no view-mode control exists;
- package and multi-control ambiguity negatives;
- all protocol-v2 controller and full-policy tests;
- the complete local suite; and
- the unchanged 197-file protocol-v1 breadth seal.

One zero-model-call probe must also confirm that the actual AndroidWorld AVD
exposes exactly one compatible DocumentsUI view-mode control. Only after a
fresh exact-source preflight may one isolated non-scored M0 Files development
smoke be considered.
