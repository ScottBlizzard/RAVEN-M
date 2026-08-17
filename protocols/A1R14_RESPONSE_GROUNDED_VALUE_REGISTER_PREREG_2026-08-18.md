# A1-R14 response-grounded value register protocol

Date: 2026-08-18
Status: prospective, pre-generation
Parent evidence commit: `b1523abcad250d6193c75fdde02ad92cd8e9ff10`
Mechanism ID: `a1r14_response_grounded_value_register_v1`
Experiment ID: `A1R14_RGVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`

## 1. Evidence-driven change

A1-R13D's Browser trace contained all five explicit observations in the model's
own Thought text (`1, 8, 10, 7, 2`) but EVR-v1 rejected them.  Its condition
incorrectly required collection and arithmetic words in the same `pending=`
field, while the live model placed collection locally in `pending=` and the
arithmetic objective in the stable task goal.  The fifth value appeared only in
Thought because that Action omitted a MEMORY prefix.

A1-R14 makes one bounded change: the goal establishes a collection-plus-
arithmetic episode, and a frozen set of observation-phrase regexes may retain
one unambiguous integer from the model's already-generated Thought text.  It
does not parse arbitrary numbers.  Counts such as “click 5 times” or “4 more”
are rejected unless they occur in an explicit current/seen-number observation
phrase.

## 2. Pure-memory boundary

Inputs are the goal and the same Qwen response already produced for the normal
decision.  There is no additional call, OCR, UI tree, evaluator, screenshot
parser, arithmetic, task identity, action override, guard, or forced
termination.  Current screenshots remain authoritative.  State is episode-
local, at most six integer strings, and expires under the inherited eight-
request bound.  Rendering is the exact R2 text followed by the frozen factual,
unverified sequence suffix.

## 3. Frozen gates and order

Run `BrowserMultiply` first.  It must achieve reward 1 after exactly one
activation, five retained response-grounded values, and an exact committed read
containing `[1, 8, 10, 7, 2]`.  Failure is terminal and is not rerun.

Then run the six R2 successes in frozen order.  Each must retain reward 1 and
have zero value-register activation/render.  Only then run the remaining twelve
tasks.  Scientific failures are retained; only infrastructure-invalid attempts
may be replaced under the bounded shared rule.

## 4. Offline authorization

The committed zero-generation fixture contains all 19 SYS-NAG-V4 episodes,
with Browser replaced by the sealed A1-R13D target trace.  Replay must show one
active episode (Browser), exact response append count five, an exact five-value
read, zero activation on the six successes and all other tasks, zero generation
calls, and audit size below 128 KiB.

## 5. Claims

Browser success is candidate support for response-grounded value retention, but
remains ablation-unresolved.  A committed five-value read followed by Browser
failure refutes sufficiency on that run.  Silent successes are not attributed to
the mechanism.  The study is same-seed matched exploratory evidence, not held-
out generalization.  Any semantic change after first valid generation requires
a new identity.
