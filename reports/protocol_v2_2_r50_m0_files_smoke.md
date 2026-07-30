# Protocol-v2.2 r50 M0 Files smoke

Status: **native task PASS; r50 source-exit branch live-qualified; destination-navigation branch still over-constrained; Gate D withheld**

Candidate:
`protocol-v2-2-r50-local-candidate` /
`ac8d6ece831a18a55d86d82f940faf152669694a`

Suite:
`nonhard_capability_v2_2_seed20260729_r50_candidate_development_smoke_sequence_4`

## Result

The fresh, isolated, non-scored M0 `FilesMoveFile` smoke moved
`nature_sounds.mp3` from `Music` to `Ringtones`. AndroidWorld returned native
reward 1.0. Exactly one bottom MOVE commit executed, no later transfer or
selection mutation executed, all 20 actions had semantic audit records, all
responses were valid after at most one repair, and there were no recorded
infrastructure attempts.

r50's new source-exit rule was consumed live at step 17. Android Files still
showed the exact task source `Music` in its top navigation region after the
commit. The proposed source-folder swipe was rejected before execution, the
sole repair returned exactly `press_back`, and Back reached the storage root.

At step 18 the policy summary incorrectly referred to `Music`, but its actual
tap coordinate overlapped the exact visible `Ringtones` label. Android Files
entered `Ringtones`, and step 19 visibly contained the moved file. The r49
destination-navigation assessment nevertheless returned `permitted=false`
because the exact label hit had no separately exposed clickable accessibility
container. The action was therefore still classified by the generic
consequential-action heuristic instead of the narrow navigation binding.

The run ended at `max_steps`: a completion proposal at step 19 was rejected
because the Android Files grid clipped the full filename, and the bounded
repair pressed Back. This does not undo the native task success, but it is not
an evidence-backed terminal decision. Gate D is withheld.

## Bounded r51 scope

A justified r51 may modify only the post-commit destination-navigation
assessment. A tap may be treated as task verification navigation when:

- one destination commit has already executed;
- the destination picker is inactive;
- the tap overlaps the exact task `destination_folder` label;
- the exact label belongs to Android Files, is visible, enabled, noneditable,
  and has a valid accessibility bounding box;
- the exact-label hit is below the top 20% navigation/breadcrumb region; and
- the tapped label is not a commit control.

The content-region constraint excludes a current-directory title or
breadcrumb. A separately exposed clickable ancestor may remain audit evidence
but cannot be mandatory because the real Android Files root row does not
provide it.

r51 must preserve r50's live-qualified source-exit rule, the one-commit
boundary, all second-mutation blocks, and all non-Files/wrong-label/top-region
denials. It requires complete local and Protocol-v1-seal validation, a new
source tag, a zero-call preflight, and at most one fresh isolated M0 Files
smoke. r50 is immutable and may not be resumed. Formal Gate E and Gate F
remain unauthorized.

