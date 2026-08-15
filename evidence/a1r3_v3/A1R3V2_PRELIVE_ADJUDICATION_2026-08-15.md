# A1-R3-v2 CNR pre-live adjudication

Status: `DESIGN_REJECTED_PRELIVE`

The GPT Pro A1-R3-v2 design was reviewed against the complete local A1-R2 raw
suite before implementation or GPU generation.  The design is retained as a
useful falsifiable proposal, but its frozen identity is not modified or run.

Applying its exact two-support trigger, action families, threshold, cooldown,
and per-episode cap of three to the 19 valid A1-R2 episodes produced:

- zero receipt creations and zero CNR reads on all six A1-R2 successes;
- receipt exposure on eight failed tasks;
- 19 receipt creations and 18 next-request reads;
- projected rendered-memory characters of 109,141 versus A1-R2's 108,423.

The v2 protocol required total receipt creations in `[3, 11]` and projected
characters no greater than 108,423.  Both gates fail.  Therefore v2 is closed
without implementation or live generation.  Its thresholds and identity must
not be silently changed.

The successor A1-R3-v3 uses this result as development/calibration evidence,
not independent confirmation.  It creates a new identity and reduces the
intervention to a single attributable temporal fact per episode.
