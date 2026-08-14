# A1-R6 Goal-Anchored Pending Ledger Preregistration

Parent evidence is commit `87d665a1021c6a1479bcbd80ff6a1716dd8f6cd8`. A1-R5 removed stale page guidance and deleted one of three required expenses, but at the first Tuition Fees encounter its self-authored ledger incorrectly reduced pending work to Bike Repairs merely because Tuition Fees had been located. It then repeatedly opened and exited Tuition Fees detail.

A1-R6 inherits R5 and adds exactly one bounded invariant to each memory read: the original goal (whitespace-normalized, at most 320 characters) plus the rule that every requirement remains pending until visibly confirmed complete and locating/opening is not completion. The current screenshot remains authoritative. This is a ledger-correctness rule, not an action recommendation; it adds no call, guard, override, forced stop, hidden input, task whitelist, or budget change.

The same six A1-R2 successes run first in frozen order. Any valid reward failure stops the arm; only 6/6 releases the remaining thirteen without rerunning the gate. Full accuracy requires at least 7/19, reward above 6.5, and all six preserved. Cost and causal verdicts are separate.
