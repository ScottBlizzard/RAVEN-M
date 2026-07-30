# Protocol-v2.2 r48 M0 Contacts smoke

Date: 2026-07-31  
Source: `90916a46f678af38f3632d3d229e04bb5f23200d`  
Tag: `protocol-v2-2-r48-local-candidate`  
Decision: **development smoke passed; eligible for Gate-D preparation**

## Outcome

The isolated, non-scored M0 `ContactsAddContact` smoke passed with native
AndroidWorld reward 1.0. The model created `Sofija Martin` with
`+17634322348`, saved the record, observed the resulting contact page, and
then returned `done`.

The episode executed 8 actions using 15 model calls: 11 executor calls and 4
history-role calls. It required one consequential-action adjudication for
Save and one completion adjudication after Save. Both were accepted. The
semantic-progress audit passed with no visible failures, no executed blocked
actions, no unresolved guard repair, and no unhandled repeated no-effect
action.

The development runner exited 3 because a one-cell smoke intentionally cannot
satisfy the formal eight-cell pairing, B3, cache, and minimum-success criteria.
That exit is not an episode failure; `success=true` and
`evaluator_reward=1.0` are recorded in the suite result.

## Task grounding and action trace

The Planner froze exactly two required variables:

- `Sofija Martin`
- `+17634322348`

The model entered `Sofija`, `Martin`, and the supplied phone number from task
literals. It did not enter Company, Email, Note, a placeholder, or any other
optional value. Save was executed before completion was claimed, and the
post-save screen visibly contained the exact name and formatted number
`+1 763-432-2348`.

## r48 branch boundary

The first add-contact tap at `(0.87, 0.835)` initially produced no semantic
delta. Its post-action screenshot still showed `No contacts yet`. Before the
next policy decision, however, the delayed UI transition completed and the
Create contact form was visible. The next action therefore targeted First
name rather than repeating the add-contact tap.

Accordingly:

- `visible_control_activation_repeat_override_count=0`;
- no unverified-progress repeat block occurred;
- the new r48 allowance was not consumed live; and
- the allowance remains deterministic-branch-qualified, not
  live-trigger-qualified.

This distinction is deliberate. The smoke qualifies end-to-end compatibility
of the candidate, task-scope control, the separately preserved input-focus
repair, Save adjudication, completion adjudication, and native evaluation. It
does not claim that the r48 branch fired. The exact r47 failure shape remains
covered by the passing full-chain regression, including one admitted repair
and a blocked third identical tap.

## Infrastructure accounting

Initial environment construction failed when AndroidWorld's accessibility
forwarder APK install timed out twice. The runner classified this as
`INFRA_ENVIRONMENT_CONSTRUCTION`, cold-recovered the emulator, and recorded
attempt 2 as successful before the episode began.

The startup audit therefore contains one failure and one recovery success,
with final status `recovered`. The valid episode then ran for 326.488 seconds;
the complete invocation, including recovery, took 792.908 seconds. It used 19
readiness observations and 2 readiness retries.

## Evidence hashes

- `suite_summary.json`:
  `f14892eb90f67941d7dbff14b88e920d27553636bbb27856891cae9548503251`;
- `manifest.snapshot.json`:
  `e9fc462c2305b014be57df827a18bfd6b8a656ba540465ed1532fc856c33d410`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- `startup_environment_audit.json`:
  `b723299d539f1e22ec5d3831f306bd10bb0de997d61ea568e5bed6d463aa4f65`;
- episode:
  `b78d9338bbed380ea7ec08d142430deba88ebd3bc81852956ca547002da5228d`;
- events:
  `5d223b19876287490b639375c7c23fb254b71061a13f5a2fec6dcbf9f3911a44`;
- pre-/post-add-contact screenshots:
  `df4ca77cce977c3374cf0eb93bbe0fb5ceaa76a1094afb236464cc5795c25af4`
  and
  `bc0e01fc252037a90b2f3e1d6949c23e0eb0547d86e2a55da2bbfb6f7af831a4`;
- delayed form screenshot:
  `d8bfe5fb47d916c6bbb0842b526f5159b1a3e2adee1420974a1e266dd6a4587d`;
- saved contact screenshot:
  `b25546fdc245a7885c395b015ea77d1ce5761a5934f89b2f533611683c9c3c54`.

This is development evidence only and is not pooled with any formal paired
result.
