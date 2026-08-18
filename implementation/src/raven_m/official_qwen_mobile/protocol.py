"""Qwen3-VL Mobile Agent prompt, parser, and coordinate adapter.

The prompt and user-message template are transcribed from
``cookbooks/mobile_agent.ipynb`` at ``OFFICIAL_QWEN_COMMIT``.  This module is
deliberately independent of RAVEN-M memory, planning, critic, and guard code so
the resulting arm is a faithful end-to-end Qwen baseline rather than another
custom controller variant.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Iterable


OFFICIAL_QWEN_REPOSITORY = "https://github.com/QwenLM/Qwen3-VL"
OFFICIAL_QWEN_COMMIT = "96588727e44c78b25ba03ea03b8e12f7e64fd0da"
OFFICIAL_QWEN_NOTEBOOK = "cookbooks/mobile_agent.ipynb"
OFFICIAL_GRID_MAX = 999.0
DEFAULT_SWIPE_DURATION_MS = 400

OFFICIAL_SYSTEM_PROMPT = r"""

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name": "mobile_use", "description": "Use a touchscreen to interact with a mobile device, and take screenshots.\n* This is an interface to a mobile device with touchscreen. You can perform actions like clicking, typing, swiping, etc.\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.\n* The screen's resolution is 999x999.\n* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.", "parameters": {"properties": {"action": {"description": "The action to perform. The available actions are:\n* `click`: Click the point on the screen with coordinate (x, y).\n* `long_press`: Press the point on the screen with coordinate (x, y) for specified seconds.\n* `swipe`: Swipe from the starting point with coordinate (x, y) to the end point with coordinates2 (x2, y2).\n* `type`: Input the specified text into the activated input box.\n* `answer`: Output the answer.\n* `system_button`: Press the system button.\n* `wait`: Wait specified seconds for the change to happen.\n* `terminate`: Terminate the current task and report its completion status.", "enum": ["click", "long_press", "swipe", "type", "answer", "system_button", "wait", "terminate"], "type": "string"}, "coordinate": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=click`, `action=long_press`, and `action=swipe`.", "type": "array"}, "coordinate2": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=swipe`.", "type": "array"}, "text": {"description": "Required only by `action=type` and `action=answer`.", "type": "string"}, "time": {"description": "The seconds to wait. Required only by `action=long_press` and `action=wait`.", "type": "number"}, "button": {"description": "Back means returning to the previous interface, Home means returning to the desktop, Menu means opening the application background menu, and Enter means pressing the enter. Required only by `action=system_button`", "enum": ["Back", "Home", "Menu", "Enter"], "type": "string"}, "status": {"description": "The status of the task. Required only by `action=terminate`.", "type": "string", "enum": ["success", "failure"]}}, "required": ["action"], "type": "object"}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

# Response format

Response format for every step:
1) Thought: one concise sentence explaining the next move (no multi-step reasoning).
2) Action: a short imperative describing what to do in the UI.
3) A single <tool_call>...</tool_call> block containing only the JSON: {"name": <function-name>, "arguments": <args-json-object>}.

Rules:
- Output exactly in the order: Thought, Action, <tool_call>.
- Be brief: one sentence for Thought, one for Action.
- Do not output anything else outside those three parts.
- If finishing, use action=terminate in the tool call."""


# Frozen post-hoc diagnostic intervention.  This is intentionally separate
# from OFFICIAL_SYSTEM_PROMPT so the published baseline remains byte-for-byte
# unchanged unless the runner explicitly opts in.
TRANSIENT_OBSERVATION_CARRY_SUFFIX = r"""

# Transient observation carry

- If the current screenshot contains a task-relevant value or label that will
  disappear after the next action, copy it exactly into the Action sentence.
