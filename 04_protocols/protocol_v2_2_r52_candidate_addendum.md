# Protocol-v2.2 r52 development-candidate addendum

Status: live attempt invalidated by stale before-decision accessibility;
candidate frozen

This addendum follows the immutable r51 development smoke. It preserves
r51's exact destination content-label binding, r50's live-qualified
source-exit behavior, the one-commit boundary, and all prior protocol
artifacts.

## Post-activation clear-text focus proof

The r51 smoke exposed a pre-commit input-safety failure. A bounded repair
clicked the visible Android Files Search input. The following screenshot
contained the soft keyboard, but accessibility did not expose an actually
focused editable node. The next coordinate-bearing
`type_text(clear_text=true)` was repaired by removing x/y while preserving
`clear_text=true`. AndroidWorld's Ctrl+A clear operation reached the
surrounding storage-root grid and selected all 14 folders instead of clearing
Search.

r52 adds one post-activation clear-text rule. While a one-step input
activation proof is pending, `type_text(clear_text=true)` is rejected unless
current accessibility contains an actually focused editable node. A soft
keyboard alone is explicitly insufficient evidence for Ctrl+A.

The bounded repair contract requires:

- `action.type=type_text`;
- the exact same text, `text_origin`, and `source_memory_ids`;
- no x or y; and
- `clear_text=false`.

The controller supplies no text or coordinate. A repair that retains
`clear_text=true`, changes text authority, adds a coordinate, taps, or
navigates is rejected before execution. The guard persists its focused-input
assessment, coordinate-target assessment, blocked action, semantic-state
hash, and post-activation clear-text block count.

## Preserved boundary

The rule does not apply without a pending bounded activation proof or when
accessibility proves an actually focused editable node. Coordinate-free
non-clearing text input after a valid activation remains available. r51's
destination content-label logic, r50's source-exit logic, exact-target,
field-role, text provenance, keyboard, loop, readiness, completion,
action-budget, model-budget, memory, evaluator, and Protocol-v1 behavior are
unchanged.

## Qualification boundary

The deterministic full-chain regression reproduces the r51 shape: unfocused
editable, activation-tap repair, soft keyboard without a focused editable,
and a second `clear_text=true` proposal. The unsafe action is not executed;
the sole valid repair keeps the exact task text and authority, removes x/y,
sets `clear_text=false`, executes once, and consumes the activation proof.
A negative repair regression proves that retaining clear mode cannot pass.
An actual-focused-editable unit case proves ordinary clear behavior is
preserved.

The exact candidate passed 392/392 project tests, 142/142 focused guard,
controller, and full-memory-policy tests, `compileall`, `git diff --check`,
and the unchanged 197/197 Protocol-v1 breadth seal.

The authorized fresh, isolated, non-scored M0 `FilesMoveFile` attempt stopped
at step 3 before Search or MOVE. Cross-modal review invalidated the attempt:
the drawer-closed storage-root screenshot changed across 35.875270% of
pixels, while its accessibility hash and nine-element tree remained exactly
the prior open-drawer state. The existing roots-drawer guard therefore
rejected an action against UI evidence that was no longer current.

r52 is frozen and may not be resumed. A future r53 is bounded to requiring
Protocol-v2.2 before-decision accessibility freshness against the previous
after-action pixels and semantic hash, plus retaining that readiness audit on
invalid-output steps. No action rule, budget, or r52/r51/r50 branch may
change. This does not authorize formal Gate E or Gate F.

