from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from raven_m.eest_ac.outcome_oracle_v0_2_3 import (
    DEFAULT_CONTRACT_PATH,
    DEFAULT_SCHEMA_PATH,
    OutcomeOracleError,
    build_trace_schema,
    canonical_json,
    context_route_signature,
    evaluate_trace_v0_2_3,
    load_contract,
    parse_trace_v0_2_3,
    value_sha256,
)


def h(value: str) -> str:
    return value_sha256(value)


def observation(
    name: str,
    *,
    package: str = "example.alpha",
    activity: str | None = "example.alpha.Main",
    content: str | None = None,
    a11y: bool = True,
    pixel: str | None = None,
    route: str | None = "auto",
) -> dict:
    packages = [package] if package else []
    return {
        "pixel_sha256": h(pixel or f"pixel:{name}"),
        "a11y_available": a11y,
        "a11y_sha256": h(f"a11y:{content or name}") if a11y else None,
        "page_content_sha256": h(f"content:{content or name}") if a11y else None,
        "package_names": packages,
        "activity": activity,
        "route_signature": context_route_signature(packages, activity) if route == "auto" else route,
    }


def trace(action_class: str, pre: dict, post: list[dict], *, resolver: dict | None = None) -> dict:
    return {
        "trace_id": f"trace-{action_class}",
        "action_class": action_class,
        "action": {"type": action_class},
        "resolver": resolver,
        "pre": pre,
        "post": post,
    }


def resolver(package: str, activity: str | None = None) -> dict:
    return {
        "target_packages": [package],
        "target_activities": [activity] if activity else [],
        "provenance_sha256": h(f"resolver:{package}:{activity}"),
    }


def test_generated_schema_is_exact_contract_derivative() -> None:
    assert json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")) == build_trace_schema(load_contract())


def test_parser_accepts_valid_and_rejects_unknown_fields() -> None:
    item = trace("navigation_press", observation("pre"), [observation("post"), observation("post")])
    assert parse_trace_v0_2_3(canonical_json(item))["trace_id"] == item["trace_id"]
    item["unknown"] = True
    with pytest.raises(OutcomeOracleError, match="TRACE_SCHEMA_INVALID"):
        parse_trace_v0_2_3(canonical_json(item))


def test_scroll_accepts_stable_a11y_change_without_pixel_stability() -> None:
    pre = observation("pre", content="top")
    one = observation("one", content="bottom", pixel="motion-one")
    two = observation("two", content="bottom", pixel="motion-two")
    result = evaluate_trace_v0_2_3(trace("scroll", pre, [one, two]))
    assert result.decision == "accept"
    assert result.rule_id == "SCROLL_STABLE_A11Y_CHANGE"
    assert "terminal_pixels_unstable" in result.optional_witnesses


@pytest.mark.parametrize("post_pixels", [("same", "same"), ("one", "two")])
def test_scroll_rejects_no_semantic_change_even_when_pixels_change(post_pixels: tuple[str, str]) -> None:
    pre = observation("pre", content="same", pixel="pre")
    posts = [
        observation("post-one", content="same", pixel=post_pixels[0]),
        observation("post-two", content="same", pixel=post_pixels[1]),
    ]
    result = evaluate_trace_v0_2_3(trace("scroll", pre, posts))
    assert result.decision == "reject"
    assert "stable_no_semantic_change" in result.vetoes


def test_scroll_missing_a11y_is_uncertain() -> None:
    posts = [observation("post", a11y=False), observation("post", a11y=False)]
    result = evaluate_trace_v0_2_3(trace("scroll", observation("pre"), posts))
    assert result.decision == "uncertain"
    assert result.missing_evidence


def test_scroll_context_transition_is_rejected() -> None:
    posts = [
        observation("post", package="example.beta", activity="example.beta.Main"),
        observation("post", package="example.beta", activity="example.beta.Main"),
    ]
    result = evaluate_trace_v0_2_3(trace("scroll", observation("pre"), posts))
    assert result.decision == "reject"
    assert result.rule_id == "SCROLL_CONTEXT_TRANSITION"


def test_open_app_accepts_resolver_target_without_exact_pixels() -> None:
    target = "example.target"
    activity = "example.target.Main"
    posts = [
        observation("post", package=target, activity=activity, content="target", pixel="one"),
        observation("post", package=target, activity=activity, content="target", pixel="two"),
    ]
    result = evaluate_trace_v0_2_3(trace("open_app", observation("pre"), posts, resolver=resolver(target, activity)))
    assert result.decision == "accept"
    assert "terminal_pixels_unstable" in result.optional_witnesses


