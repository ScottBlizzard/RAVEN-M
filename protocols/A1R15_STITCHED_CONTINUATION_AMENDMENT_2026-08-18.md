# A1-R15 post-terminal stitched continuation amendment

Status: prospective scheduling amendment, frozen before any continuation generation.

This amendment does not alter or reopen the sealed A1-R15 Browser episode.  The
memory mechanism remains `a1r15_explicit_observation_value_register_v1`, with the
same prompt, parser, controller semantics, model revision, sampling, seeds, and
native task budgets as implementation commit
`c21cad1d5456c37cf72fa677d5fa08d2d8f28665`.

The historical Browser result is imported only as immutable evidence.  It stays
classified `TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED`: EVR retained
only `[8,2]`, rendered/read no values, and receives no causal credit.

The continuation runs these six tasks, in order, without scientific fail-fast:

1. ExpenseDeleteMultiple2
2. RetroSavePlaylist
3. SimpleCalendarAddOneEvent
4. SportsTrackerTotalDurationForCategoryThisWeek
5. RecipeDeleteMultipleRecipesWithConstraint
6. OsmAndMarker

Valid model failures are retained and do not stop those six.  Only a retained,
hash-bound infrastructure-invalid attempt may be replaced.  Browser is never
rerun.  If and only if the imported Browser reward is 1 and all six continuation
tasks have reward 1, the remaining twelve tasks from the original A1-R15 order
are released, without rerunning the first seven.  Otherwise the continuation is
sealed after six and the twelve are `NOT_RUN_BY_PROTOCOL`.

This is a transparent post-hoc stitched behavioral diagnostic, not the original
prospective target-gate continuation, not held-out evidence, and not proof that
EVR caused any success.  Component-silent successes are unattributed.
