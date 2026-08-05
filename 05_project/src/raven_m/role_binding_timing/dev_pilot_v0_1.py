"""Lightweight DEV screening for Correct Memory, Wrong Target.

The module deliberately bypasses the failed Android snapshot collector.  It uses
already inspected AndroidWorld frames as development material and never labels
them held-out.  It does not execute Android actions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any

from raven_m.models.transformers_client import TransformersClient
from raven_m.role_binding_timing.contract import canonical_json, load_contract
from raven_m.role_binding_timing.parser import (
    DecisionParseError,
    parse_action,
    parse_grounding,
)
from raven_m.role_binding_timing.token_audit import (
    HuggingFaceChatTokenCounter,
    TokenCounter,
    build_exact_neutral_block,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEFAULT_CONFIG = (
    PROJECT_ROOT / "configs/role_binding_timing/stage1_dev_pilot_v0_1.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "artifacts/role_binding_timing/stage1_dev_pilot_v0_1"
)


@dataclass(frozen=True)
class CellSpec:
    base_family_id: str
    fact_timing: str
    role_ambiguity: str
    image_path: Path
    field: str
    value: str
    source_name: str
    source_target_id: str
    destination_name: str
    destination_target_id: str
    task: str
    candidates: tuple[dict[str, Any], ...]
    candidate_prompt_fields: tuple[str, ...]

    @property
    def cell_id(self) -> str:
        return f"{self.base_family_id}__{self.fact_timing}_{self.role_ambiguity}"


@dataclass(frozen=True)
class PromptBundle:
    fact_block: str
    neutral_block: str
    call_1_prompt: str
    call_2_prompt: str


def _load_config_tree(path: Path, *, seen: tuple[Path, ...] = ()) -> dict[str, Any]:
    resolved_path = path.resolve()
    if resolved_path in seen:
        raise ValueError(f"Circular DEV config inheritance: {resolved_path}")
    value = json.loads(resolved_path.read_text(encoding="utf-8"))
    if value.get("parent_config"):
        parent_path = PROJECT_ROOT / value["parent_config"]
        parent = _load_config_tree(parent_path, seen=(*seen, resolved_path))
        child = {key: item for key, item in value.items() if key != "parent_config"}
        value = {**parent, **child}
        overrides = value.pop("task_overrides", {})
        if overrides:
            revised = []
            for template in value["templates"]:
                item = dict(template)
                item.update(overrides.get(item["base_family_id"], {}))
                revised.append(item)
            value["templates"] = revised
    return value


def load_dev_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    value = _load_config_tree(path)
    if value.get("schema_version") not in {
        "role_binding_timing.dev_pilot.v0_1",
        "role_binding_timing.dev_pilot.v0_2",
        "role_binding_timing.dev_pilot.v0_3",
    }:
        raise ValueError("Unexpected DEV pilot config version.")
    if value.get("development_contaminated") is not True:
        raise ValueError("DEV pilot must remain development-contaminated.")
    if value.get("confirmatory_claim_allowed") is not False:
        raise ValueError("DEV pilot cannot authorize confirmatory claims.")
    if len(value.get("templates", [])) != 8:
        raise ValueError("DEV pilot requires exactly eight base templates.")
    return value


def resolve_templates(config: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    resolved: list[dict[str, Any]] = []
    for raw in config["templates"]:
        item = dict(raw)
        source = item.pop("candidates_from", None)
        if source:
            if source not in by_id:
                raise ValueError(f"Unknown candidates_from: {source}")
            item["candidates"] = json.loads(json.dumps(by_id[source]["candidates"]))
        if not item.get("candidates"):
            raise ValueError(f"No candidates for {item['base_family_id']}")
        target_ids = [candidate["target_id"] for candidate in item["candidates"]]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError(f"Duplicate target IDs in {item['base_family_id']}")
        overrides = item.get("source_target_overrides", {})
        for ambiguity in ("low", "high"):
            key = f"{ambiguity}_source_target_id"
            if ambiguity in overrides:
                item[key] = overrides[ambiguity]
            if item[key] not in target_ids:
                raise ValueError(f"Missing {key} in {item['base_family_id']}")
        if item["destination_target_id"] not in target_ids:
            raise ValueError(f"Missing destination in {item['base_family_id']}")
        image = REPOSITORY_ROOT / item["image_path"]
        if not image.is_file():
            raise ValueError(f"Missing image: {image}")
        by_id[item["base_family_id"]] = item
        resolved.append(item)
    return resolved


def build_cells(config: dict[str, Any]) -> list[CellSpec]:
    templates = resolve_templates(config)
    cells: list[CellSpec] = []
    for item in templates:
        by_condition: dict[str, CellSpec] = {}
        for ambiguity in ("low", "high"):
            source = item[f"{ambiguity}_source_name"]
            source_target = item[f"{ambiguity}_source_target_id"]
            task_template = item.get(
                f"{ambiguity}_task_template", item["task_template"]
            )
            task = task_template.format(
                field=item["field"],
                source=source,
                destination=item["destination_name"],
            )
            for timing in ("early", "late"):
                spec = CellSpec(
                    base_family_id=item["base_family_id"],
                    fact_timing=timing,
                    role_ambiguity=ambiguity,
                    image_path=REPOSITORY_ROOT / item["image_path"],
                    field=item["field"],
                    value=item["value"],
                    source_name=source,
                    source_target_id=source_target,
                    destination_name=item["destination_name"],
                    destination_target_id=item["destination_target_id"],
                    task=task,
                    candidates=tuple(item["candidates"]),
                    candidate_prompt_fields=tuple(
                        config.get(
                            "candidate_prompt_fields",
                            ("target_id", "visible_label", "visual_cue", "bounds"),
                        )
                    ),
                )
                by_condition[f"{timing}_{ambiguity}"] = spec
        cells.extend(by_condition[name] for name in config["condition_order"])
    if len(cells) != 32:
        raise ValueError(f"Expected 32 cells, found {len(cells)}")
    return cells


def _fact_block(cell: CellSpec) -> str:
    return "FACT_BLOCK=" + canonical_json(
        {
            "field": cell.field,
            "source": cell.source_name,
            "value": cell.value,
        }
    )


def _context(cell: CellSpec) -> str:
    candidates = [
        {key: item[key] for key in cell.candidate_prompt_fields}
        for item in cell.candidates
    ]
    return "\n".join(
        [
            f"BASE_FAMILY={cell.base_family_id}",
            f"ROLE_AMBIGUITY={cell.role_ambiguity}",
            f"TASK={cell.task}",
            "TARGET_CANDIDATES=" + canonical_json(candidates),
            "ROLE_ENCODING=Return source_entity_id E1 and destination_entity_id E2. "
            "These role IDs do not reveal any target ID.",
            "The attached screenshot is the current mobile UI. Bounds are "
            "[left,top,right,bottom] pixels and are supplied only to map the "
            "blinded target IDs to visible UI regions.",
        ]
    )


def build_call_1(
    cell: CellSpec,
    *,
    counter: TokenCounter,
    contract: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    contract = contract or load_contract()
    fact = _fact_block(cell)
    neutral = build_exact_neutral_block(
        fact_block=fact,
        counter=counter,
        forbidden=(cell.source_name, cell.destination_name, cell.field, cell.value),
    )
    phase_block = fact if cell.fact_timing == "early" else neutral
    prompt = "\n".join(
        [
            _context(cell),
            phase_block,
            contract["grounding_instruction"],
            "OUTPUT_SCHEMA=" + canonical_json(contract["grounding_output_schema"]),
            "Return one bare JSON object. Do not use markdown or reasoning text.",
        ]
    )
    return fact, neutral, prompt


def build_call_2(
    cell: CellSpec,
    *,
    call_1_prompt: str,
    fact: str,
    neutral: str,
    grounding_commitment: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> str:
    contract = contract or load_contract()
    phase_block = neutral if cell.fact_timing == "early" else fact
    commitment = {
        "destination_entity_id": grounding_commitment["destination_entity_id"],
        "destination_target_id": grounding_commitment["destination_target_id"],
        "source_entity_id": grounding_commitment["source_entity_id"],
    }
    prompt = "\n".join(
        [
            "GROUNDING_PHASE_TRANSCRIPT_BEGIN",
            call_1_prompt,
            "GROUNDING_PHASE_TRANSCRIPT_END",
            "CANONICAL_GROUNDING_COMMITMENT=" + canonical_json(commitment),
            phase_block,
            contract["action_instruction"],
            "OUTPUT_SCHEMA=" + canonical_json(contract["action_output_schema"]),
            "For this decision the only valid action type is tap and text must be null.",
            "Return one bare JSON object. Do not use markdown or reasoning text.",
        ]
    )
    logical_transcript = prompt
    if logical_transcript.count(fact) != 1:
        raise ValueError(f"Fact occurrence drift in {cell.cell_id}")
    return prompt


def prompt_certificate(
    config: dict[str, Any],
    *,
    counter: TokenCounter,
) -> list[dict[str, Any]]:
    contract = load_contract()
    certificates: list[dict[str, Any]] = []
    cells = build_cells(config)
    indexed = {(cell.base_family_id, cell.role_ambiguity, cell.fact_timing): cell for cell in cells}
    for family in [item["base_family_id"] for item in resolve_templates(config)]:
        for ambiguity in ("low", "high"):
            prompts: dict[str, tuple[str, str]] = {}
            for timing in ("early", "late"):
                cell = indexed[(family, ambiguity, timing)]
                fact, neutral, call_1 = build_call_1(cell, counter=counter, contract=contract)
                oracle = {
                    "destination_entity_id": "E2",
                    "destination_target_id": cell.destination_target_id,
                    "source_entity_id": "E1",
                }
                call_2 = build_call_2(
                    cell,
                    call_1_prompt=call_1,
                    fact=fact,
                    neutral=neutral,
                    grounding_commitment=oracle,
                    contract=contract,
                )
                prompts[timing] = (call_1, call_2)
            counts = {
                f"{timing}_call_{index + 1}": counter.count_messages(
                    [
                        {"role": "system", "content": contract["system_prompt"]},
                        {"role": "user", "content": prompt},
                    ]
                )
                for timing, pair in prompts.items()
                for index, prompt in enumerate(pair)
            }
            counts["early_total"] = counts["early_call_1"] + counts["early_call_2"]
            counts["late_total"] = counts["late_call_1"] + counts["late_call_2"]
            counts["absolute_total_difference"] = abs(
                counts["early_total"] - counts["late_total"]
            )
            if counts["absolute_total_difference"] != 0:
                raise ValueError(f"Prompt budget mismatch: {family}/{ambiguity}: {counts}")
            certificates.append(
                {"base_family_id": family, "role_ambiguity": ambiguity, **counts}
            )
    return certificates


def _safe_commitment(parsed: dict[str, Any] | None) -> dict[str, str]:
    if parsed is not None:
        return {
            "destination_entity_id": parsed["destination_entity_id"],
            "destination_target_id": parsed["destination_target_id"],
            "source_entity_id": parsed["source_entity_id"],
        }
    # Fixed fallback keeps the second call count constant when call 1 is invalid.
    return {
        "destination_entity_id": "E2",
        "destination_target_id": "A",
        "source_entity_id": "E1",
    }


def run_cell(
    cell: CellSpec,
    *,
    client: TransformersClient,
    counter: TokenCounter,
    output_dir: Path,
) -> dict[str, Any]:
    contract = load_contract()
    allowed = {item["target_id"] for item in cell.candidates}
    fact, neutral, call_1_prompt = build_call_1(cell, counter=counter, contract=contract)
    started = time.monotonic()
    first = client.generate(
        image_path=cell.image_path,
        system_prompt=contract["system_prompt"],
        user_prompt=call_1_prompt,
        episode_id=cell.cell_id,
        call_label="grounding",
        max_tokens=128,
    )
    grounding: dict[str, Any] | None = None
    grounding_error: str | None = None
    try:
        grounding = parse_grounding(first.content, allowed_target_ids=allowed).value
    except DecisionParseError as exc:
        grounding_error = str(exc)
    call_2_prompt = build_call_2(
        cell,
        call_1_prompt=call_1_prompt,
        fact=fact,
        neutral=neutral,
        grounding_commitment=_safe_commitment(grounding),
        contract=contract,
    )
    second = client.generate(
        image_path=cell.image_path,
        system_prompt=contract["system_prompt"],
        user_prompt=call_2_prompt,
        episode_id=cell.cell_id,
        call_label="action",
        max_tokens=128,
    )
    action: dict[str, Any] | None = None
    action_error: str | None = None
    try:
        action = parse_action(second.content, allowed_target_ids=allowed).value
    except DecisionParseError as exc:
        action_error = str(exc)
    valid = grounding is not None and action is not None
    metrics: dict[str, Any] | None = None
    if valid:
        action_target = action["action"]["target_id"]
        metrics = {
            "wrong_target_first_targeting_action": action_target
            != cell.destination_target_id,
            "grounding_destination_correct": grounding["destination_target_id"]
            == cell.destination_target_id,
            "action_target_correct": action_target == cell.destination_target_id,
            "post_grounding_drift": action["grounded_destination_target_id"]
            != grounding["destination_target_id"],
            "exact_value_recall": action["recalled_value"] == cell.value,
            "source_as_target": action_target == cell.source_target_id,
            "other_wrong_target": action_target
            not in {cell.destination_target_id, cell.source_target_id},
        }
    record = {
        "schema_version": "role_binding_timing.dev_pilot_cell.v0_1",
        "cell": {
            **asdict(cell),
            "image_path": str(cell.image_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
            "image_sha256": sha256(cell.image_path.read_bytes()).hexdigest(),
        },
        "prompt_tokens": {
            "call_1": counter.count_messages(
                [
                    {"role": "system", "content": contract["system_prompt"]},
                    {"role": "user", "content": call_1_prompt},
                ]
            ),
            "call_2": counter.count_messages(
                [
                    {"role": "system", "content": contract["system_prompt"]},
                    {"role": "user", "content": call_2_prompt},
                ]
            ),
        },
        "grounding_call": first.audit_record(),
        "action_call": second.audit_record(),
        "parsed_grounding": grounding,
        "parsed_action": action,
        "grounding_parse_error": grounding_error,
        "action_parse_error": action_error,
        "valid": valid,
        "metrics": metrics,
        "wall_time_seconds": time.monotonic() - started,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{cell.cell_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def summarize(records: list[dict[str, Any]], gates: dict[str, float]) -> dict[str, Any]:
    valid = [record for record in records if record["valid"]]
    total = len(records)
    parser_failure_rate = (total - len(valid)) / total if total else 1.0

    def rate(ambiguity: str, timing: str, metric: str) -> float | None:
        selected = [
            record["metrics"][metric]
            for record in valid
            if record["cell"]["role_ambiguity"] == ambiguity
            and record["cell"]["fact_timing"] == timing
        ]
        return sum(bool(value) for value in selected) / len(selected) if selected else None

    wrong = {
        f"{timing}_{ambiguity}": rate(
            ambiguity, timing, "wrong_target_first_targeting_action"
        )
        for ambiguity in ("low", "high")
        for timing in ("early", "late")
    }
    high_difference = (
        wrong["early_high"] - wrong["late_high"]
        if wrong["early_high"] is not None and wrong["late_high"] is not None
        else None
    )
    low_difference = (
        wrong["early_low"] - wrong["late_low"]
        if wrong["early_low"] is not None and wrong["late_low"] is not None
        else None
    )
    interaction = (
        high_difference - low_difference
        if high_difference is not None and low_difference is not None
        else None
    )
    exact_recall = (
        sum(record["metrics"]["exact_value_recall"] for record in valid) / len(valid)
        if valid
        else 0.0
    )
    low_accuracy_values = [
        record["metrics"]["action_target_correct"]
        for record in valid
        if record["cell"]["role_ambiguity"] == "low"
    ]
    low_accuracy = (
        sum(low_accuracy_values) / len(low_accuracy_values)
        if low_accuracy_values
        else 0.0
    )
    source_rates = {
        f"{timing}_{ambiguity}": rate(ambiguity, timing, "source_as_target")
        for ambiguity in ("low", "high")
        for timing in ("early", "late")
    }
    drift_rates = {
        f"{timing}_{ambiguity}": rate(ambiguity, timing, "post_grounding_drift")
        for ambiguity in ("low", "high")
        for timing in ("early", "late")
    }
    qualification_pass = (
        exact_recall >= gates["exact_value_recall_min"]
        and parser_failure_rate < gates["parser_failure_max_exclusive"]
        and low_accuracy > gates["low_ambiguity_target_accuracy_min_exclusive"]
    )
    mechanism_moves = False
    if all(value is not None for value in source_rates.values()):
        mechanism_moves = (
            source_rates["early_high"] - source_rates["late_high"] > 0
        )
    if all(value is not None for value in drift_rates.values()):
        mechanism_moves = mechanism_moves or (
            drift_rates["early_high"] - drift_rates["late_high"] > 0
        )
    signal_pass = bool(
        qualification_pass
        and high_difference is not None
        and high_difference >= gates["high_early_minus_late_wrong_target_min"]
        and low_difference is not None
        and abs(low_difference)
        <= gates["absolute_low_early_minus_late_wrong_target_max"]
        and interaction is not None
        and interaction > 0
        and mechanism_moves
    )
    usage = {
        "calls": total * 2,
        "prompt_tokens_reported": sum(
            record[phase]["usage"].get("prompt_tokens", 0)
            for record in records
            for phase in ("grounding_call", "action_call")
        ),
        "completion_tokens_reported": sum(
            record[phase]["usage"].get("completion_tokens", 0)
            for record in records
            for phase in ("grounding_call", "action_call")
        ),
        "wall_time_seconds": sum(record["wall_time_seconds"] for record in records),
    }
    return {
        "schema_version": "role_binding_timing.dev_pilot_summary.v0_1",
        "development_contaminated": True,
        "confirmatory_claim_allowed": False,
        "total_cells": total,
        "valid_cells": len(valid),
        "parser_failure_rate": parser_failure_rate,
        "exact_value_recall": exact_recall,
        "low_ambiguity_target_accuracy": low_accuracy,
        "wrong_target_rates": wrong,
        "source_as_target_rates": source_rates,
        "post_grounding_drift_rates": drift_rates,
        "high_early_minus_late": high_difference,
        "low_early_minus_late": low_difference,
        "timing_by_ambiguity_interaction": interaction,
        "qualification_pass": qualification_pass,
        "mechanism_diagnostic_moves": mechanism_moves,
        "dev_signal_pass": signal_pass,
        "decision": (
            "EXPAND_TO_CONTROLS_AND_FRESH_HELD_OUT"
            if signal_pass
            else "STOP_OR_REVISE_AFTER_DEV_PILOT"
        ),
        "usage": usage,
    }