def test_open_app_wrong_target_is_rejected() -> None:
    posts = [observation("post"), observation("post")]
    result = evaluate_trace_v0_2_3(trace("open_app", observation("pre", package="example.pre"), posts, resolver=resolver("example.other")))
    assert result.decision == "reject"
    assert "wrong_target" in result.vetoes


def test_open_app_already_target_noop_is_rejected() -> None:
    target = "example.target"
    activity = "example.target.Main"
    pre = observation("same", package=target, activity=activity, content="same")
    posts = [
        observation("same", package=target, activity=activity, content="same"),
        observation("same", package=target, activity=activity, content="same"),
    ]
    result = evaluate_trace_v0_2_3(trace("open_app", pre, posts, resolver=resolver(target, activity)))
    assert result.decision == "reject"
    assert result.rule_id == "OPEN_APP_ALREADY_TARGET_NOOP"


def test_open_app_missing_resolver_is_uncertain() -> None:
    posts = [observation("post"), observation("post")]
    result = evaluate_trace_v0_2_3(trace("open_app", observation("pre"), posts))
    assert result.decision == "uncertain"
    assert "resolver.target_packages_or_provenance" in result.missing_evidence


def test_navigation_accepts_cross_context_transition_without_exact_pixels() -> None:
    posts = [
        observation("post", package="example.beta", activity="example.beta.Main", pixel="one"),
        observation("post", package="example.beta", activity="example.beta.Main", pixel="two"),
    ]
    result = evaluate_trace_v0_2_3(trace("navigation_press", observation("pre"), posts))
    assert result.decision == "accept"
    assert "cross_context_transition" in result.optional_witnesses


def test_navigation_accepts_same_context_stable_page_change() -> None:
    pre = observation("pre", content="page-one")
    posts = [observation("post", content="page-two"), observation("post", content="page-two")]
    result = evaluate_trace_v0_2_3(trace("navigation_press", pre, posts))
    assert result.decision == "accept"
    assert "same_context_page_change" in result.optional_witnesses


def test_navigation_rejects_stable_noop_and_pixel_only_change() -> None:
    pre = observation("pre", content="same", pixel="pre")
    posts = [
        observation("post", content="same", pixel="one"),
        observation("post", content="same", pixel="two"),
    ]
    result = evaluate_trace_v0_2_3(trace("navigation_press", pre, posts))
    assert result.decision == "reject"
    assert "pixel_only_change" in result.vetoes


def test_terminal_semantic_instability_rejects() -> None:
    posts = [observation("one", content="one"), observation("two", content="two")]
    result = evaluate_trace_v0_2_3(trace("navigation_press", observation("pre"), posts))
    assert result.decision == "reject"
    assert "terminal_semantic_instability" in result.vetoes


def test_contradictory_context_rejects() -> None:
    bad = observation("bad")
    bad["route_signature"] = h("contradiction")
    result = evaluate_trace_v0_2_3(trace("navigation_press", observation("pre"), [bad, bad]))
    assert result.decision == "reject"
    assert result.rule_id == "GENERIC_CONTRADICTORY_CONTEXT"


def test_contract_policies_expose_authority_and_vetoes() -> None:
    contract = load_contract()
    assert not contract["authority"]["pixel_can_authorize_accept"]
    for action_class in contract["input"]["action_classes"]:
        policy = contract["policies"][action_class]
        assert policy["required_witnesses"]
        assert policy["optional_witnesses"]
        assert policy["vetoes"]
        assert policy["missing_behavior"] == "uncertain"


def test_production_source_and_contract_have_no_task_app_or_coordinate_branches() -> None:
    paths = [Path(__file__).parents[2] / "src/raven_m/eest_ac/outcome_oracle_v0_2_3.py", DEFAULT_CONTRACT_PATH]
    forbidden = ("settings", "camera", "launcher", "dialer", "h17", "r79", "r80", "fixed coordinate")
    hits = []
    for path in paths:
        source = path.read_text(encoding="utf-8").casefold()
        for item in forbidden:
            if re.search(rf"(?<![a-z0-9_]){re.escape(item)}(?![a-z0-9_])", source):
                hits.append((path.name, item))
    assert hits == []