- For such a step, use: Remember: <exact observation>; <imperative action>.
"""

TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT = (
    OFFICIAL_SYSTEM_PROMPT + TRANSIENT_OBSERVATION_CARRY_SUFFIX
)


# A1 is the first formal memory intervention on top of the official baseline.
# It reuses the official Action prose channel but turns it into an explicit,
# bounded, auditable within-episode working-memory record.
A1_WORKING_MEMORY_SUFFIX = r"""

# A1 explicit working memory

Begin every Action sentence, including answer or terminate steps, with exactly:
MEMORY[observed=<exact task-relevant facts visible now or none>; verified=<task requirements directly confirmed by the current screen or none>; pending=<most important unmet requirements>] | <one concise UI imperative>

Rules:
- Keep the complete MEMORY[...] payload under 450 characters.
- Copy exact names, numbers, dates, labels, and other values that may disappear after the next action.
- Mark a requirement verified only when the current screenshot directly proves it; an attempted click or page change is not proof.
- Do not invent missing facts. Use none when the current screen provides no support.
- On later steps, consult the explicit working-memory block in the user message. The current screenshot overrides stale or conflicting memory.
"""

A1_WORKING_MEMORY_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A1_WORKING_MEMORY_SUFFIX


# A1-R1 BPR v2 remains a separate prospective identity. Importing the literal
# from its mechanism module keeps one exact byte source without changing A1.
from .a1r1_bpr_v2 import A1R1_BPR_V2_SUFFIX  # noqa: E402

A1R1_BPR_V2_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A1R1_BPR_V2_SUFFIX


# A2 replaces A1's recency list with one compact, outcome-aware progress state.
# The expected field makes the next screenshot comparison explicit without an
# extra model call.  Controller-observed screen change is never called task
# success; the hidden evaluator remains unavailable until the episode ends.
A2_VERIFIED_PROGRESS_SUFFIX = r"""

# A2-v1r1 model-asserted screenshot-progress memory

Begin every Action sentence, including answer or terminate steps, with exactly:
PROGRESS[observed=<exact task-relevant facts visible now or none>; verified=<requirements you assert are visible in the current screenshot or none>; pending=<most important unmet requirements>; expected=<visible effect expected from this action>] | <one concise UI imperative>

Rules:
- Keep the complete PROGRESS[...] payload under 360 characters.
- Verified is your own screenshot-visible assertion, not a controller or evaluator confirmation; never use it for something merely attempted.
- State the concrete visible effect expected after the proposed action.
- Consult the compact progress block in the user message, but let the current screenshot override it.
- If the prior outcome says no visible change, inspect or choose a different target instead of repeating the same action.
- A page transition alone does not prove that the requested object, field, or final task state is correct.
"""

A2_VERIFIED_PROGRESS_SYSTEM_PROMPT = (
    OFFICIAL_SYSTEM_PROMPT + A2_VERIFIED_PROGRESS_SUFFIX
)


# A3 isolates the zero-shot Context-as-Action memory kernel from MemGUI-Agent.
# The same policy call updates compact context and selects the GUI action; no
# SFT model, extra planner, critic, or memory-model call is introduced.
A3_CONACT_SUFFIX = r"""

# A3 proactive folded-context memory

Begin every Action sentence, including answer or terminate steps, with exactly:
CONTEXT[folded_history=<compact completed operations and progress or none>; ui_state=<exact task facts that must survive page/app changes or none>; recent=<what the current screen says about the last operation>] | <one concise UI imperative>

Rules:
- Keep the complete CONTEXT[...] payload under 420 characters.
- Replace stale context instead of copying the whole trajectory.
- Preserve exact names, values, constraints, and still-pending requirements.
- The current screenshot overrides folded context; an attempted action or page transition is not task completion.
- Do not add a planner, critic, repair action, or hidden-state claim.
"""

A3_CONACT_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A3_CONACT_SUFFIX


# A4 keeps the official response format byte-for-byte and only teaches the
# policy how to interpret a frozen donor-only workflow block.  The bank is
# built before the scored Hard suite and is immutable during evaluation.
A4_WORKFLOW_SUFFIX = r"""

