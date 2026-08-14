# A1-R5 Transition-Invalidated Pending Ledger Preregistration

## Frozen parent and motivation

Parent evidence is commit `2b7e6b80d707682ac0f2d685b3dd293a53a4af78`. A1-R4 failed the first fixed capability task with reward 0 after 34 valid single-transport calls. It repaired initial prefix compliance but allowed a semantic ledger written on an earlier page to survive later material page transitions when subsequent responses omitted the prefix.

## Only prospective change

A1-R5 inherits A1-R4 byte-for-byte except for one deterministic lifecycle rule. After an executed action, if the response prefix was invalid, an active ledger exists, the screenshots have the same shape, and `changed_pixel_fraction_gt_5 > 0.001`, the active ledger is immediately retired. The next read contains only A1-R4's frozen writer reminder. A valid current response may update or replace the ledger normally and is not invalidated by this rule.

The mechanism uses only model-visible RGB transition statistics and the model's own response. It adds no model call, guard, action override, forced termination, UI-tree access, evaluator access, task whitelist, or step-budget change.

## Fixed prospective order and stopping

Run the six frozen A1-R2 successes first in their frozen order. Any scientifically valid reward failure stops the arm without rerun. Only a 6/6 gate releases the remaining thirteen tasks, without rerunning the first six. Infrastructure-invalid episodes are retained and resolved under the existing exact contract.

Full-suite accuracy requires at least 7 successes, reward greater than 6.5, and preservation of all six gate tasks. Cost and causal verdicts remain separate.
