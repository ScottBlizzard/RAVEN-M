# Protocol-v2.2 r46 M0 Contacts smoke

Date: 2026-07-30  
Source: `c60997750e039be06e958aac614f52d4196fdf83`  
Decision: **valid development attempt; candidate rejected**

## Outcome

The isolated, non-scored M0 `ContactsAddContact` smoke ended with native reward
0 after four executed steps and seven model calls. It was not an
infrastructure failure. The runner stopped on
`MODEL_OUTPUT_INVALID_AFTER_REPAIR`, exactly as required by the development
gate policy.

r46's intended task-scope behavior did work. The only Planner variables were
`Sofija Martin` and `+17634322348`; no company, email, note, placeholder, or
other invented payload appeared in a model response.

## Causal trace

1. Contacts opened and the add-contact form loaded.
2. The model tapped the empty First name field at `(0.49, 0.387)`.
3. Pixels changed and the visible field border became blue, but the
   accessibility semantic digest did not change and no keyboard appeared.
4. The next response proposed `Sofija` with the correct task-literal
   provenance, but used the same coordinate with `clear_text=true`.
5. `UNFOCUSED_CLEAR_TEXT_GUARD` correctly blocked the possible click/Ctrl+A
   race and required a separate activation tap.
6. The bounded repair returned that exact tap.
7. `UNVERIFIED_PROGRESS_REPEAT_REQUIRED` rejected it because the immediately
   preceding policy action was the same tap and had claimed progress without
   semantic change.

Neither the unsafe text action nor the repair tap executed. The failure is a
conflict between two conservative contracts, not an incorrect task value and
not a VPN/model/emulator outage.

## r47 boundary

A justified r47 may let only a tap generated under an active
`UNFOCUSED_CLEAR_TEXT_GUARD` repair contract bypass the immediately preceding
unverified-progress exact-repeat check. The allowance is bounded because:

- it applies only to a repair response, never an ordinary policy step;
- the action must remain a tap;
- an exact-repeat bypass is possible only when the prior fingerprint matches;
- after execution, the existing input-activation proof becomes pending;
- the next policy step must type into the activated field or choose a
  materially different action; and
- another identical tap remains blocked by the post-activation guard and the
  ordinary no-effect fingerprint threshold.

No guard threshold, task budget, text provenance rule, or clear-text safety
rule should change.

## Evidence hashes

- `suite_summary.json`:
  `f3bec32200e2a275a1bce5324eb368fa478019a003be92bca7e8938e9ffdc94d`;
- `manifest.snapshot.json`:
  `ab205d18d851708b33b34cab8902a6f669bb1b404e8141f1d8f68efaf0d63fa5`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- episode:
  `f62e4a5bcb1e9a6f3aca5b432d102c1ef26106e4fa0ba875074c0088e09fc55c`.

This is development evidence only and is not pooled with r45 or any formal
paired result.