# A4 frozen procedural workflow memory

- A user-message workflow block, when present, comes only from an independent evaluator-confirmed donor task.
- Treat it as a reusable procedure, not as evidence that the current task is complete and never copy donor-specific values.
- Apply a step only when the current screenshot visibly supports the same operation.
- If no workflow is retrieved, act exactly as the official baseline.
- Do not add a planner, critic, reflection call, action guard, or controller override.
"""

A4_WORKFLOW_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A4_WORKFLOW_SUFFIX

A4V2_WORKFLOW_SUFFIX = r"""

# A4-v2 faithful offline workflow memory

- A user-message workflow block, when present, was induced offline from at least two independent-seed evaluator-confirmed non-Hard donor episodes on one exact reusable route.
- Treat it as optional reusable prior procedure, not as evidence that the current task is complete, and never copy donor-specific values.
- Apply a step only when the current screenshot visibly supports the same route subroutine; current pixels override workflow text.
- If no compatible workflow is retrieved, act exactly as the official baseline.
- Do not add a planner, critic, reflection call, action guard, or controller override.
"""

A4V2_WORKFLOW_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A4V2_WORKFLOW_SUFFIX


# A5 is deliberately named as an isolated in-trial graph adaptation.  Full
# HyMEM additionally requires an offline successful-trajectory graph, learned
# Q-Former continuous tokens, retrieval digestion, and self-evolution; those
# unavailable components are not silently approximated or claimed here.
A5_VISUAL_GRAPH_SUFFIX = r"""

# A5 online visual-symbolic transition-graph memory (HyMEM-inspired)

Begin every Action sentence, including answer or terminate steps, with exactly:
GRAPH[node=<semantic role of the current page>; relation=<visible transition or function expected from this action>; facts=<exact reusable facts visible now or none>; avoid=<a visibly unsupported edge to avoid or none>] | <one concise UI imperative>

Rules:
- Keep the complete GRAPH[...] payload under 420 characters.
- Retrieved edges are applicable only when their page evidence matches the current screenshot.
- Store exact visible facts and transition roles, never hidden app state or evaluator conclusions.
- An identical/near page can still contain changed values; current pixels always override graph memory.
- Do not add a planner, critic, action guard, or controller override.
"""

A5_VISUAL_GRAPH_SYSTEM_PROMPT = OFFICIAL_SYSTEM_PROMPT + A5_VISUAL_GRAPH_SUFFIX


# Frozen post-hoc mechanism diagnostic.  A visible transition is evidence only
# for the exact object role and postcondition that the screenshot supports; it
# is not automatically evidence of task progress.
EVIDENCE_QUALIFIED_PROGRESS_SUFFIX = (
    "\n\n# Evidence-qualified progress\n\n"
    "Evidence-qualified progress rule: Treat every action as ATTEMPTED until "
    "the current screenshot directly verifies the exact task predicate. A "
    "real screen transition is insufficient if the object type, parent "
    "hierarchy, field, container, or operation differs from the requirement. "
    "Before acting, state the intended object role and exact postcondition. "
    "After acting, compare visible evidence against those exact slots. Never "
    "promote a related weaker fact to completed progress. If exact proof is "
    "absent, keep the subgoal pending and inspect the current page or recover. "
    "Apply the same standard before terminate(success)."
)

EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT = (
    OFFICIAL_SYSTEM_PROMPT + EVIDENCE_QUALIFIED_PROGRESS_SUFFIX
)


# Frozen development diagnostic for source-document coverage.  It remains
# opt-in so the official baseline prompt and all prior frozen runs are intact.
SOURCE_DOCUMENT_COVERAGE_SUFFIX = r"""

# Source-document coverage contract

When a task requires extracting multiple records from a scrollable source
document, opening the document, selecting all text, or copying text does not
prove that you inspected every record.

