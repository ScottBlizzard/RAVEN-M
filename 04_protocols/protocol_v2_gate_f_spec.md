# Protocol-v2 Gate F frozen execution specification

Gate F is a twelve-cell paired Hard micro-gate over six preregistered task
families. It uses seed `20260730`, B3 and M0, and the protocol implementation
that passed Gate E.

Execution is divided into three separately invoked batches of four cells.
Completing one batch never authorizes or launches the next. Each checkpoint
must be inspected before the user explicitly requests continuation.

The block order is frozen with Python's `random.Random(2026073001)`. Candidate
orders were tested in sequence; candidate 21 was the first order satisfying:

- exactly four cells per batch;
- exactly two B3 and two M0 cells per batch;
- no task pair appears within the same batch;
- no adjacent cells are variants of the same task.

The final order is stored in
`05_project/configs/experiments/v2_hard_micro_gate.json`.

All six task instances are generated and hashed before batch 1. Each later
variant must reproduce the frozen goal and parameter hashes. Results are
written atomically after every valid cell. Infrastructure-invalid attempts
are archived and never counted.

Image-valued task parameters are canonicalized by image mode, dimensions, and
pixel-content SHA-256. Process-local PIL object addresses are never part of a
pairing hash or persisted instance snapshot.

The 3.5-hour cap applies to cumulative active execution across all batches.
Projected total time uses completed-cell wall time relative to the frozen v1
per-cell baseline, plus the scaled baseline for remaining cells.

Gate F is a feasibility gate, not evidence that M0 is superior. Gate G remains
disabled unless all twelve cells finish and every frozen Gate-F criterion
passes.
