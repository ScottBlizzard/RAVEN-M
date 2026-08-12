"""A10-v2 Evidence-Matured Obligation--Branch Frontier memory.

This module is a deterministic, controller-authored episode memory.  It uses
only the task query, model-visible RGB frames, the executed canonical action,
and the policy's action summary.  It does not call a model, inspect evaluator
or UI metadata, filter actions, or terminate an episode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
import re
import unicodedata
from typing import Any, Iterable

import numpy as np


MECHANISM_ID = "a10_v2_evidence_matured_obligation_branch_frontier_v2"
EXPERIMENT_ID = "A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"


class A10V2VisibleInputError(RuntimeError):
    """The controller did not provide a legal model-visible RGB frame."""


class A10V2IntegrityError(RuntimeError):
    """The episode/controller ordering or canonical action is invalid."""


def _compact(value: Any, limit: int) -> str:
    text = " ".join(str(value).split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _norm(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def _anchor_norm(value: Any) -> str:
    return re.sub(r"[_\W]+", " ", _norm(value), flags=re.UNICODE).strip()


def _normalized_typed_value(value: Any) -> str:
    return re.sub(
        r"[_\W]+",
        " ",
        unicodedata.normalize("NFKC", str(value)).casefold(),
        flags=re.UNICODE,
    ).strip()


def _json_sha(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _audit_descriptor(descriptor: "VisualDescriptor") -> dict[str, Any]:
    return {
        "exact_sha256": descriptor.exact_sha256,
        "descriptor_sha256": descriptor.descriptor_sha256,
        "luma_q_packed_hex": "".join(format(value, "x") for value in descriptor.luma_q),
        "edge_bits_hex": descriptor.edge_bits_hex,
        "crop_shape": descriptor.crop_shape,
    }


def _round_audit_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round_audit_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_audit_floats(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_round_audit_floats(item) for item in value)
    return value


def _sat(value: int) -> int:
    return min(255, max(0, int(value)))


def _visible_rgb(snapshot: dict[str, Any]) -> np.ndarray:
    pixels = np.asarray(snapshot.get("pixels"))
    if (
        pixels.ndim != 3
        or pixels.shape[0] < 25
        or pixels.shape[1] < 8
        or pixels.shape[2] < 3
        or not np.issubdtype(pixels.dtype, np.integer)
    ):
        raise A10V2VisibleInputError("A10 requires integer model-visible RGB pixels")
    if pixels.size and (int(pixels.min()) < 0 or int(pixels.max()) > 255):
        raise A10V2VisibleInputError("A10 RGB values must be within [0,255]")
    return np.ascontiguousarray(pixels[:, :, :3])


@dataclass(frozen=True)
class VisualDescriptor:
    exact_sha256: str
    descriptor_sha256: str
    luma_q: tuple[int, ...]
    edge_bits_hex: str
    crop_shape: tuple[int, int, int]


def describe_visual_state(pixels: np.ndarray) -> VisualDescriptor:
    rgb = _visible_rgb({"pixels": pixels})
    height = rgb.shape[0]
    top = int(math.floor(0.04 * height))
    bottom = int(math.ceil(0.96 * height))
    crop = np.ascontiguousarray(rgb[top:bottom, :, :3])
    exact_payload = (
        f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
    )
    exact = sha256(exact_payload).hexdigest()

    # W>=8 is legal even though the descriptor has 16 columns.  Overlapping
    # one-pixel cells at narrow widths keep every cell defined and deterministic.
    def cell_indices(size: int, count: int, index: int) -> np.ndarray:
        start = int(math.floor(index * size / count))
        stop = int(math.ceil((index + 1) * size / count))
        start = min(size - 1, max(0, start))
        stop = min(size, max(start + 1, stop))
        return np.arange(start, stop)

    rows = [cell_indices(crop.shape[0], 9, index) for index in range(9)]
    cols = [cell_indices(crop.shape[1], 16, index) for index in range(16)]
    integral = crop.astype(np.uint64).cumsum(axis=0).cumsum(axis=1)

    def rectangle_sum(r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
        total = integral[r1 - 1, c1 - 1].copy()
        if r0:
            total -= integral[r0 - 1, c1 - 1]
        if c0:
            total -= integral[r1 - 1, c0 - 1]
        if r0 and c0:
            total += integral[r0 - 1, c0 - 1]
        return total
    q: list[int] = []
    for rr in rows:
        for cc in cols:
            r0, r1 = int(rr[0]), int(rr[-1]) + 1
            c0, c1 = int(cc[0]), int(cc[-1]) + 1
            means = rectangle_sum(r0, r1, c0, c1) // ((r1 - r0) * (c1 - c0))
            luminance = (77 * int(means[0]) + 150 * int(means[1]) + 29 * int(means[2])) // 256
            q.append(min(15, max(0, luminance // 16)))
    matrix = np.asarray(q, dtype=np.uint8).reshape(9, 16)
    edge_values = np.concatenate(
        ((matrix[:, 1:] > matrix[:, :-1]).ravel(), (matrix[1:, :] > matrix[:-1, :]).ravel())
    ).astype(np.uint8)
    edge_bytes = np.packbits(edge_values, bitorder="big").tobytes()
    descriptor_sha = sha256(bytes(q) + edge_bytes).hexdigest()
    return VisualDescriptor(
        exact_sha256=exact,
        descriptor_sha256=descriptor_sha,
        luma_q=tuple(q),
        edge_bits_hex=edge_bytes.hex(),
        crop_shape=tuple(int(x) for x in crop.shape),
    )


def visual_distance(a: VisualDescriptor, b: VisualDescriptor) -> tuple[float, float, float]:
    if a.exact_sha256 == b.exact_sha256:
        return 0.0, 0.0, 0.0
    qa = np.asarray(a.luma_q, dtype=np.int16)
    qb = np.asarray(b.luma_q, dtype=np.int16)
    dl = float(np.abs(qa - qb).sum()) / (144.0 * 15.0)
    ea = np.unpackbits(np.frombuffer(bytes.fromhex(a.edge_bits_hex), dtype=np.uint8), bitorder="big")[:263]
    eb = np.unpackbits(np.frombuffer(bytes.fromhex(b.edge_bits_hex), dtype=np.uint8), bitorder="big")[:263]
    de = float(np.count_nonzero(ea != eb)) / 263.0
    return dl, de, 0.7 * dl + 0.3 * de


def visual_match(a: VisualDescriptor, b: VisualDescriptor) -> bool:
    if a.exact_sha256 == b.exact_sha256:
        return True
    dl, de, dv = visual_distance(a, b)
    return dl <= 0.06 and de <= 0.12 and dv <= 0.055


def changed_pixel_fraction(before: np.ndarray, after: np.ndarray) -> float:
    a = _visible_rgb({"pixels": before})
    b = _visible_rgb({"pixels": after})
    if a.shape != b.shape:
        return 1.0
    delta = np.max(np.abs(a.astype(np.int16) - b.astype(np.int16)), axis=2)
    return float(np.count_nonzero(delta > 5)) / float(delta.size)


_OPERATION_LEXICON = (
    ("DELETE", ("delete", "remove", "erase")),
    ("TRANSFER", ("send", "share", "sms", "export")),
    ("TRANSFORM", ("merge", "transcribe", "copy", "convert")),
    ("CREATE_OR_ADD", ("add", "create", "save", "make", "mark")),
    ("QUERY_OR_CALCULATE", ("find", "calculate", "total", "report", "list", "what")),
    ("NAVIGATE", ("open", "launch", "navigate")),
)


def classify_operation(goal: str) -> str:
    normalized = _norm(goal)
    for label, words in _OPERATION_LEXICON:
        if any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in words):
            return label
    return "OTHER"


_INTENT_LEXICON = (
    ("COMMIT", ("delete", "remove", "add", "create", "save", "send", "share", "submit", "confirm", "merge", "copy", "mark")),
    ("OPEN_OR_SELECT", ("open", "launch", "navigate", "select", "choose")),
    ("INPUT_OR_SEARCH", ("type", "enter", "fill", "search")),
    ("INSPECT", ("inspect", "check", "view", "read", "find", "calculate")),
    ("RECOVER", ("back", "return", "close", "cancel")),
    ("SCROLL", ("scroll", "swipe")),
    ("WAIT", ("wait",)),
    ("ANSWER", ("answer",)),
)


def classify_intent(summary: str, action: dict[str, Any]) -> str:
    normalized = _norm(summary)
    for label, words in _INTENT_LEXICON:
        positions = [m.start() for word in words for m in re.finditer(rf"\b{re.escape(word)}\b", normalized)]
        if positions:
            return label
    action_type = str(action.get("type") or "")
    fallback = {
        "swipe": "SCROLL", "wait": "WAIT", "answer": "ANSWER",
        "type_text": "INPUT_OR_SEARCH", "press_back": "RECOVER",
    }
    return fallback.get(action_type, "OTHER")


@dataclass
class AnchorEvidence:
    event_kind: str
    source_step: int
    weight: float


@dataclass
class GoalAnchor:
    anchor_id: str
    literal: str
    normalized: str
    source_kind: str
    source_offset: int
    specificity_weight: int
    role: str = "HEAD"
    group_id: str = ""
    persistent_open: bool = False
    confidence: float = 0.0
    status: str = "OPEN"
    last_evidence_step: int | None = None
    evidence_events: list[AnchorEvidence] = field(default_factory=list)
    contradiction_count: int = 0
    ever_supported: bool = False


def _extract_structured_anchors(goal: str, max_anchors: int = 8) -> list[GoalAnchor]:
    text = unicodedata.normalize("NFKC", str(goal))
    candidates: list[tuple[int, int, str, str]] = []
    # Pair each opening delimiter with only its legal closing delimiter.  A
    # natural apostrophe inside double quotes (or vice versa) is content, not
    # an early terminator.
    quote_pairs = ((r'"([^"\n]{2,64})"', 1),
                   (r"(?<!\w)'((?:[^'\n]|(?<=\w)'(?=\w)){2,64})'(?!\w)", 1),
                   (r'`([^`\n]{2,64})`', 1),
                   (r'“([^”\n]{2,64})”', 1),
                   (r'(?<!\w)‘((?:[^’\n]|(?<=\w)’(?=\w)){2,64})’(?!\w)', 1))
    for pattern, group in quote_pairs:
        for match in re.finditer(pattern, text):
            candidates.append((4, match.start(group), "quoted", match.group(group)))
    colon_parts = text.rsplit(":", 1)
    if len(colon_parts) == 2:
        payload = re.split(r"[.!?]", colon_parts[1], maxsplit=1)[0]
        items = [x.strip() for x in re.split(r"[,;\n]", payload) if x.strip()]
        if len(items) >= 2:
            for item in items:
                if 2 <= len(item) <= 64:
                    candidates.append((3, text.rfind(item), "colon_list", item))
    marker = re.compile(r"\b(?:following|these|named|called|titled|containing)\b\s*:?[ ]*([^.!?]+)", re.I)
    for match in marker.finditer(text):
        payload = match.group(1)
        if ":" in payload:
            payload = payload.rsplit(":", 1)[1]
        items = [x.strip() for x in re.split(r"[,;\n]|\band\b", payload, flags=re.I) if x.strip()]
        if len(items) >= 2:
            for item in items:
                if 2 <= len(item) <= 64:
                    candidates.append((3, match.start(1), "marker_list", item))
    numeric = re.compile(
        r"\b(?:\d{1,4}(?:[-/:.]\d{1,4})+|"
        r"\d+(?:\.\d+)?(?:\s*(?:am|pm|km|mins?|minutes?|h|hrs?|hours?))?)\b",
        re.I,
    )
    for match in numeric.finditer(text):
        candidates.append((2, match.start(), "numeric_or_time", match.group(0)))
    temporal_terms = (
        "today", "tomorrow", "yesterday", "this week", "last week",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december",
    )
    lower = text.casefold()
    for term in temporal_terms:
        for match in re.finditer(rf"\b{re.escape(term)}\b", lower):
            candidates.append((2, match.start(), "temporal", text[match.start():match.end()]))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    seen: set[str] = set()
    anchors: list[GoalAnchor] = []
    for weight, offset, kind, literal in candidates:
        normalized = _anchor_norm(literal)[:64]
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        anchors.append(GoalAnchor(
            anchor_id=f"a10v2a_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}",
            literal=_compact(literal, 64), normalized=normalized, source_kind=kind,
            source_offset=int(offset), specificity_weight=int(weight),
        ))
        if len(anchors) >= max_anchors:
            break
    return anchors


@dataclass
class ObligationGroup:
    group_id: str
    kind: str
    head_anchor_id: str
    qualifier_anchor_ids: list[str]
    predicate_class: str
    predicate_literal: str
    polarity: str
    render_label: str
    persistent_open: bool
    specificity_weight: int
    status: str = "OPEN"


FIELD_ALIASES = {
    "file name": "file name", "filename": "file name",
    "direction": "directions", "directions": "directions",
    "ingredient": "ingredients", "ingredients": "ingredients",
    "description": "description", "note": "notes", "notes": "notes",
    "content": "content", "body": "body", "text": "text",
    "title": "title", "name": "name", "category": "category",
    "date": "date", "time": "time", "duration": "duration",
    "distance": "distance", "amount": "amount", "price": "price",
    "tag": "tags", "tags": "tags", "label": "labels", "labels": "labels",
    "prepare": "preparation time", "complete": "completion time",
    "finish": "completion time",
}
STOPWORDS = {"a", "an", "the", "of", "to", "from", "in", "on", "at", "for", "with", "without", "that", "which", "and", "or", "app", "application", "it", "them"}
GENERIC_NOUNS = {"item", "items", "entry", "entries", "record", "records", "recipe", "recipes", "expense", "expenses", "note", "notes", "file", "files", "song", "songs", "activity", "activities", "event", "events", "task", "tasks", "data", "thing", "things", "value", "values"}
COMMAND_VERBS = {"delete", "remove", "erase", "add", "create", "save", "open", "launch", "navigate", "send", "share", "find", "calculate"}
_FIELD_PATTERN = r"file\s+name|filename|directions?|ingredients?|description|notes?|content|body|text|title|name|category|date|time|duration|distance|amount|price|tags?|labels?"
_VALUE = r"[^\W_](?:[\w'’/+\-]*[^\W_])?(?:\s+[^\W_](?:[\w'’/+\-]*[^\W_])?){0,5}"
_APP_LOCATOR_RE = re.compile(r"\b(?:from|in|on|using|via|into|to)\s+(?:the\s+)?[A-Za-z0-9][A-Za-z0-9'’_-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'’_-]*){0,4}\s+(?:recipe\s+|maps\s+)?(?:app|application)\b", re.I | re.U)
_REL_FIELD_RE = re.compile(rf"\b(?:that|which)\s+(?P<neg>(?:(?:do|does)\s+not|don['’]t|doesn['’]t)\s+)?(?P<predicate>use|uses|using|contain|contains|containing|include|includes|including|mention|mentions|mentioning|have|has|having)\s+(?P<value>{_VALUE})\s+(?:in|within|from|on)\s+(?:the\s+)?(?P<field>{_FIELD_PATTERN})\b", re.I | re.U)
_REL_BARE_RE = re.compile(rf"\b(?:that|which)\s+(?P<neg>(?:(?:do|does)\s+not|don['’]t|doesn['’]t)\s+)?(?P<predicate>use|uses|using|contain|contains|containing|include|includes|including|mention|mentions|mentioning|have|has|having)\s+(?P<value>{_VALUE})(?=\s*(?:[,;.!?]|$|\band\b|\bor\b|\bthen\b))", re.I | re.U)
_WITH_FIELD_RE = re.compile(rf"\b(?P<polarity>with|without)\s+(?P<value>{_VALUE})\s+(?:in|within)\s+(?:the\s+)?(?P<field>{_FIELD_PATTERN})\b", re.I | re.U)
_REL_NUMERIC_RE = re.compile(r"\b(?:that|which)\s+(?:must\s+)?(?P<predicate>take|takes|taking|cost|costs|costing|last|lasts|lasting)\s+(?P<value>\d+(?:\.\d+)?\s*(?:ms|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|dollars?|usd|meters?|metres?|km|kilometers?|kilometres?))(?:\s+to\s+(?P<field>prepare|complete|finish))?", re.I | re.U)
_REL_NAME_RE = re.compile(rf"\b(?:that|which)\s+(?:is|are)\s+(?P<predicate>named|called|titled)\s+(?P<value>{_VALUE})(?=\s*(?:[,;.!?]|$|\band\b|\bor\b|\bthen\b))", re.I | re.U)


def _valid_constraint_value(value: str, app_spans: list[tuple[int, int]], span: tuple[int, int]) -> bool:
    normalized = _anchor_norm(value)
    tokens = normalized.split()
    if not (2 <= len(value) <= 48 and 1 <= len(tokens) <= 6):
        return False
    if any(max(span[0], a) < min(span[1], b) for a, b in app_spans):
        return False
    if tokens[0] in STOPWORDS or tokens[-1] in STOPWORDS:
        return False
    useful = [x for x in tokens if x not in STOPWORDS and x not in GENERIC_NOUNS]
    return bool(useful) and not all(x in COMMAND_VERBS for x in useful)


def parse_goal(goal: str, max_anchors: int = 8) -> tuple[list[GoalAnchor], list[ObligationGroup], dict[str, Any]]:
    text = unicodedata.normalize("NFKC", str(goal))
    base = _extract_structured_anchors(text, max_anchors=64)
    units: list[tuple[int, int, str, str, str | None, str, str, str]] = []
    app_spans = [m.span() for m in _APP_LOCATOR_RE.finditer(text)]
    occupied: list[tuple[int, int]] = []
    patterns = ((_REL_FIELD_RE, "CONTENT", True), (_WITH_FIELD_RE, "CONTENT", True), (_REL_NUMERIC_RE, "COMPARISON", True), (_REL_NAME_RE, "NAME", False))
    for regex, predicate_class, has_field in patterns:
        for match in regex.finditer(text):
            if any(max(match.start(), a) < min(match.end(), b) for a, b in occupied):
                continue
            value = match.group("value").strip()
            if not _valid_constraint_value(value, app_spans, match.span("value")):
                continue
            raw_field = match.groupdict().get("field") if has_field else None
            field_name = FIELD_ALIASES.get(_norm(raw_field), _norm(raw_field)) if raw_field else None
            polarity_token = (match.groupdict().get("polarity") or "").casefold()
            neg = bool(match.groupdict().get("neg")) or polarity_token == "without"
            predicate = match.groupdict().get("predicate") or polarity_token or "contain"
            units.append((4, match.start(), value, predicate, field_name, "EXCLUDE" if neg else "REQUIRE", predicate_class, "FILTER_SET"))
            occupied.append(match.span())
    for match in _REL_BARE_RE.finditer(text):
        if any(max(match.start(), a) < min(match.end(), b) for a, b in occupied):
            continue
        value = match.group("value").strip()
        if _valid_constraint_value(value, app_spans, match.span("value")):
            units.append((4, match.start(), value, match.group("predicate"), None, "EXCLUDE" if match.group("neg") else "REQUIRE", "CONTENT", "FILTER_SET"))
            occupied.append(match.span())

    anchors: list[GoalAnchor] = []
    groups: list[ObligationGroup] = []
    seen: dict[str, GoalAnchor] = {}
    frozen_priority = {"quoted": 6, "colon_list": 5, "marker_list": 5, "numeric_or_time": 3, "temporal": 2}
    all_units: list[tuple[int, int, str, Any]] = [(frozen_priority[a.source_kind], a.source_offset, "BASE", a) for a in base]
    all_units += [(u[0], u[1], "CONSTRAINT", u) for u in units]
    all_units.sort(key=lambda x: (-x[0], x[1], _json_sha(str(x[3]))))
    for priority, offset, kind, payload in all_units:
        if kind == "BASE":
            anchor = payload
            normalized = anchor.normalized
            if normalized in seen or len(anchors) >= max_anchors:
                continue
            gid = f"a10v2g_{sha256(('base:'+normalized).encode()).hexdigest()[:12]}"
            anchor.group_id = gid
            anchor.specificity_weight = priority
            anchors.append(anchor); seen[normalized] = anchor
            groups.append(ObligationGroup(gid, "ENUM_ITEM", anchor.anchor_id, [], "LITERAL", "", "REQUIRE", anchor.literal, False, priority))
            continue
        _, _, value, predicate, field_name, polarity, predicate_class, group_kind = payload
        normalized = _anchor_norm(value)
        field_norm = _anchor_norm(field_name or "")
        cost = (0 if normalized in seen else 1) + (0 if not field_norm or field_norm in seen else 1)
        if len(anchors) + cost > max_anchors:
            continue
        gid = f"a10v2g_{sha256((normalized+'|'+field_norm+'|'+polarity).encode()).hexdigest()[:12]}"
        head = seen.get(normalized)
        if head is None:
            head = GoalAnchor(f"a10v2a_{sha256(normalized.encode()).hexdigest()[:12]}", _compact(value, 64), normalized, "CONSTRAINT_VALUE", offset, 4, "HEAD", gid, True)
            anchors.append(head); seen[normalized] = head
        qualifier_ids: list[str] = []
        if field_norm:
            qualifier = seen.get(field_norm)
            if qualifier is None:
                qualifier = GoalAnchor(f"a10v2a_{sha256(field_norm.encode()).hexdigest()[:12]}", field_name or "", field_norm, "CONSTRAINT_FIELD", offset, 4, "QUALIFIER", gid, False)
                anchors.append(qualifier); seen[field_norm] = qualifier
            qualifier_ids.append(qualifier.anchor_id)
        label = f"{value} in {field_name}" if field_name else value
        if polarity == "EXCLUDE":
            label = f"exclude {label}"
        groups.append(ObligationGroup(gid, group_kind, head.anchor_id, qualifier_ids, predicate_class, _norm(predicate), polarity, _compact(label, 64), True, 4))
    return anchors[:max_anchors], groups[:8], {"app_locator_spans": app_spans, "rejected_candidates": []}


def extract_goal_anchors(goal: str, max_anchors: int = 8) -> list[GoalAnchor]:
    return parse_goal(goal, max_anchors)[0]


def _canonical_action(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        raise A10V2IntegrityError("canonical action must be a mapping")
    action_type = str(action.get("type") or "")
    allowed = {"tap", "long_press", "swipe", "type_text", "press_back", "press_home", "press_enter", "press_recents", "wait", "answer"}
    if action_type not in allowed:
        raise A10V2IntegrityError(f"unsupported canonical action: {action_type!r}")
    return dict(action)


def _coord(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise A10V2IntegrityError("canonical coordinate must be finite")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise A10V2IntegrityError("canonical coordinate outside [0,1]")
    return result


def canonical_action_family(action: dict[str, Any]) -> tuple[Any, ...]:
    action = _canonical_action(action)
    kind = str(action["type"])
    if kind in {"tap", "long_press"}:
        family: tuple[Any, ...] = (kind, min(11, int(12 * _coord(action.get("x")))), min(23, int(24 * _coord(action.get("y")))))
        if kind == "long_press":
            duration = int(action.get("duration_ms") or 0)
            family += (("short" if duration < 700 else "medium" if duration <= 1500 else "long"),)
        return family
    if kind == "swipe":
        x, y, x2, y2 = (_coord(action.get(key)) for key in ("x", "y", "x2", "y2"))
        dx, dy = x2 - x, y2 - y
        direction = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")
        length = math.hypot(dx, dy)
        bucket = "short" if length < 0.25 else "medium" if length < 0.55 else "long"
        return (kind, direction, bucket, min(2, int(3 * x)), min(3, int(4 * y)))
    if kind == "type_text":
        text = unicodedata.normalize("NFKC", str(action.get("text") or ""))
        size = len(text)
        bucket = "1-8" if size <= 8 else "9-32" if size <= 32 else "33-96" if size <= 96 else "97+"
        return (kind, sha256(text.encode("utf-8")).hexdigest(), bucket, bool(action.get("clear_text")))
    if kind == "wait":
        duration = int(action.get("duration_ms") or 0)
        return (kind, "short" if duration < 700 else "medium" if duration <= 1500 else "long")
    if kind == "answer":
        return (kind, sha256(unicodedata.normalize("NFKC", str(action.get("text") or "")).encode("utf-8")).hexdigest())
    return (kind,)


def target_anchor_mask(summary: str, action: dict[str, Any], anchors: list[GoalAnchor]) -> int:
    summary_norm = _anchor_norm(summary)
    typed = _anchor_norm(action.get("text") or "") if action.get("type") == "type_text" else ""
    mask = 0
    for index, anchor in enumerate(anchors):
        pattern = rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)"
        if re.search(pattern, summary_norm) or (typed and (typed == anchor.normalized or re.search(pattern, typed))):
            mask |= 1 << index
    return mask


def target_masks(summary: str, action: dict[str, Any], anchors: list[GoalAnchor], groups: list[ObligationGroup]) -> tuple[int, int]:
    anchor_mask = target_anchor_mask(summary, action, anchors)
    by_id = {anchor.anchor_id: index for index, anchor in enumerate(anchors)}
    group_mask = 0
    for index, group in enumerate(groups):
        head_index = by_id.get(group.head_anchor_id)
        if head_index is not None and anchor_mask & (1 << head_index):
            group_mask |= 1 << index
    return anchor_mask, group_mask


@dataclass
class BranchRecord:
    branch_id: str
    canonical_family: tuple[Any, ...]
    intent_class: str
    target_anchor_mask: int
    label: str
    latest_intent_excerpt: str
    first_step: int
    last_step: int
    attempt_count: int = 0
    raw_no_progress_count: int = 0
    raw_local_change_count: int = 0
    raw_return_count: int = 0
    raw_durable_count: int = 0
    failure_confidence: float = 0.0
    escape_confidence: float = 0.0
    canonical_action_sha256s: list[str] = field(default_factory=list)
    target_group_mask: int = 0
    events: list[tuple[int, str]] = field(default_factory=list)
    bad_return_count: int = 0
    retry_exemption_used: bool = False
    first_bad_anchor_confidences: tuple[float, ...] = ()


@dataclass
class FrontierRecord:
    frontier_id: str
    phase_id: int
    open_anchor_mask: int
    visual_exemplars: list[VisualDescriptor]
    first_step: int
    last_visit_step: int
    recent_visit_steps: list[int]
    visit_count: int
    branches: dict[str, BranchRecord]
    return_count: int
    durable_departure_count: int
    anchor_confidence_at_first_visit: tuple[float, ...]
    read_count_in_phase: int = 0


@dataclass
class AttemptReceipt:
    attempt_id: str
    source_step: int
    resolve_step: int | None
    frontier_id: str
    branch_id: str
    source_exact_sha256: str
    destination_exact_sha256: str
    open_anchor_mask: int
    immediate_outcome: str
    resolved_outcome: str
    route_length: int | None
    touched_anchor_ids: list[str]
    source_response_sha256: str
    canonical_action_sha256: str


@dataclass
class PendingRoute:
    attempt_id: str
    source_step: int
    frontier_id: str
    branch_id: str
    open_anchor_mask: int
    source_descriptor: VisualDescriptor
    phase_id: int
    base_confidences: tuple[float, ...]
    target_anchor_mask: int
    max_open_anchor_gain: float = 0.0
    phase_open_unchanged: bool = True
    target_anchor_unchanged: bool = True
    durable_emitted: bool = False
    target_group_mask: int = 0
    target_context_changed: bool = False
    route_work_event_count: int = 0


@dataclass
class ClosedRouteWatch:
    watch_id: str
    route_key: str
    source_step: int
    returned_step: int
    frontier_id: str
    branch_id: str
    source_descriptor: VisualDescriptor
    phase_id: int
    open_group_mask: int
    target_group_mask: int
    baseline_confidences: tuple[float, ...]
    stage: str = "PROVISIONAL_POST_RETURN"
    return_count: int = 1
    witness_count: int = 1
    witness_steps: list[int] = field(default_factory=list)
    post_return_deadline: int = 0
    recurrence_deadline: int = 0
    route_work_event_count: int = 0
    last_update_step: int = 0


@dataclass
class NoGroupPhaseWatch:
    source_step: int
    frontier_id: str
    source_descriptor: VisualDescriptor
    stage: str = "PENDING"


@dataclass
class EscapeWatch:
    source_step: int
    frontier_id: str
    anchor_id: str
    open_anchor_mask: int
    source_descriptor: VisualDescriptor
    base_confidences: tuple[float, ...]
    offscreen_count: int = 0


@dataclass
class TriggerCandidate:
    trigger_id: str
    kind: str
    created_step: int
    expires_step: int
    phase_id: int
    open_anchor_mask: int
    query_frontier_id: str
    expected_descriptor: VisualDescriptor
    evidence_strength: float
    route_return_strength: float
    anchor_gain: float
    evidence_signature: str
    evidence_payload: dict[str, Any]
    delivered: bool = False
    stage: str = "MATURE"
    matured_step: int = 0
    witness_steps: list[int] = field(default_factory=list)
    witness_count: int = 0
    baseline_head_confidences: tuple[float, ...] = ()
    productive_event_count: int = 0


_ANCHOR_WEIGHTS = {
    "ACTION_MENTION": 0.20, "TYPE_EXACT": 0.25, "COMMIT_INTENT": 0.20,
    "MATERIAL_VISIBLE_CHANGE": 0.10, "DURABLE_ROUTE_DEPARTURE": 0.15,
    "INDEPENDENT_SECOND_SUPPORT": 0.15, "NO_PROGRESS_COMMIT": -0.20,
    "BAD_ROUTE_MATURED": -0.25, "REVERSAL_OR_FAILURE_PROSE": -0.45,
    "LATER_REOPEN_ATTEMPT": -0.30,
}


class EvidenceMaturedObligationBranchFrontierMemory:
    mechanism_id = MECHANISM_ID

    def __init__(self, *, max_anchors: int = 8, max_anchor_events: int = 6,
                 max_frontiers: int = 16, max_branches_per_frontier: int = 5,
                 max_attempt_receipts: int = 32, max_pending_routes: int = 4,
                 max_escape_watches: int = 2, max_trigger_candidates: int = 8,
                 max_nonempty_reads: int = 5, max_reads_per_phase: int = 2,
                 read_cooldown_steps: int = 4, max_chars: int = 420,
                 max_utf8_bytes: int = 720, experiment_id: str = EXPERIMENT_ID) -> None:
        self.experiment_id = str(experiment_id)
        self.max_anchors = min(8, max(1, int(max_anchors)))
        self.max_anchor_events = min(6, max(1, int(max_anchor_events)))
        self.max_frontiers = min(16, max(1, int(max_frontiers)))
        self.max_branches_per_frontier = min(5, max(1, int(max_branches_per_frontier)))
        self.max_attempt_receipts = min(32, max(1, int(max_attempt_receipts)))
        self.max_pending_routes = min(4, max(1, int(max_pending_routes)))
        self.max_escape_watches = min(2, max(1, int(max_escape_watches)))
        self.max_trigger_candidates = min(8, max(1, int(max_trigger_candidates)))
        self.max_nonempty_reads = min(5, max(1, int(max_nonempty_reads)))
        self.max_reads_per_phase = min(2, max(1, int(max_reads_per_phase)))
        self.read_cooldown_steps = max(4, int(read_cooldown_steps))
        self.max_chars = min(420, max(256, int(max_chars)))
        self.max_utf8_bytes = min(720, max(512, int(max_utf8_bytes)))

        self.goal_sha256 = ""
        self.operation_class = "OTHER"
        self.anchors: list[GoalAnchor] = []
        self.obligation_groups: list[ObligationGroup] = []
        self.parser_diagnostics: dict[str, Any] = {}
        self.phase_id = 0
        self.frontiers: dict[str, FrontierRecord] = {}
        self.attempt_receipts: list[AttemptReceipt] = []
        self.pending_routes: list[PendingRoute] = []
        self.closed_route_watches: list[ClosedRouteWatch] = []
        self.escape_watches: list[EscapeWatch] = []
        self.trigger_candidates: list[TriggerCandidate] = []
        self.delivered_signatures: list[str] = []
        self.screen_trace: list[str] = []
        self.read_events: list[dict[str, Any]] = []
        self.phase_switch_events: list[dict[str, Any]] = []
        self.last_observed_step = -1
        self.last_nonempty_read_step: int | None = None
        self._type_occurrences: dict[str, list[dict[str, Any]]] = {}
        self._recent_clear_steps: list[int] = []
        self._no_anchor_phase_watch: NoGroupPhaseWatch | None = None
        self._current_phase_nonempty_reads = 0
        self._read_baselines: dict[str, dict[str, Any]] = {}
        # Bounded, non-semantic memoization.  Controller sequencing commonly
        # presents the same RGB as an action's ``after`` and the next call's
        # ``before``.  Reusing its immutable descriptor changes no decision or
        # audit state and avoids repeating the 144-cell integral reduction.
        self._descriptor_cache: list[tuple[str, VisualDescriptor]] = []

        self.read_count = self.nonempty_read_count = 0
        self.write_attempt_count = self.write_success_count = 0
        self.frontier_merge_count = self.frontier_eviction_count = 0
        self.branch_eviction_count = self.trigger_eviction_count = 0
        self.phase_switch_count = self.expired_trigger_count = 0
        self.route_watch_created_count = self.route_watch_matured_count = 0
        self.route_watch_dismissed_count = self.route_watch_expired_count = 0
        self.duplicate_suppressed_count = 0
        self.max_observed_frontiers = self.max_observed_branches = 0
        self.max_observed_receipts = self.max_observed_rendered_chars = 0
        self.max_observed_rendered_utf8_bytes = 0
        self.raw_outcome_counts: dict[str, int] = {}
        self.created_counts_by_kind: dict[str, int] = {}
        self.delivered_counts_by_kind: dict[str, int] = {}
        self.next_branch_novel_count = self.same_branch_after_read_count = 0
        self.escaped_frontier_within_3_count = self.returned_within_4_count = 0
        self.anchor_gain_after_read_count = 0

    def _describe(self, pixels: np.ndarray) -> VisualDescriptor:
        rgb = _visible_rgb({"pixels": pixels})
        height = rgb.shape[0]
        crop = np.ascontiguousarray(
            rgb[int(math.floor(.04 * height)):int(math.ceil(.96 * height)), :, :3]
        )
        exact = sha256(
            f"{crop.shape}|{crop.dtype.str}|".encode("ascii") + crop.tobytes()
        ).hexdigest()
        for cached_exact, descriptor in reversed(self._descriptor_cache):
            if cached_exact == exact:
                return descriptor
        descriptor = describe_visual_state(rgb)
        self._descriptor_cache.append((exact, descriptor))
        self._descriptor_cache = self._descriptor_cache[-20:]
        return descriptor

    def _initialize_goal_once(self, goal: str) -> None:
        digest = sha256(str(goal).encode("utf-8")).hexdigest()
        if not self.goal_sha256:
            self.goal_sha256 = digest
            self.operation_class = classify_operation(goal)
            self.anchors, self.obligation_groups, self.parser_diagnostics = parse_goal(goal, self.max_anchors)
        elif digest != self.goal_sha256:
            raise A10V2IntegrityError("goal changed within an episode")

    def _open_mask(self) -> int:
        mask = 0
        by_id = {anchor.anchor_id: anchor for anchor in self.anchors}
        for index, group in enumerate(self.obligation_groups):
            head = by_id[group.head_anchor_id]
            if group.persistent_open or head.status != "LOCALLY_SUPPORTED":
                mask |= 1 << index
        return mask

    def _head_indices_for_group_mask(self, mask: int) -> list[int]:
        by_id = {anchor.anchor_id: index for index, anchor in enumerate(self.anchors)}
        return [by_id[group.head_anchor_id] for group_index, group in enumerate(self.obligation_groups) if mask & (1 << group_index) and group.head_anchor_id in by_id]

    def _event_decay(self, event: AnchorEvidence, step: int) -> float:
        if event.event_kind in {"DURABLE_ROUTE_DEPARTURE", "INDEPENDENT_SECOND_SUPPORT"}:
            lam = 0.995
        elif event.weight < 0:
            lam = 0.99
        else:
            lam = 0.97
        return event.weight * (lam ** max(0, (step - event.source_step) // 6))

    def _refresh_anchors(self, step: int) -> None:
        for anchor in self.anchors:
            confidence = min(1.0, max(0.0, sum(self._event_decay(e, step) for e in anchor.evidence_events)))
            kinds = {e.event_kind for e in anchor.evidence_events}
            material_steps = {e.source_step for e in anchor.evidence_events if e.event_kind in {"MATERIAL_VISIBLE_CHANGE", "INDEPENDENT_SECOND_SUPPORT"}}
            hard = bool(kinds & {"ACTION_MENTION", "TYPE_EXACT"}) and "COMMIT_INTENT" in kinds and (
                "DURABLE_ROUTE_DEPARTURE" in kinds or len(material_steps) >= 2
            )
            anchor.confidence = confidence
            strong_negative = any(e.weight <= -0.30 for e in anchor.evidence_events)
            if anchor.role == "QUALIFIER":
                anchor.status = "QUALIFIER"
            elif anchor.persistent_open:
                anchor.status = "OPEN_FILTER" if confidence < .35 else "TOUCHED_FILTER" if confidence < .60 else "PROVISIONAL_FILTER"
            elif anchor.ever_supported and strong_negative and anchor.contradiction_count > 0:
                anchor.status = "REOPENED"
            elif confidence >= 0.80 and hard:
                anchor.status = "LOCALLY_SUPPORTED"
                anchor.ever_supported = True
                # Existing negative evidence may precede the first hard support;
                # only a later strong-negative event reopens the anchor.
                anchor.contradiction_count = 0
            elif confidence >= 0.60:
                anchor.status = "PROVISIONAL"
            elif confidence >= 0.35:
                anchor.status = "TOUCHED"
            else:
                anchor.status = "OPEN"

    def _refresh_branches(self, step: int) -> None:
        for frontier in self.frontiers.values():
            for branch in frontier.branches.values():
                (
                    _, _, _, _, branch.failure_confidence,
                    branch.escape_confidence,
                ) = self._branch_values(branch, step)

    def _add_anchor_event(self, anchor: GoalAnchor, kind: str, step: int) -> AnchorEvidence | None:
        if kind not in _ANCHOR_WEIGHTS or any(e.event_kind == kind and e.source_step == step for e in anchor.evidence_events):
            return None
        event = AnchorEvidence(kind, step, _ANCHOR_WEIGHTS[kind])
        anchor.evidence_events.append(event)
        anchor.last_evidence_step = step
        # contradiction_count is the bounded marker for a *strong* negative
        # that occurred after this anchor had once reached hard support.  Old
        # pre-support negatives and later weak negatives must not combine into
        # a false REOPENED state.
        if event.weight <= -0.30 and anchor.ever_supported:
            anchor.contradiction_count = _sat(anchor.contradiction_count + 1)
        while len(anchor.evidence_events) > self.max_anchor_events:
            newest_negative = max((e.source_step for e in anchor.evidence_events if e.weight < 0), default=-1)
            eligible = [e for e in anchor.evidence_events if not (e.weight < 0 and e.source_step == newest_negative)]
            victim = min(eligible or anchor.evidence_events, key=lambda e: (abs(self._event_decay(e, step)), e.source_step, e.event_kind))
            anchor.evidence_events.remove(victim)
        return event

    def _match_frontier(self, descriptor: VisualDescriptor, phase: int, open_mask: int, *, merge: bool) -> tuple[FrontierRecord | None, float]:
        matches: list[tuple[float, int, str, FrontierRecord]] = []
        for frontier in self.frontiers.values():
            if frontier.phase_id != phase or frontier.open_anchor_mask != open_mask:
                continue
            distances = [visual_distance(x, descriptor)[2] for x in frontier.visual_exemplars]
            exact = any(x.exact_sha256 == descriptor.exact_sha256 for x in frontier.visual_exemplars)
            best = min(distances)
            allowed = exact or (best <= 0.035 if merge else any(visual_match(x, descriptor) for x in frontier.visual_exemplars))
            if allowed:
                matches.append((0.0 if exact else best, -frontier.last_visit_step, frontier.frontier_id, frontier))
        if not matches:
            return None, 1.0
        matches.sort(key=lambda x: (x[0], x[1], x[2]))
        return matches[0][3], matches[0][0]

    def _frontier(self, descriptor: VisualDescriptor, phase: int, open_mask: int, step: int) -> tuple[FrontierRecord, bool, bool]:
        frontier, _ = self._match_frontier(descriptor, phase, open_mask, merge=True)
        if frontier is None:
            fid = f"a10f_{phase}_{sha256(f'{open_mask}|{descriptor.descriptor_sha256}|{step}'.encode()).hexdigest()[:16]}"
            frontier = FrontierRecord(fid, phase, open_mask, [descriptor], step, step, [], 0, {}, 0, 0, tuple(a.confidence for a in self.anchors))
            self.frontiers[fid] = frontier
            self._evict_frontiers(step, current=fid)
            return frontier, True, False
        added = False
        if all(visual_distance(x, descriptor)[2] > 0.02 for x in frontier.visual_exemplars):
            frontier.visual_exemplars.append(descriptor)
            frontier.visual_exemplars = frontier.visual_exemplars[-3:]
            added = True
        self.frontier_merge_count += 1
        return frontier, False, added

    @staticmethod
    def _visit(frontier: FrontierRecord, step: int) -> None:
        if frontier.recent_visit_steps and frontier.recent_visit_steps[-1] == step:
            frontier.last_visit_step = max(frontier.last_visit_step, step)
            return
        frontier.last_visit_step = step
        frontier.visit_count = _sat(frontier.visit_count + 1)
        frontier.recent_visit_steps.append(step)
        frontier.recent_visit_steps = frontier.recent_visit_steps[-10:]

    def _branch(self, frontier: FrontierRecord, family: tuple[Any, ...], intent: str, mask: int, group_mask: int, summary: str, step: int) -> tuple[BranchRecord, bool]:
        key = _json_sha([family, intent, mask, group_mask])
        if key in frontier.branches:
            return frontier.branches[key], False
        branch_id = _json_sha([frontier.frontier_id, key])
        branch = BranchRecord(f"a10b_{branch_id[:16]}", family, intent, mask, _compact(self._family_label(family, mask), 40), _compact(summary, 56), step, step)
        branch.target_group_mask = group_mask
        frontier.branches[key] = branch
        self._evict_branches(frontier, step)
        return branch, True

    def _family_label(self, family: tuple[Any, ...], mask: int) -> str:
        base = str(family[0]).replace("type_text", "text")
        if family[0] in {"tap", "long_press"}:
            horizontal = ("left", "middle", "right")[min(2, int(family[1]) // 4)]
            vertical = ("upper", "middle", "lower")[min(2, int(family[2]) // 8)]
            base += f" {vertical}-{horizontal}"
        elif family[0] == "swipe":
            base += f"-{family[1]}"
        labels = [a.literal for i, a in enumerate(self.anchors) if mask & (1 << i)]
        if labels:
            base += f' for "{_compact(labels[0], 20)}"'
        return base

    def _branch_values(self, branch: BranchRecord, step: int) -> tuple[float, float, float, float, float, float]:
        n = r = l = d = 0.0
        events = (
            receipt for receipt in self.attempt_receipts
            if receipt.branch_id == branch.branch_id
        )
        for receipt in events:
            event_step = receipt.resolve_step if receipt.resolve_step is not None else receipt.source_step
            outcome = receipt.resolved_outcome
            decay = 0.85 ** max(0, (step - event_step) // 8)
            if outcome.startswith("NO_PROGRESS"):
                n += decay
            elif outcome == "RETURNED":
                r += 1.25 * decay
            elif outcome == "LATE_RETURN":
                r += 0.75 * decay
            elif outcome == "LOCAL_VISIBLE_CHANGE":
                l += 0.5 * decay
            elif outcome == "DURABLE_DEPARTURE":
                d += decay
        total = n + r + l + d
        strength = 1.0 - math.exp(-0.7 * total)
        bad = ((1.0 + n + r) / (2.0 + total)) * strength
        escape = ((1.0 + d) / (2.0 + total)) * strength
        return n, r, l, d, bad, escape

    def _record_outcome(self, branch: BranchRecord, outcome: str, step: int) -> None:
        self.raw_outcome_counts[outcome] = self.raw_outcome_counts.get(outcome, 0) + 1
        if outcome.startswith("NO_PROGRESS"):
            branch.raw_no_progress_count = _sat(branch.raw_no_progress_count + 1)
        elif outcome == "LOCAL_VISIBLE_CHANGE":
            branch.raw_local_change_count = _sat(branch.raw_local_change_count + 1)
        elif outcome in {"RETURNED", "LATE_RETURN"}:
            branch.raw_return_count = _sat(branch.raw_return_count + 1)
        elif outcome == "DURABLE_DEPARTURE":
            branch.raw_durable_count = _sat(branch.raw_durable_count + 1)
        branch.events.append((step, outcome))
        branch.events = branch.events[-12:]
        _, _, _, _, branch.failure_confidence, branch.escape_confidence = self._branch_values(branch, step)
        if outcome in {"LOCAL_VISIBLE_CHANGE", "DURABLE_DEPARTURE"}:
            for trigger in self.trigger_candidates:
                if (
                    trigger.stage == "MATURE"
                    and trigger.query_frontier_id
                    == next(
                        (
                            frontier.frontier_id
                            for frontier in self.frontiers.values()
                            if any(item.branch_id == branch.branch_id for item in frontier.branches.values())
                        ),
                        "",
                    )
                ):
                    trigger.productive_event_count = _sat(trigger.productive_event_count + 1)

    def _classify_outcome(self, before: VisualDescriptor, after: VisualDescriptor, before_pixels: np.ndarray, after_pixels: np.ndarray) -> tuple[str, float]:
        fraction = changed_pixel_fraction(before_pixels, after_pixels)
        if before.exact_sha256 == after.exact_sha256:
            return "NO_PROGRESS_EXACT", fraction
        if fraction <= 0.001:
            return "NO_PROGRESS_NEGLIGIBLE", fraction
        if visual_match(before, after):
            return "LOCAL_VISIBLE_CHANGE", fraction
        return "DEPARTURE_PENDING", fraction

    def _evict_branches(self, frontier: FrontierRecord, step: int) -> None:
        while len(frontier.branches) > self.max_branches_per_frontier:
            def utility(item: tuple[str, BranchRecord]) -> tuple[float, int, str]:
                key, branch = item
                _, _, _, _, bad, escape = self._branch_values(branch, step)
                u = 2 * bad + escape + 0.5 * bool(branch.target_group_mask & self._open_mask()) + math.exp(-max(0, step - branch.last_step) / 8)
                return u, branch.last_step, branch.branch_id
            victim = min(frontier.branches.items(), key=utility)[0]
            del frontier.branches[victim]
            self.branch_eviction_count += 1

    def _evict_frontiers(self, step: int, current: str) -> None:
        while len(self.frontiers) > self.max_frontiers:
            open_mask = self._open_mask()
            def utility(item: tuple[str, FrontierRecord]) -> tuple[float, int, str]:
                key, f = item
                intersection_weight = sum(
                    group.specificity_weight
                    for index, group in enumerate(self.obligation_groups)
                    if (f.open_anchor_mask & open_mask) & (1 << index)
                )
                union_weight = sum(
                    group.specificity_weight
                    for index, group in enumerate(self.obligation_groups)
                    if (f.open_anchor_mask | open_mask) & (1 << index)
                )
                jac = intersection_weight / union_weight if union_weight else 1.0
                totals = [self._branch_values(branch, step)[:4] for branch in f.branches.values()]
                evidence = min(1.0, sum(sum(values) for values in totals) / 3.0)
                unread = any(t.query_frontier_id == key and not t.delivered for t in self.trigger_candidates)
                u = 3.0 * (key == current) + 1.5 * jac + 1.5 * evidence + float(unread) + math.exp(-max(0, step - f.last_visit_step) / 12)
                return u, f.last_visit_step, f.frontier_id
            victim = min(self.frontiers.items(), key=utility)[0]
            del self.frontiers[victim]
            self.pending_routes = [r for r in self.pending_routes if r.frontier_id != victim]
            self.trigger_candidates = [t for t in self.trigger_candidates if t.query_frontier_id != victim]
            self.frontier_eviction_count += 1

    def _derive_anchor_events(self, step: int, summary: str, action: dict[str, Any], mask: int, intent: str, outcome: str) -> list[tuple[GoalAnchor, AnchorEvidence]]:
        created: list[tuple[GoalAnchor, AnchorEvidence]] = []
        normalized_summary = _anchor_norm(summary)
        commit_terms = re.compile(r"\b(?:delete|remove|add|create|save|send|share|submit|confirm|merge|copy|mark)\b")
        failure_terms = re.compile(r"\b(?:cancel|undo|failed|failure|not)\b")

        def near_anchor(pattern: re.Pattern[str], anchor_text: str) -> bool:
            anchor_matches = list(re.finditer(rf"(?<!\w){re.escape(anchor_text)}(?!\w)", normalized_summary))
            term_matches = list(pattern.finditer(normalized_summary))
            return any(
                min(abs(a.start() - t.end()), abs(t.start() - a.end())) <= 48
                for a in anchor_matches for t in term_matches
            )

        for index, anchor in enumerate(self.anchors):
            if anchor.role != "HEAD" or not mask & (1 << index):
                continue
            kinds: list[str] = ["ACTION_MENTION"] if re.search(rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)", normalized_summary) else []
            if action.get("type") == "type_text" and anchor.normalized in _anchor_norm(action.get("text") or ""):
                kinds.append("TYPE_EXACT")
            if intent == "COMMIT" and near_anchor(commit_terms, anchor.normalized):
                kinds.append("COMMIT_INTENT")
                if outcome.startswith("NO_PROGRESS"):
                    kinds.append("NO_PROGRESS_COMMIT")
            if outcome == "LOCAL_VISIBLE_CHANGE":
                kinds.append("MATERIAL_VISIBLE_CHANGE")
            if near_anchor(failure_terms, anchor.normalized):
                kinds.append("REVERSAL_OR_FAILURE_PROSE")
            if anchor.status == "LOCALLY_SUPPORTED":
                kinds.append("LATER_REOPEN_ATTEMPT")
            for kind in kinds:
                event = self._add_anchor_event(anchor, kind, step)
                if event:
                    created.append((anchor, event))
            positive_steps = {e.source_step for e in anchor.evidence_events if e.weight > 0}
            if len(positive_steps) >= 2:
                event = self._add_anchor_event(anchor, "INDEPENDENT_SECOND_SUPPORT", step)
                if event:
                    created.append((anchor, event))
        return created

    def _receipt(self, attempt_id: str) -> AttemptReceipt | None:
        return next((r for r in self.attempt_receipts if r.attempt_id == attempt_id), None)

    def _resolve_routes(self, step: int, descriptor: VisualDescriptor) -> list[dict[str, Any]]:
        resolutions: list[dict[str, Any]] = []
        retained: list[PendingRoute] = []
        for route in self.pending_routes:
            age = step - route.source_step
            # Frozen design §13.4 counts the departure action itself:
            # route_length = return_step - source_step + 1.
            route_length = age + 1
            receipt = self._receipt(route.attempt_id)
            frontier = self.frontiers.get(route.frontier_id)
            branch = next((b for b in frontier.branches.values() if b.branch_id == route.branch_id), None) if frontier else None
            returned = visual_match(route.source_descriptor, descriptor)
            route_gain = route.max_open_anchor_gain
            common = {
                "attempt_id": route.attempt_id,
                "resolve_step": step,
                "route_length": route_length,
                "frontier_id": route.frontier_id,
                "branch_id": route.branch_id,
                "phase_id": route.phase_id,
                "open_anchor_mask": route.open_anchor_mask,
                "route_anchor_gain": route_gain,
                "phase_open_unchanged": (
                    route.phase_open_unchanged
                    and self.phase_id == route.phase_id
                    and self._open_mask() == route.open_anchor_mask
                ),
                "target_anchor_unchanged": route.target_anchor_unchanged,
                "target_context_changed": route.target_context_changed,
                "target_group_mask": route.target_group_mask,
                "route_work_event_count": route.route_work_event_count,
                "source_descriptor": route.source_descriptor,
                "branch_label": branch.label if branch else "route",
            }
            if returned and 1 <= route_length <= 4:
                outcome = "RETURNED"
                if receipt:
                    receipt.resolved_outcome, receipt.resolve_step, receipt.route_length = outcome, step, route_length
                if branch:
                    self._record_outcome(branch, outcome, step)
                if frontier:
                    frontier.return_count = _sat(frontier.return_count + 1)
                for occurrences in self._type_occurrences.values():
                    for occurrence in occurrences:
                        if occurrence.get("attempt_id") == route.attempt_id:
                            occurrence["outcome"] = outcome
                            occurrence["route_anchor_gain"] = route_gain
                resolutions.append({**common, "outcome": outcome})
                continue
            if returned and 5 <= route_length <= 8:
                outcome = "LATE_RETURN"
                durable_step = (
                    receipt.resolve_step
                    if receipt and receipt.resolved_outcome == "DURABLE_DEPARTURE"
                    else None
                )
                if receipt:
                    receipt.resolved_outcome, receipt.resolve_step, receipt.route_length = outcome, step, route_length
                if branch:
                    removed = durable_step is not None and route.durable_emitted
                    if removed:
                        branch.raw_durable_count = _sat(branch.raw_durable_count - 1)
                        branch.events = [
                            event for event in branch.events
                            if not (
                                event[0] == durable_step
                                and event[1] == "DURABLE_DEPARTURE"
                            )
                        ]
                        self.raw_outcome_counts["DURABLE_DEPARTURE"] = max(
                            0, self.raw_outcome_counts.get("DURABLE_DEPARTURE", 0) - 1
                        )
                        if frontier:
                            frontier.durable_departure_count = _sat(
                                frontier.durable_departure_count - 1
                            )
                    self._record_outcome(branch, outcome, step)
                if durable_step is not None and receipt:
                    touched = set(receipt.touched_anchor_ids)
                    for anchor in self.anchors:
                        if anchor.anchor_id in touched:
                            anchor.evidence_events = [
                                event for event in anchor.evidence_events
                                if not (
                                    event.event_kind == "DURABLE_ROUTE_DEPARTURE"
                                    and event.source_step == durable_step
                                )
                            ]
                for occurrences in self._type_occurrences.values():
                    for occurrence in occurrences:
                        if occurrence.get("attempt_id") == route.attempt_id:
                            occurrence["outcome"] = outcome
                            occurrence["route_anchor_gain"] = route_gain
                resolutions.append({**common, "outcome": outcome, "revised_durable_step": durable_step})
                continue
            # The fourth subsequent action is still eligible to return.  Only
            # after observing it without a return is durable departure emitted.
            if route_length >= 4 and not route.durable_emitted:
                route.durable_emitted = True
                if receipt:
                    receipt.resolved_outcome, receipt.resolve_step, receipt.route_length = "DURABLE_DEPARTURE", step, route_length
                if branch:
                    self._record_outcome(branch, "DURABLE_DEPARTURE", step)
                if frontier:
                    frontier.durable_departure_count = _sat(frontier.durable_departure_count + 1)
                resolutions.append({**common, "outcome": "DURABLE_DEPARTURE"})
            if route_length <= 8:
                retained.append(route)
        # Older routes are nearer their frozen return/durable/late-return
        # boundary and therefore carry higher resolution priority.
        retained.sort(key=lambda route: (route.source_step, route.attempt_id))
        self.pending_routes = retained[: self.max_pending_routes]
        return resolutions

    def _update_closed_route_watches(
        self, *, step: int, source: FrontierRecord, branch: BranchRecord,
        outcome: str, group_mask: int, route_resolutions: list[dict[str, Any]],
    ) -> list[ClosedRouteWatch]:
        matured: list[ClosedRouteWatch] = []
        # Only steps strictly after returned_step may update post-return state.
        for watch in self.closed_route_watches:
            if watch.stage not in {"PROVISIONAL_POST_RETURN", "DORMANT_SINGLE_RETURN"} or step <= watch.returned_step:
                continue
            if step > watch.recurrence_deadline:
                watch.stage = "EXPIRED"; self.route_watch_expired_count += 1; continue
            current_gain = max((a.confidence - watch.baseline_confidences[i] for i, a in enumerate(self.anchors)), default=0.0)
            if self.phase_id != watch.phase_id or self._open_mask() != watch.open_group_mask or current_gain >= .10 or group_mask != watch.target_group_mask:
                watch.stage = "DISMISSED_PRODUCTIVE_WORKFLOW"; self.route_watch_dismissed_count += 1; continue
            if source.frontier_id == watch.frontier_id and branch.branch_id == watch.branch_id and outcome.startswith("NO_PROGRESS") and step <= watch.post_return_deadline:
                watch.stage = "MATURE_STAGNATION"; watch.witness_count = 2; watch.witness_steps.append(step); watch.last_update_step = step
                self.route_watch_matured_count += 1; branch.bad_return_count = _sat(branch.bad_return_count + 1); matured.append(watch); continue
            if source.frontier_id == watch.frontier_id and branch.branch_id != watch.branch_id and (
                (branch.first_step == step and outcome in {"LOCAL_VISIBLE_CHANGE", "DEPARTURE_PENDING"})
                or (step == watch.returned_step + 1 and watch.route_work_event_count >= 1 and not outcome.startswith("NO_PROGRESS"))
            ):
                watch.stage = "DISMISSED_PRODUCTIVE_WORKFLOW"; self.route_watch_dismissed_count += 1; continue
            if outcome in {"LOCAL_VISIBLE_CHANGE", "DURABLE_DEPARTURE"} and (branch.branch_id != watch.branch_id or group_mask != watch.target_group_mask):
                watch.stage = "DISMISSED_PRODUCTIVE_WORKFLOW"; self.route_watch_dismissed_count += 1; continue
            if step >= watch.post_return_deadline and watch.stage == "PROVISIONAL_POST_RETURN":
                watch.stage = "DORMANT_SINGLE_RETURN"

        for resolution in route_resolutions:
            if resolution["outcome"] != "RETURNED" or int(resolution["route_length"]) > 4:
                continue
            if not resolution["phase_open_unchanged"] or resolution["target_context_changed"] or float(resolution["route_anchor_gain"]) >= .15:
                continue
            route_key = _json_sha([resolution["frontier_id"], resolution["phase_id"], resolution["open_anchor_mask"], resolution["branch_id"]])
            prior = next((w for w in reversed(self.closed_route_watches) if w.route_key == route_key and w.stage in {"PROVISIONAL_POST_RETURN", "DORMANT_SINGLE_RETURN"} and step <= w.recurrence_deadline), None)
            if prior is not None:
                prior.stage = "MATURE_STAGNATION"; prior.return_count = 2; prior.witness_count = 2; prior.witness_steps.append(step); prior.last_update_step = step
                self.route_watch_matured_count += 1
                original = self.frontiers.get(prior.frontier_id)
                if original:
                    matched = next((b for b in original.branches.values() if b.branch_id == prior.branch_id), None)
                    if matched: matched.bad_return_count = _sat(matched.bad_return_count + 2)
                matured.append(prior)
                for occurrences in self._type_occurrences.values():
                    for occurrence in occurrences:
                        if occurrence.get("branch_id") == prior.branch_id and occurrence.get("frontier_id") == prior.frontier_id:
                            occurrence["outcome"] = "MATURED_BAD_RETURN"
                continue
            watch = ClosedRouteWatch(
                watch_id=f"a10v2w_{step}_{route_key[:10]}", route_key=route_key,
                source_step=int(resolution["resolve_step"]) - int(resolution["route_length"]) + 1,
                returned_step=step, frontier_id=str(resolution["frontier_id"]), branch_id=str(resolution["branch_id"]),
                source_descriptor=resolution["source_descriptor"], phase_id=int(resolution["phase_id"]),
                open_group_mask=int(resolution["open_anchor_mask"]), target_group_mask=int(resolution["target_group_mask"]),
                baseline_confidences=tuple(a.confidence for a in self.anchors), witness_steps=[step],
                post_return_deadline=step + 3, recurrence_deadline=step + 12,
                route_work_event_count=int(resolution["route_work_event_count"]), last_update_step=step,
            )
            self.closed_route_watches.append(watch); self.route_watch_created_count += 1
        self.closed_route_watches = sorted(self.closed_route_watches, key=lambda w: (w.stage != "MATURE_STAGNATION", -w.return_count, -w.last_update_step, w.watch_id))[:4]
        return matured

    def _make_trigger(self, kind: str, step: int, frontier: FrontierRecord, descriptor: VisualDescriptor, strength: float, route_strength: float, gain: float, payload: dict[str, Any]) -> TriggerCandidate:
        bounded_payload = {str(k)[:32]: (_compact(v, 56) if isinstance(v, str) else v) for k, v in list(payload.items())[:6]}
        signature = _json_sha([kind, self.phase_id, self._open_mask(), frontier.frontier_id, bounded_payload])
        expires = step + (5 if kind == "MATURED_FRONTIER_EXHAUSTION" else 6)
        witness_count = int(payload.get("witness_count", {"PARTIAL_OBLIGATION_ESCAPE": 3, "BAD_BRANCH_REPEAT": 2, "MATURED_CLOSED_ROUTE_STAGNATION": 2, "MATURED_FRONTIER_EXHAUSTION": 3, "VALUE_REENTRY_AFTER_BAD_OUTCOME": 2}.get(kind, 2)))
        trigger = TriggerCandidate(f"a10v2t_{kind[:2].lower()}_{step}_{signature[:10]}", kind, step, expires, self.phase_id, self._open_mask(), frontier.frontier_id, descriptor, min(1.0, max(0.0, strength)), min(1.0, max(0.0, route_strength)), max(0.0, gain), signature, bounded_payload)
        trigger.matured_step = step
        trigger.witness_count = witness_count
        trigger.witness_steps = [int(x) for x in payload.get("witness_steps", [step])][-4:]
        trigger.baseline_head_confidences = tuple(a.confidence for a in self.anchors)
        return trigger

    def _enqueue(self, trigger: TriggerCandidate) -> bool:
        if trigger.evidence_signature in self.delivered_signatures or any(t.evidence_signature == trigger.evidence_signature for t in self.trigger_candidates):
            self.duplicate_suppressed_count += 1
            return False
        self.trigger_candidates.append(trigger)
        self.created_counts_by_kind[trigger.kind] = self.created_counts_by_kind.get(trigger.kind, 0) + 1
        while len(self.trigger_candidates) > self.max_trigger_candidates:
            bonus = {"PARTIAL_OBLIGATION_ESCAPE": .20, "BAD_BRANCH_REPEAT": .18, "MATURED_CLOSED_ROUTE_STAGNATION": .15, "VALUE_REENTRY_AFTER_BAD_OUTCOME": .10, "MATURED_FRONTIER_EXHAUSTION": .05}
            victim = min(self.trigger_candidates, key=lambda t: (t.evidence_strength + self._unresolved_ratio() + math.exp(-max(0, trigger.created_step - t.created_step) / 8) + bonus[t.kind], t.created_step, t.trigger_id))
            self.trigger_candidates.remove(victim)
            self.trigger_eviction_count += 1
        return True

    def _unresolved_ratio(self) -> float:
        if not self.obligation_groups:
            return 1.0
        total = sum(g.specificity_weight for g in self.obligation_groups)
        return sum(g.specificity_weight for index, g in enumerate(self.obligation_groups) if self._open_mask() & (1 << index)) / total

    def _retry_exempt(
        self,
        branch: BranchRecord,
        action: dict[str, Any],
        before: VisualDescriptor,
        step: int,
        anchor_gain: float,
    ) -> bool:
        if branch.retry_exemption_used:
            return False
        exempt = False
        if action.get("type") == "wait" and branch.raw_no_progress_count <= 2:
            exempt = True
        if action.get("type") == "type_text" and bool(action.get("clear_text")):
            exempt = True
        if any(step - clear_step <= 2 for clear_step in self._recent_clear_steps):
            exempt = True
        prior_receipts = [
            receipt
            for receipt in self.attempt_receipts
            if receipt.branch_id == branch.branch_id and receipt.source_step < step
        ]
        if prior_receipts:
            prior = prior_receipts[-1]
            if prior.source_exact_sha256 != before.exact_sha256:
                exempt = True
            if prior.resolved_outcome == "DEPARTURE_PENDING":
                exempt = True
            if prior.resolved_outcome == "LOCAL_VISIBLE_CHANGE" and anchor_gain >= .10:
                exempt = True
        if exempt:
            branch.retry_exemption_used = True
        return exempt

    def _expire(self, step: int) -> None:
        kept = []
        for trigger in self.trigger_candidates:
            if step > trigger.expires_step or trigger.phase_id != self.phase_id:
                self.expired_trigger_count += 1
            elif not trigger.delivered:
                kept.append(trigger)
        self.trigger_candidates = kept

    def _candidate_distance(self, trigger: TriggerCandidate, descriptor: VisualDescriptor) -> tuple[float, bool]:
        dl, de, dv = visual_distance(trigger.expected_descriptor, descriptor)
        if trigger.expected_descriptor.exact_sha256 == descriptor.exact_sha256:
            return 0.0, True
        return dv, dl <= .05 and de <= .10 and dv <= .040

    def _score(self, trigger: TriggerCandidate, descriptor: VisualDescriptor, step: int, frontier: FrontierRecord | None) -> tuple[float, dict[str, float]]:
        distance, matches = self._candidate_distance(trigger, descriptor)
        m = 1.0 if distance == 0 else max(0.0, 1.0 - distance / .040) if matches else 0.0
        e = trigger.evidence_strength
        u = self._unresolved_ratio()
        g = 1.0 - min(1.0, trigger.anchor_gain / .15)
        required = {"PARTIAL_OBLIGATION_ESCAPE": 3, "BAD_BRANCH_REPEAT": 2, "MATURED_CLOSED_ROUTE_STAGNATION": 2, "MATURED_FRONTIER_EXHAUSTION": 3, "VALUE_REENTRY_AFTER_BAD_OUTCOME": 2}.get(trigger.kind, 2)
        w = min(1.0, trigger.witness_count / required)
        s = min(1.0, trigger.route_return_strength if trigger.route_return_strength else trigger.witness_count / required)
        f = math.exp(-max(0, step - trigger.matured_step) / 8)
        score = m * (.30 * e + .20 * u + .20 * s + .15 * w + .10 * g + .05 * f)
        return score, {"M": m, "E": e, "U": u, "S": s, "W": w, "G": g, "F": f}

    def _render(self, trigger: TriggerCandidate) -> str:
        unresolved = [g for index, g in enumerate(self.obligation_groups) if self._open_mask() & (1 << index)]
        label_limit = 20 if len(unresolved) > 1 else 24
        labels = [f'"{_compact(g.render_label, label_limit)}"' for g in unresolved[:2]]
        open_text = ", ".join(labels) if labels else "task completion is not established"
        if len(unresolved) > 2:
            open_text += f" (+{len(unresolved) - 2} more)"
        if len(open_text) > 56:
            labels = [f'"{_compact(g.render_label, 16)}"' for g in unresolved[:2]]
            open_text = ", ".join(labels)
            if len(unresolved) > 2:
                open_text += f" (+{len(unresolved) - 2} more)"
        payload = trigger.evidence_payload
        if trigger.kind == "PARTIAL_OBLIGATION_ESCAPE":
            evidence = f'"{payload.get("anchor", "an item")}" gained local support, but the route left while other items stayed open'
        elif trigger.kind == "BAD_BRANCH_REPEAT":
            evidence = f'{payload.get("branch", "this branch")} had no/negligible screen change {payload.get("count", 2)}x'
        elif trigger.kind == "MATURED_CLOSED_ROUTE_STAGNATION":
            evidence = f'{payload.get("branch", "this route")} left and returned twice without visible obligation progress'
        elif trigger.kind == "VALUE_REENTRY_AFTER_BAD_OUTCOME":
            evidence = "the same text was re-entered after its earlier route returned without open-item gain"
        else:
            evidence = f'{payload.get("visits", 4)} visits contained {payload.get("bad_count", 3)} bad outcomes across {payload.get("branch_count", 2)} branches and no productive transition'
        evidence = _compact(evidence, 86)
        suffix = "This warning requires repeated stagnation, not one navigation return. Reassess a different action family, target, or route only if the screen supports it. Nothing is blocked or selected."
        rendered = (
            "A10-v2 frontier; observed history only, current screen controls.\n"
            f"Open: {open_text}. Evidence: {evidence}.\n"
            + suffix
        )
        if len(rendered) > self.max_chars or len(rendered.encode("utf-8")) > self.max_utf8_bytes:
            evidence = _compact(evidence, 48)
            rendered = (
                "A10-v2 frontier; observed history only, current screen controls.\n"
                f"Open: {_compact(open_text, 40)}. Evidence: {evidence}.\n"
                + suffix
            )
        if len(rendered) > self.max_chars or len(rendered.encode("utf-8")) > self.max_utf8_bytes:
            raise A10V2IntegrityError("A10 fixed renderer exceeded its frozen budget")
        return rendered

    def _update_post_read_behavior(
        self,
        *,
        step: int,
        source_frontier: FrontierRecord,
        branch: BranchRecord,
        branch_created: bool,
        after_descriptor: VisualDescriptor,
    ) -> None:
        for event in self.read_events:
            age = step - int(event["step"])
            if not 0 <= age <= 4:
                continue
            baseline = self._read_baselines.get(str(event["read_id"]))
            if baseline is None:
                continue
            if event["next_action_branch_id"] is None:
                event["next_action_branch_id"] = branch.branch_id
                prior_ids = {item for item in event["retrieved_branch_ids"] if item}
                novel = bool(
                    branch_created
                    or source_frontier.frontier_id != event["frontier_id"]
                    or branch.branch_id not in prior_ids
                )
                event["next_action_was_novel"] = novel
                if novel:
                    self.next_branch_novel_count += 1
                else:
                    self.same_branch_after_read_count += 1
            frontier = self.frontiers.get(str(event["frontier_id"]))
            matches = bool(
                frontier
                and any(
                    visual_match(exemplar, after_descriptor)
                    for exemplar in frontier.visual_exemplars
                )
            )
            if age <= 3 and not matches and not baseline.get("escaped"):
                baseline["escaped"] = True
                event["escaped_frontier_within_3"] = True
                self.escaped_frontier_within_3_count += 1
            elif event["escaped_frontier_within_3"] is None and age >= 3:
                event["escaped_frontier_within_3"] = False
            if baseline.get("escaped") and matches and not baseline.get("returned"):
                baseline["returned"] = True
                event["returned_within_4"] = True
                self.returned_within_4_count += 1
            elif event["returned_within_4"] is None and age >= 4:
                event["returned_within_4"] = False
            previous = tuple(baseline.get("anchor_confidences") or ())
            read_open_mask = int(event.get("open_anchor_mask") or 0)
            read_head_indices = self._head_indices_for_group_mask(read_open_mask)
            delta = max(
                (
                    anchor.confidence - previous[index]
                    for index, anchor in enumerate(self.anchors)
                    if index < len(previous) and index in read_head_indices
                ),
                default=0.0,
            )
            event["open_anchor_confidence_delta_within_4"] = max(
                float(event["open_anchor_confidence_delta_within_4"] or 0.0),
                delta,
            )
            if delta >= .15 and not baseline.get("anchor_gain_counted"):
                baseline["anchor_gain_counted"] = True
                self.anchor_gain_after_read_count += 1

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        step = self.read_count
        self.read_count += 1
        self._initialize_goal_once(str(context.get("goal") or ""))
        descriptor = self._describe(_visible_rgb(dict(context.get("before") or {})))
        self.screen_trace.append(descriptor.descriptor_sha256)
        self.screen_trace = self.screen_trace[-17:]
        self._refresh_anchors(step)
        self._refresh_branches(step)
        open_mask = self._open_mask()
        self._expire(step)
        reason = "no_eligible_candidate"
        if self.nonempty_read_count >= self.max_nonempty_reads:
            reason = "episode_read_cap"
        elif self._current_phase_nonempty_reads >= self.max_reads_per_phase:
            reason = "phase_read_cap"
        elif self.last_nonempty_read_step is not None and step - self.last_nonempty_read_step < self.read_cooldown_steps:
            reason = "cooldown"
        else:
            ranked = []
            priority = {"PARTIAL_OBLIGATION_ESCAPE": 5, "BAD_BRANCH_REPEAT": 4, "MATURED_CLOSED_ROUTE_STAGNATION": 3, "VALUE_REENTRY_AFTER_BAD_OUTCOME": 2, "MATURED_FRONTIER_EXHAUSTION": 1}
            for trigger in self.trigger_candidates:
                if trigger.stage != "MATURE" or trigger.phase_id != self.phase_id or trigger.open_anchor_mask != open_mask or trigger.evidence_signature in self.delivered_signatures or step > trigger.expires_step:
                    continue
                if trigger.witness_count < {"PARTIAL_OBLIGATION_ESCAPE": 3, "BAD_BRANCH_REPEAT": 2, "MATURED_CLOSED_ROUTE_STAGNATION": 2, "MATURED_FRONTIER_EXHAUSTION": 3, "VALUE_REENTRY_AFTER_BAD_OUTCOME": 2}[trigger.kind]:
                    continue
                current_gain = max((a.confidence - trigger.baseline_head_confidences[i] for i, a in enumerate(self.anchors) if i < len(trigger.baseline_head_confidences)), default=0.0)
                if current_gain >= .15 or trigger.productive_event_count:
                    trigger.stage = "DISMISSED"
                    continue
                distance, matches = self._candidate_distance(trigger, descriptor)
                if not matches:
                    continue
                frontier = self.frontiers.get(trigger.query_frontier_id)
                if frontier and frontier.read_count_in_phase >= self.max_reads_per_phase:
                    continue
                score, components = self._score(trigger, descriptor, step, frontier)
                if score >= .72:
                    ranked.append((-score, -priority[trigger.kind], distance, -trigger.created_step, trigger.trigger_id, trigger, components))
            if ranked:
                ranked.sort(key=lambda x: x[:5])
                neg_score, _, distance, _, _, selected, components = ranked[0]
                score = -neg_score
                rendered = self._render(selected)
                self.nonempty_read_count += 1
                self._current_phase_nonempty_reads += 1
                self.last_nonempty_read_step = step
                self.delivered_signatures.append(selected.evidence_signature)
                self.delivered_signatures = self.delivered_signatures[-12:]
                selected.delivered = True
                selected.stage = "DELIVERED"
                frontier = self.frontiers.get(selected.query_frontier_id)
                if frontier:
                    frontier.read_count_in_phase = min(self.max_reads_per_phase, frontier.read_count_in_phase + 1)
                self.delivered_counts_by_kind[selected.kind] = self.delivered_counts_by_kind.get(selected.kind, 0) + 1
                selected_head_indices = self._head_indices_for_group_mask(selected.open_anchor_mask)
                event = {"read_id": f"a10r_{step}_{selected.evidence_signature[:8]}", "step": step, "trigger_id": selected.trigger_id, "trigger_kind": selected.kind, "frontier_id": selected.query_frontier_id, "phase_id": self.phase_id, "open_anchor_mask": open_mask, "score": score, "score_components": components, "visual_distance": distance, "evidence_signature": selected.evidence_signature, "rendered_sha256": sha256(rendered.encode()).hexdigest(), "rendered_chars": len(rendered), "rendered_utf8_bytes": len(rendered.encode()), "retrieved_anchor_ids": [self.anchors[index].anchor_id for index in selected_head_indices][:3], "retrieved_branch_ids": [str(selected.evidence_payload.get("branch_id") or "")][:1], "next_action_branch_id": None, "next_action_was_novel": None, "escaped_frontier_within_3": None, "returned_within_4": None, "open_anchor_confidence_delta_within_4": None}
                self.read_events.append(event)
                self.read_events = self.read_events[-5:]
                self._read_baselines[event["read_id"]] = {
                    "anchor_confidences": tuple(a.confidence for a in self.anchors),
                    "frontier_id": selected.query_frontier_id,
                    "escaped": False,
                }
                self._read_baselines = {
                    item["read_id"]: self._read_baselines[item["read_id"]]
                    for item in self.read_events
                    if item["read_id"] in self._read_baselines
                }
                self.max_observed_rendered_chars = max(self.max_observed_rendered_chars, len(rendered))
                self.max_observed_rendered_utf8_bytes = max(self.max_observed_rendered_utf8_bytes, len(rendered.encode()))
                return rendered, {"mechanism_id": self.mechanism_id, "nonempty": True, "reason": "selected", "step": step, "candidate_count": len(ranked), "selected_trigger_id": selected.trigger_id, "trigger_kind": selected.kind, "score": score, "score_components": components, "visual_distance": distance, "rendered_chars": len(rendered), "rendered_utf8_bytes": len(rendered.encode()), "rendered_sha256": sha256(rendered.encode()).hexdigest(), "retrieved_ids": [selected.trigger_id], "one_shot": True}
        return "", {"mechanism_id": self.mechanism_id, "nonempty": False, "reason": reason, "step": step, "candidate_count": 0, "rendered_chars": 0, "rendered_utf8_bytes": 0, "rendered_sha256": sha256(b"").hexdigest(), "retrieved_ids": []}

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        counter_before = {
            "frontier_merges": self.frontier_merge_count,
            "frontiers": self.frontier_eviction_count,
            "branches": self.branch_eviction_count,
            "triggers": self.trigger_eviction_count,
        }
        step = int(kwargs["source_step"])
        if step != self.last_observed_step + 1:
            raise A10V2IntegrityError("non-monotonic source_step")
        before_pixels = _visible_rgb(dict(kwargs.get("before") or {}))
        after_pixels = _visible_rgb(dict(kwargs.get("after") or {}))
        action = _canonical_action(dict(kwargs.get("canonical_action") or {}))
        summary = _compact(kwargs.get("action_summary") or "", 256)
        if bool(action.get("clear_text")) or re.search(
            r"\b(?:clear|erase)\b.{0,32}\b(?:input|text|field|query|search)\b",
            _norm(summary),
        ):
            self._recent_clear_steps.append(step)
            self._recent_clear_steps = self._recent_clear_steps[-12:]
        response_sha = _compact(kwargs.get("source_response_sha256") or "", 64)
        before_desc, after_desc = self._describe(before_pixels), self._describe(after_pixels)
        self._refresh_anchors(step)
        self._refresh_branches(step)
        step_start_conf = tuple(anchor.confidence for anchor in self.anchors)
        old_mask = self._open_mask()
        source, created, exemplar_added = self._frontier(before_desc, self.phase_id, old_mask, step)
        self._visit(source, step)
        for occurrences in self._type_occurrences.values():
            for occurrence in occurrences:
                if occurrence["step"] >= step or step - occurrence["step"] > 12:
                    continue
                if source.frontier_id != occurrence["frontier_id"]:
                    occurrence["left_source"] = True
                elif occurrence.get("left_source"):
                    occurrence["reentered_source"] = True
        intent = classify_intent(summary, action)
        mask, group_mask = target_masks(summary, action, self.anchors, self.obligation_groups)
        family = canonical_action_family(action)
        branch, branch_created = self._branch(source, family, intent, mask, group_mask, summary, step)
        branch.attempt_count = _sat(branch.attempt_count + 1)
        branch.last_step = step
        branch.latest_intent_excerpt = _compact(summary, 56)
        action_sha = _json_sha(action)
        branch.canonical_action_sha256s.append(action_sha)
        branch.canonical_action_sha256s = branch.canonical_action_sha256s[-3:]
        outcome, pixel_fraction = self._classify_outcome(before_desc, after_desc, before_pixels, after_pixels)
        attempt_id = f"a10p_{step}_{source.frontier_id[-6:]}_{branch.branch_id[-6:]}"
        receipt = AttemptReceipt(attempt_id, step, None if outcome == "DEPARTURE_PENDING" else step, source.frontier_id, branch.branch_id, before_desc.exact_sha256, after_desc.exact_sha256, old_mask, outcome, outcome, None, [a.anchor_id for i, a in enumerate(self.anchors) if mask & (1 << i)][:3], response_sha, action_sha)
        self.attempt_receipts.append(receipt)
        self.attempt_receipts = self.attempt_receipts[-self.max_attempt_receipts:]
        if outcome == "DEPARTURE_PENDING":
            self.pending_routes.append(
                PendingRoute(
                    attempt_id,
                    step,
                    source.frontier_id,
                    branch.branch_id,
                    old_mask,
                    before_desc,
                    self.phase_id,
                    tuple(anchor.confidence for anchor in self.anchors),
                    mask,
                    target_group_mask=group_mask,
                )
            )
        else:
            self._record_outcome(branch, outcome, step)
        anchor_events = self._derive_anchor_events(step, summary, action, mask, intent, outcome)
        self._refresh_anchors(step)
        for pending in self.pending_routes:
            pending.max_open_anchor_gain = max(
                pending.max_open_anchor_gain,
                max(
                    (
                        self.anchors[index].confidence - pending.base_confidences[index]
                        for index in self._head_indices_for_group_mask(pending.open_anchor_mask)
                    ),
                    default=0.0,
                ),
            )
            pending.phase_open_unchanged = bool(
                pending.phase_open_unchanged
                and self.phase_id == pending.phase_id
                and self._open_mask() == pending.open_anchor_mask
            )
            if (
                pending.source_step < step
                and group_mask != pending.target_group_mask
            ):
                pending.target_anchor_unchanged = False
                pending.target_context_changed = True
            if pending.source_step < step and intent in {"COMMIT", "CONFIGURE", "INPUT_OR_SEARCH"} and outcome in {"LOCAL_VISIBLE_CHANGE", "DEPARTURE_PENDING"}:
                pending.route_work_event_count = _sat(pending.route_work_event_count + 1)
        route_resolutions = self._resolve_routes(step, after_desc)
        for resolution in route_resolutions:
            resolved_receipt = self._receipt(str(resolution["attempt_id"]))
            touched = set(resolved_receipt.touched_anchor_ids if resolved_receipt else [])
            for anchor in self.anchors:
                if anchor.anchor_id not in touched:
                    continue
                if resolution["outcome"] in {"RETURNED", "LATE_RETURN"}:
                    self._add_anchor_event(anchor, "ROUTE_RETURN", step)
                elif resolution["outcome"] == "DURABLE_DEPARTURE":
                    self._add_anchor_event(anchor, "DURABLE_ROUTE_DEPARTURE", step)
        self._refresh_anchors(step)
        self._refresh_branches(step)
        new_mask = self._open_mask()
        no_anchor_phase_mature = False
        if self._no_anchor_phase_watch is not None:
            watch = self._no_anchor_phase_watch
            age = step - watch.source_step
            if visual_match(watch.source_descriptor, after_desc):
                self._no_anchor_phase_watch = None
            elif age + 1 >= 4:
                no_anchor_phase_mature = True
                self._no_anchor_phase_watch = None
        phase_switch = old_mask != new_mask or no_anchor_phase_mature
        if phase_switch:
            self.phase_id += 1
            self.phase_switch_count += 1
            self.phase_switch_events.append({"step": step, "old_open_mask": old_mask, "new_open_mask": new_mask, "phase_id": self.phase_id})
            self.phase_switch_events = self.phase_switch_events[-8:]
            self._current_phase_nonempty_reads = 0
        destination, _, _ = self._frontier(after_desc, self.phase_id, new_mask, step + 1)
        self._visit(destination, step + 1)
        if not self.obligation_groups and intent == "COMMIT" and outcome == "LOCAL_VISIBLE_CHANGE":
            self._no_anchor_phase_watch = NoGroupPhaseWatch(
                source_step=step,
                frontier_id=source.frontier_id,
                source_descriptor=before_desc,
            )
        enqueued: list[str] = []
        n, r, _, _, bad, _ = self._branch_values(branch, step)
        frontier_gain = max(
            (
                self.anchors[index].confidence - source.anchor_confidence_at_first_visit[index]
                for index in self._head_indices_for_group_mask(source.open_anchor_mask)
            ),
            default=0.0,
        )
        bad_steps = [event_step for event_step, event_outcome in branch.events if event_outcome.startswith("NO_PROGRESS")]
        if bad_steps and not branch.first_bad_anchor_confidences:
            branch.first_bad_anchor_confidences = step_start_conf
        t1_gain = max(
            (
                self.anchors[index].confidence - branch.first_bad_anchor_confidences[index]
                for index in self._head_indices_for_group_mask(source.open_anchor_mask)
                if index < len(branch.first_bad_anchor_confidences)
            ),
            default=0.0,
        ) if branch.first_bad_anchor_confidences else frontier_gain
        if not phase_switch:
            between_productive = bool(len(bad_steps) >= 2 and any(bad_steps[-2] < event_step < bad_steps[-1] and event_outcome in {"LOCAL_VISIBLE_CHANGE", "DURABLE_DEPARTURE"} for event_step, event_outcome in branch.events))
            if n >= 1.8 and len(set(bad_steps)) >= 2 and not between_productive and t1_gain < .10 and not self._retry_exempt(branch, action, before_desc, step, t1_gain):
                trigger = self._make_trigger("BAD_BRANCH_REPEAT", step, source, before_desc, max(.60, bad), min(1.0, n / 2), t1_gain, {"branch": branch.label, "branch_id": branch.branch_id, "count": max(2, branch.raw_no_progress_count), "witness_count": 2, "witness_steps": bad_steps[-2:]})
                if self._enqueue(trigger): enqueued.append(trigger.trigger_id)
        matured_watches = self._update_closed_route_watches(step=step, source=source, branch=branch, outcome=outcome, group_mask=group_mask, route_resolutions=route_resolutions)
        for watch in matured_watches:
            original_frontier = self.frontiers.get(watch.frontier_id)
            if original_frontier and not phase_switch:
                original_branch = next((b for b in original_frontier.branches.values() if b.branch_id == watch.branch_id), None)
                t2_evidence = min(1.0, .55 + .15 * min(3, watch.witness_count) + .15 * int(watch.return_count >= 2))
                trigger = self._make_trigger("MATURED_CLOSED_ROUTE_STAGNATION", step, original_frontier, watch.source_descriptor, t2_evidence, 1.0, frontier_gain, {"branch": original_branch.label if original_branch else "route", "branch_id": watch.branch_id, "witness_count": watch.witness_count, "witness_steps": watch.witness_steps[-2:]})
                if self._enqueue(trigger): enqueued.append(trigger.trigger_id)
                touched = set(next((receipt.touched_anchor_ids for receipt in self.attempt_receipts if receipt.branch_id == watch.branch_id), []))
                for anchor in self.anchors:
                    if anchor.anchor_id in touched: self._add_anchor_event(anchor, "BAD_ROUTE_MATURED", step)
        window_receipts = [receipt for receipt in self.attempt_receipts if receipt.frontier_id == source.frontier_id and step - 9 <= receipt.source_step <= step]
        visits = len({receipt.source_step for receipt in window_receipts})
        productive = [receipt for receipt in window_receipts if receipt.resolved_outcome in {"LOCAL_VISIBLE_CHANGE", "DURABLE_DEPARTURE"}]
        bad_receipts = [receipt for receipt in window_receipts if receipt.resolved_outcome.startswith("NO_PROGRESS")]
        bad_branch_counts: dict[str, int] = {}
        for receipt in bad_receipts: bad_branch_counts[receipt.branch_id] = bad_branch_counts.get(receipt.branch_id, 0) + 1
        bad_count = len(bad_receipts); distinct_bad = len(bad_branch_counts); repeated_bad = sum(max(0, count - 1) for count in bad_branch_counts.values())
        active_higher_priority = any(
            trigger.kind in {"BAD_BRANCH_REPEAT", "MATURED_CLOSED_ROUTE_STAGNATION", "VALUE_REENTRY_AFTER_BAD_OUTCOME"}
            and trigger.phase_id == self.phase_id
            and trigger.open_anchor_mask == new_mask
            and trigger.query_frontier_id == source.frontier_id
            and not trigger.delivered
            and step <= trigger.expires_step
            for trigger in self.trigger_candidates
        )
        if (
            not phase_switch
            and visits >= 4 and bad_count >= 3 and distinct_bad >= 2 and repeated_bad >= 1
            and not productive and frontier_gain < .10
            and not enqueued
            and not active_higher_priority
        ):
            trigger = self._make_trigger("MATURED_FRONTIER_EXHAUSTION", step, source, before_desc, min(1.0, bad_count / 4), 1.0, frontier_gain, {"visits": visits, "bad_count": bad_count, "branch_count": distinct_bad, "witness_count": bad_count, "witness_steps": [r.source_step for r in bad_receipts][-4:]})
            if self._enqueue(trigger): enqueued.append(trigger.trigger_id)
        if action.get("type") == "type_text":
            text_key = sha256(_normalized_typed_value(action.get("text") or "").encode()).hexdigest()
            occurrences = self._type_occurrences.setdefault(text_key, [])
            prior = next((x for x in reversed(occurrences) if step - x["step"] <= 12 and x["open_mask"] == old_mask and x["phase_id"] == self.phase_id and x["group_mask"] == group_mask and x["frontier_id"] == source.frontier_id), None)
            clear_between = bool(prior) and any(prior["step"] < clear_step <= step for clear_step in self._recent_clear_steps)
            prior_gain = max(
                (
                    anchor.confidence - prior["base_confidences"][index]
                    for index, anchor in enumerate(self.anchors)
                    if prior and prior["open_mask"] & (1 << index)
                ),
                default=0.0,
            ) if prior else 0.0
            reentered_without_gain = bool(
                prior
                and prior.get("reentered_source")
                and prior_gain < .15
            )
            bad_prior = bool(
                prior
                and (
                    prior["outcome"] in {"NO_PROGRESS_EXACT", "NO_PROGRESS_NEGLIGIBLE", "MATURED_BAD_RETURN"}
                    or reentered_without_gain
                )
                and (not clear_between or prior["frontier_id"] == source.frontier_id)
            )
            if bad_prior and not phase_switch:
                trigger = self._make_trigger("VALUE_REENTRY_AFTER_BAD_OUTCOME", step, source, before_desc, max(.65, bad), r, frontier_gain, {"branch_id": branch.branch_id})
                if self._enqueue(trigger): enqueued.append(trigger.trigger_id)
            occurrences.append({
                "step": step,
                "phase_id": self.phase_id,
                "open_mask": old_mask,
                "group_mask": group_mask,
                "outcome": outcome,
                "frontier_id": source.frontier_id,
                "attempt_id": attempt_id,
                "branch_id": branch.branch_id,
                "base_confidences": step_start_conf,
                "route_anchor_gain": 0.0,
                "left_source": False,
                "reentered_source": False,
            })
            self._type_occurrences[text_key] = occurrences[-4:]
            if len(self._type_occurrences) > 8:
                victim = min(self._type_occurrences, key=lambda k: self._type_occurrences[k][-1]["step"])
                del self._type_occurrences[victim]
        commit_gains = [
            (index, anchor, anchor.confidence - step_start_conf[index])
            for index, anchor in enumerate(self.anchors)
            if mask & (1 << index) and anchor.confidence - step_start_conf[index] >= .20
        ]
        closeable_groups = [g for g in self.obligation_groups if not g.persistent_open]
        if intent == "COMMIT" and len(closeable_groups) >= 2 and commit_gains:
            gained_index, gained_anchor, _ = max(commit_gains, key=lambda item: (item[2], -item[0]))
            gained_group_index = next((i for i, group in enumerate(self.obligation_groups) if group.head_anchor_id == gained_anchor.anchor_id), -1)
            remaining_open_mask = new_mask & ~(1 << gained_group_index) if gained_group_index >= 0 else new_mask
            if remaining_open_mask:
                self.escape_watches.append(EscapeWatch(step, source.frontier_id, gained_anchor.anchor_id, remaining_open_mask, before_desc, tuple(a.confidence for a in self.anchors)))
            self.escape_watches = self.escape_watches[-self.max_escape_watches:]
        mature: list[EscapeWatch] = []
        for watch in self.escape_watches:
            age = step - watch.source_step
            if age > 4 or visual_match(watch.source_descriptor, after_desc):
                continue
            returned_to_work_frontier = any(
                frontier.first_step < watch.source_step
                and frontier.frontier_id != watch.frontier_id
                and frontier.open_anchor_mask & watch.open_anchor_mask
                and any(visual_match(exemplar, after_desc) for exemplar in frontier.visual_exemplars)
                for frontier in self.frontiers.values()
            )
            if returned_to_work_frontier:
                continue
            watch.offscreen_count += 1
            max_open_gain = max((self.anchors[i].confidence - watch.base_confidences[i] for i in self._head_indices_for_group_mask(watch.open_anchor_mask)), default=0.0)
            if max_open_gain >= .10:
                continue
            if watch.offscreen_count >= 2 and max_open_gain < .10:
                wf = self.frontiers.get(watch.frontier_id)
                if wf:
                    anchor = next((a for a in self.anchors if a.anchor_id == watch.anchor_id), None)
                    completed_delta = max(0.0, (anchor.confidence - watch.base_confidences[self.anchors.index(anchor)]) if anchor else 0.0)
                    trigger = self._make_trigger("PARTIAL_OBLIGATION_ESCAPE", step, destination, after_desc, min(1.0, completed_delta + .20), 0.0, max_open_gain, {"anchor": anchor.literal if anchor else "an item"})
                    if self._enqueue(trigger): enqueued.append(trigger.trigger_id)
            elif age < 4:
                mature.append(watch)
        self.escape_watches = mature[-self.max_escape_watches:]
        self._refresh_anchors(step)
        self._evict_branches(source, step)
        self._evict_frontiers(step, destination.frontier_id)
        self._update_post_read_behavior(
            step=step,
            source_frontier=source,
            branch=branch,
            branch_created=branch_created,
            after_descriptor=after_desc,
        )
        self.last_observed_step = step
        self.max_observed_frontiers = max(self.max_observed_frontiers, len(self.frontiers))
        self.max_observed_branches = max(self.max_observed_branches, sum(len(f.branches) for f in self.frontiers.values()))
        self.max_observed_receipts = max(self.max_observed_receipts, len(self.attempt_receipts))
        counter_delta = {
            key: current - counter_before[key]
            for key, current in {
                "frontier_merges": self.frontier_merge_count,
                "frontiers": self.frontier_eviction_count,
                "branches": self.branch_eviction_count,
                "triggers": self.trigger_eviction_count,
            }.items()
        }
        written = bool(
            created or exemplar_added or branch_created
            or outcome != "DEPARTURE_PENDING" or anchor_events
            or route_resolutions or phase_switch or enqueued
            or any(counter_delta.values())
        )
        if written: self.write_success_count += 1
        public_resolutions = [
            {key: value for key, value in resolution.items() if key != "source_descriptor"}
            for resolution in route_resolutions
        ]
        return {"written": written, "source_step": step, "source_frontier_id": source.frontier_id, "destination_frontier_id": destination.frontier_id, "branch_id": branch.branch_id, "immediate_outcome": outcome, "changed_pixel_fraction": pixel_fraction, "anchor_events": [{"anchor_id": a.anchor_id, **asdict(e)} for a, e in anchor_events], "route_resolutions": public_resolutions, "phase_switch": phase_switch, "phase_id_after": self.phase_id, "trigger_ids_enqueued": enqueued, "evictions": counter_delta}

    def audit_record(self) -> dict[str, Any]:
        anchors = [asdict(a) for a in self.anchors]
        frontiers = []
        for frontier in self.frontiers.values():
            item = asdict(frontier)
            item["visual_exemplars"] = [
                _audit_descriptor(exemplar) for exemplar in frontier.visual_exemplars
            ]
            frontiers.append(item)
        triggers = []
        for trigger in self.trigger_candidates:
            item = asdict(trigger)
            item["expected_descriptor"] = _audit_descriptor(trigger.expected_descriptor)
            triggers.append(item)
        record: dict[str, Any] = {
            "schema": "a10_v2_emobf_audit_v1", "mechanism_id": self.mechanism_id,
            "experiment_id": self.experiment_id, "version": 2,
            "parameters": {"max_anchors": self.max_anchors, "max_groups": 8, "max_anchor_events": self.max_anchor_events, "max_frontiers": self.max_frontiers, "max_branches_per_frontier": self.max_branches_per_frontier, "max_attempt_receipts": self.max_attempt_receipts, "max_pending_routes": self.max_pending_routes, "max_closed_route_watches": 4, "max_no_group_phase_watches": 1, "max_escape_watches": self.max_escape_watches, "max_trigger_candidates": self.max_trigger_candidates, "max_nonempty_reads": self.max_nonempty_reads, "max_reads_per_phase": self.max_reads_per_phase, "read_cooldown_steps": self.read_cooldown_steps, "max_chars": self.max_chars, "max_utf8_bytes": self.max_utf8_bytes, "visual_thresholds": {"changed_fraction": .001, "route_dv": .055, "merge_dv": .035, "retrieval_dv": .040}, "confidence_thresholds": {"open": .35, "touched": .60, "provisional": .80, "retrieval": .72}, "route_horizons": {"return": 4, "late_return": 8, "watch_recurrence": 12}},
            "decision_boundary": {"allowed_inputs": ["goal", "before.pixels", "after.pixels", "canonical_action", "action_summary", "source_step"], "ignored_snapshot_fields": ["evaluator_reward", "task_success", "ui_tree", "ui_elements", "ui_sha256", "foreground", "activity", "package_name", "accessibility", "database_state", "transition"], "model_calls_added": 0, "evaluator_used_for_decision": False, "hidden_ui_used_for_decision": False, "future_information_used": False, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0, "history_summary_method": False},
            "causal_boundary": {"model_calls_added": 0, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0, "evaluator_used": False, "hidden_ui_used": False, "future_information_used": False, "task_name_used": False, "episode_id_used": False},
            "goal": {"goal_sha256": self.goal_sha256, "operation_class": self.operation_class, "anchor_count": len(anchors), "group_count": len(self.obligation_groups), "anchors": anchors, "groups": [asdict(g) for g in self.obligation_groups], "parser_diagnostics": self.parser_diagnostics},
            "phase": {"current_phase_id": self.phase_id, "phase_switch_count": self.phase_switch_count, "phase_switch_events": self.phase_switch_events},
            "frontiers": {"current_count": len(frontiers), "merge_count": self.frontier_merge_count, "eviction_count": self.frontier_eviction_count, "branch_eviction_count": self.branch_eviction_count, "records": frontiers},
            "attempts": {"retained_count": len(self.attempt_receipts), "raw_outcome_counts": self.raw_outcome_counts, "receipts": [asdict(x) for x in self.attempt_receipts]},
            "routes": {"pending_count": len(self.pending_routes), "return_count": self.raw_outcome_counts.get("RETURNED", 0), "late_return_count": self.raw_outcome_counts.get("LATE_RETURN", 0), "durable_departure_count": self.raw_outcome_counts.get("DURABLE_DEPARTURE", 0)},
            "closed_route_watches": {"current_count": len(self.closed_route_watches), "created_count": self.route_watch_created_count, "matured_count": self.route_watch_matured_count, "dismissed_count": self.route_watch_dismissed_count, "expired_count": self.route_watch_expired_count, "records": [{**{k:v for k,v in asdict(w).items() if k != "source_descriptor"}, "source_descriptor": _audit_descriptor(w.source_descriptor)} for w in self.closed_route_watches]},
            "triggers": {"candidate_count": len(triggers), "created_counts_by_kind": self.created_counts_by_kind, "delivered_counts_by_kind": self.delivered_counts_by_kind, "expired_count": self.expired_trigger_count, "duplicate_suppressed_count": self.duplicate_suppressed_count, "candidates": triggers},
            "reads": {"read_count": self.read_count, "nonempty_read_count": self.nonempty_read_count, "last_nonempty_read_step": self.last_nonempty_read_step, "delivered_signatures": self.delivered_signatures, "read_events": self.read_events},
            "post_read_behavior": {"next_branch_novel_count": self.next_branch_novel_count, "same_branch_after_read_count": self.same_branch_after_read_count, "escaped_frontier_within_3_count": self.escaped_frontier_within_3_count, "returned_within_4_count": self.returned_within_4_count, "anchor_gain_after_read_count": self.anchor_gain_after_read_count},
            "capacity": {"max_observed_frontiers": self.max_observed_frontiers, "max_observed_branches": self.max_observed_branches, "max_observed_receipts": self.max_observed_receipts, "max_observed_route_watches": max(self.route_watch_created_count, len(self.closed_route_watches)), "max_observed_rendered_chars": self.max_observed_rendered_chars, "max_observed_rendered_utf8_bytes": self.max_observed_rendered_utf8_bytes, "serialized_audit_bytes": 0},
            "write_attempt_count": self.write_attempt_count, "write_success_count": self.write_success_count,
            "active": self.nonempty_read_count > 0,
            "trigger_count": sum(self.created_counts_by_kind.values()),
            "rendered_chars_total": sum(int(item["rendered_chars"]) for item in self.read_events),
            "rendered_utf8_bytes_total": sum(int(item["rendered_utf8_bytes"]) for item in self.read_events),
            "model_calls_added": 0, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0,
        }
        record = _round_audit_floats(record)
        previous = -1
        while record["capacity"]["serialized_audit_bytes"] != previous:
            previous = record["capacity"]["serialized_audit_bytes"]
            record["capacity"]["serialized_audit_bytes"] = len(
                json.dumps(record, ensure_ascii=True, sort_keys=True).encode("utf-8")
            )
        return record