Before leaving the source document, answering, or terminating:
- Inspect the current page and keep an exact list of every task-relevant object
  visibly supported so far.
- In the Action sentence before each forward vertical swipe, write exactly:
  Coverage scan; bottom anchor: <last visible record or line>; objects so far:
  <exact identifiers>; swipe forward.
- Continue forward vertical swipes.  Do not leave after the first page.
- Stop scanning only after a forward swipe produces no new bottom anchor or
  new visible record; record that repeated anchor in the Action sentence.
- Carry the exact accumulated identifiers in later Action sentences while
  entering the destination app.  Never invent an object that was not visible.
"""

SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT = (
    OFFICIAL_SYSTEM_PROMPT + SOURCE_DOCUMENT_COVERAGE_SUFFIX
)


class OfficialProtocolError(ValueError):
    """The model output is not a valid official Mobile Agent step."""


@dataclass(frozen=True)
class OfficialMobileDecision:
    thought: str
    action_summary: str
    tool_arguments: dict[str, Any]
    canonical_action: dict[str, Any] | None
    terminal_status: str | None

    def audit_record(self) -> dict[str, Any]:
        return {
            "thought": self.thought,
            "action_summary": self.action_summary,
            "tool": {"name": "mobile_use", "arguments": self.tool_arguments},
            "canonical_action": self.canonical_action,
            "terminal_status": self.terminal_status,
        }


_TOOL_CALL = re.compile(
    r"<tool_call>\s*(?P<call>\{.*?\})\s*</tool_call>",
    flags=re.DOTALL,
)
_ACTION_LINE = re.compile(
    r"^[ \t]*Action:[ \t]*(?P<summary>[^\r\n]+)",
    flags=re.MULTILINE,
)
_THOUGHT_BLOCK = re.compile(
    r"^[ \t]*Thought:[ \t]*(?P<thought>.*?)(?=^[ \t]*Action:|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)


def build_user_prompt(instruction: str, history: Iterable[str]) -> str:
    """Render the notebook's exact text template and history convention."""
    cleaned = [str(item).replace("\n", "").replace('"', "") for item in history]
    stage2_history = "".join(
        f"Step {index}: {item}; " for index, item in enumerate(cleaned, start=1)
    )
    return (
        f"The user query: {instruction}.\n"
        "Task progress (You have done the following operation on the current "
        f"device): {stage2_history}.\n"
    )


def _exact_keys(arguments: dict[str, Any], required: set[str]) -> None:
    actual = set(arguments)
    if actual != required:
        raise OfficialProtocolError(
            f"arguments for {arguments.get('action')!r} require exactly "
            f"{sorted(required)}, received {sorted(actual)}"
        )


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OfficialProtocolError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise OfficialProtocolError(f"{name} must be a finite number")
    return value


