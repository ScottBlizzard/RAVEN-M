# Protocol-v2.2 r47 M0 Contacts smoke

Date: 2026-07-30  
Source: `32983e6767d7e47d2357bdbf87ee5f3863078cc7`  
Decision: **valid development attempt; candidate rejected**

## Outcome

The isolated, non-scored M0 `ContactsAddContact` smoke ended with native reward
0 after three executed steps and six model calls. The runner stopped on
`MODEL_OUTPUT_INVALID_AFTER_REPAIR`. Startup was classified clean and the
attempt produced a complete native evaluation, so this is a valid task failure
rather than an infrastructure-invalid attempt.

The task-scope repair remained live-qualified: the Planner required only
`Sofija Martin` and `+17634322348`, and no company, email, note, placeholder,
or other optional value appeared. The r47 input-activation exception was not
reached; its live override count remained zero.

## Causal trace

1. The emulator initially suffered slow accessibility recovery. Contacts
   eventually opened and exposed an 11-element accessibility state.
2. The model tapped the visible add-contact `+` control at `(0.87, 0.835)`.
3. The touch was visibly delivered, but the page remained on `No contacts yet`.
   Pixels changed only because of transient touch instrumentation; the semantic
   digest correctly remained unchanged.
4. The next policy response repeated the same tap because the visible control
   was still the only direct route to the required form.
5. `UNVERIFIED_PROGRESS_REPEAT_REQUIRED` blocked that first-pass response.
6. The bounded repair prompt required a materially different control. The
   model again returned the same visible `+` tap, so the same guard blocked it
   a second time and the runner failed safely.

No contact mutation, text input, or unsafe action executed. The native
evaluator returned 0 because the form never opened.

## r48 boundary

A justified r48 may admit exactly one repeated tap only when all of the
following are true:

- the initial validation error is the immediately preceding unverified-progress
  exact-repeat guard;
- the repaired action is exactly the same tap on the unchanged semantic page;
- accessibility evidence binds that coordinate to a visible, enabled,
  clickable, non-editable control with a non-empty accessible label;
- the label is not a commit-like control such as Save, Delete, Send, Confirm,
  Copy, Move, Buy, Pay, Install, or Submit;
- no visible failure is present; and
- the allowance is audit-counted and cannot admit a third identical tap.

The existing r47 input-field activation exception remains separate. No swipe,
long press, text action, open-app action, terminal response, unknown/unlabelled
target, or commit-like control may use the new allowance.

## Infrastructure observations

The run took 1,141.875 seconds, with 22 readiness observations and 15 retries.
AndroidWorld temporarily lost the accessibility tree and hit ADB timeouts
during app launch and teardown. The runner nevertheless recovered before the
scored interaction, recorded accessibility semantics for the relevant
Contacts steps, completed native evaluation, and reported zero infrastructure
attempts. These delays explain runtime but do not explain the final guard
conflict.

## Evidence hashes

- `suite_summary.json`:
  `e0e186f567d7c4a6fde4b41f54e624bcf502523886e77ddb892bd80063892496`;
- `manifest.snapshot.json`:
  `a9e6e394031d60647d10d72fe661e461c987f10d8464340e5e68840d3c9c1a55`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- `startup_environment_audit.json`:
  `ad3516cef5334a2a9a0fd94df40ea9215ee4432c8a094478eaf84081cf5a4a48`;
- episode:
  `e9c2b46614490fc756784e7c124731aae73838e5c3a47ba04df7d6dcb076af39`;
- events:
  `e74c8a84bbb3ab75f8a80b534db0cba6ea2a795be7f1da2d2a6c37e8bb581adb`;
- pre-/post-tap screenshots:
  `01187e4fc1947395df5ab04fda8b52928dfcbcad23432b211f874e6cc6bdb572`
  and
  `a70e12aad82cbdcb3de285a9cb798bcf8d5aaeb6ab32bf72f4b946ba9efaa506`.

This is development evidence only and is not pooled with r45 or any formal
paired result.
