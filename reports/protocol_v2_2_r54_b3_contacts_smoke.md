# Protocol-v2.2 r54 B3 Contacts development smoke

Date: 2026-07-31  
Source: `54adaf031abd87dc5c420bd1d8d07acc8c0a4b94`  
Tag: `protocol-v2-2-r54-local-candidate`  
Decision: **development smoke passed; Gate-D preparation allowed**

## Result

The single fresh, non-scored B3 `ContactsAddContact` smoke completed with
AndroidWorld native reward 1.0 and `success=true`.

- 10 policy decisions, 9 executed actions;
- 16 total model calls: 15 executor and 1 history;
- 5 first-pass decisions and 5 bounded-repair decisions;
- 23 readiness observations and 4 readiness retries;
- `valid_after_one_repair=true`;
- semantic-progress audit passed;
- zero executed blocked actions, visible failures, unresolved repairs, or
  infrastructure attempts; and
- clean initial AndroidWorld startup.

The single-cell aggregate intentionally reports `gate_passed=false` because
it cannot satisfy the full 8-cell pairing, M0, information-retrieval-cache,
or minimum-total-success requirements. That is not an episode failure.

## Contact and input-safety trace

The agent entered only the required first name, last name, and phone number;
it did not fill Company or another optional field. At the critical phone
stage:

1. field-role binding rejected a proposed phone value aimed at Company;
2. the keyboard was dismissed without mutating Company;
3. `UNFOCUSED_CLEAR_TEXT_GUARD` converted direct phone typing into a pure
   Phone activation tap at step 6;
4. the next observed step entered `+17634322348` with no coordinates and
   `clear_text=false`;
5. Save executed at step 8; and
6. the native evaluator returned reward 1.0.

Both activation proofs were consumed (`2/2`) and no proof remained pending.

## r54 evidence boundary

The model used normalized `y=0.637` in this smoke, so the new
`MALFORMED_COORDINATE_INPUT_GUARD` did not fire live. Its safe-activation and
direct-text-denial branches remain qualified by deterministic regression
only. This is stated explicitly rather than converting a compatibility smoke
into live branch evidence.

The successful task confirms that r54 preserves the complete Contacts path
and the existing focus, role and optional-field safeguards. It permits
Gate-D preparation for the exact source. It does not itself authorize or
launch formal Gate E or Gate F, and it is not pooled with formal evidence.