def _coordinate(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise OfficialProtocolError(f"{name} must be a two-item array")
    x = _number(value[0], f"{name}[0]")
    y = _number(value[1], f"{name}[1]")
    if not 0.0 <= x <= OFFICIAL_GRID_MAX or not 0.0 <= y <= OFFICIAL_GRID_MAX:
        raise OfficialProtocolError(f"{name} is outside the official 0..999 grid")
    return x, y


def _normalized(point: tuple[float, float]) -> tuple[float, float]:
    return point[0] / OFFICIAL_GRID_MAX, point[1] / OFFICIAL_GRID_MAX


def _nonempty_text(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise OfficialProtocolError("text must be a non-empty string")
    return value


def _positive_seconds(value: Any) -> float:
    seconds = _number(value, "time")
    if not 0.0 < seconds <= 30.0:
        raise OfficialProtocolError("time must be in (0, 30] seconds")
    return seconds


def _convert(arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    action = arguments.get("action")
    if action == "click":
        _exact_keys(arguments, {"action", "coordinate"})
        x, y = _normalized(_coordinate(arguments["coordinate"], "coordinate"))
        return {"type": "tap", "x": x, "y": y}, None
    if action == "long_press":
        _exact_keys(arguments, {"action", "coordinate", "time"})
        x, y = _normalized(_coordinate(arguments["coordinate"], "coordinate"))
        duration = round(_positive_seconds(arguments["time"]) * 1000)
        return {"type": "long_press", "x": x, "y": y, "duration_ms": duration}, None
    if action == "swipe":
        _exact_keys(arguments, {"action", "coordinate", "coordinate2"})
        x, y = _normalized(_coordinate(arguments["coordinate"], "coordinate"))
        x2, y2 = _normalized(_coordinate(arguments["coordinate2"], "coordinate2"))
        return {
            "type": "swipe", "x": x, "y": y, "x2": x2, "y2": y2,
            "duration_ms": DEFAULT_SWIPE_DURATION_MS,
        }, None
    if action == "type":
        _exact_keys(arguments, {"action", "text"})
        return {"type": "type_text", "text": _nonempty_text(arguments["text"]), "clear_text": False}, None
    if action == "answer":
        _exact_keys(arguments, {"action", "text"})
        return {"type": "answer", "text": _nonempty_text(arguments["text"])}, "answer"
    if action == "system_button":
        _exact_keys(arguments, {"action", "button"})
        buttons = {
            "Back": "press_back", "Home": "press_home",
            "Enter": "press_enter", "Menu": "press_recents",
        }
        if arguments["button"] not in buttons:
            raise OfficialProtocolError("button must be Back, Home, Menu, or Enter")
        return {"type": buttons[arguments["button"]]}, None
    if action == "wait":
        _exact_keys(arguments, {"action", "time"})
        return {"type": "wait", "duration_ms": round(_positive_seconds(arguments["time"]) * 1000)}, None
    if action == "terminate":
        _exact_keys(arguments, {"action", "status"})
        status = arguments["status"]
        if status not in {"success", "failure"}:
            raise OfficialProtocolError("terminate status must be success or failure")
        return None, str(status)
    raise OfficialProtocolError(f"unsupported mobile_use action: {action!r}")


def parse_official_response(raw: str) -> OfficialMobileDecision:
    if not isinstance(raw, str):
        raise OfficialProtocolError("response must be text")
    tool_matches = list(_TOOL_CALL.finditer(raw))
    if len(tool_matches) != 1:
        raise OfficialProtocolError("response must contain exactly one tool_call")
    match = tool_matches[0]
    try:
        call = json.loads(match.group("call"))
    except json.JSONDecodeError as exc:
        raise OfficialProtocolError(f"tool_call is not valid JSON: {exc}") from exc
    if not isinstance(call, dict) or set(call) != {"name", "arguments"}:
        raise OfficialProtocolError("tool_call requires exactly name and arguments")
    if call["name"] != "mobile_use" or not isinstance(call["arguments"], dict):
        raise OfficialProtocolError("tool_call must invoke mobile_use with object arguments")
    canonical, terminal = _convert(call["arguments"])
    action_matches = list(_ACTION_LINE.finditer(raw[: match.start()]))
    if action_matches:
        action_summary = action_matches[-1].group("summary").strip()
    else:
        # The official notebook executes the JSON inside <tool_call> directly
        # and does not parse the prose envelope.  A factual controller-derived
        # history item keeps multi-step execution possible without repairing or
        # changing the model-selected action.
        action_summary = (
            "Execute mobile_use action "
            f"{json.dumps(call['arguments'], ensure_ascii=False, sort_keys=True)}."
        )
    thought_match = _THOUGHT_BLOCK.search(raw[: match.start()])
    thought = thought_match.group("thought").strip() if thought_match else ""
    return OfficialMobileDecision(
        thought=thought,
        action_summary=action_summary,
        tool_arguments=dict(call["arguments"]),
        canonical_action=canonical,
        terminal_status=terminal,
    )
