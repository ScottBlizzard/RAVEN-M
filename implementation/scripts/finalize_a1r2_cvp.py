#!/usr/bin/env python3
'''Finalize an already-complete A1-R2 suite without model generation.'''

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_SCHEMA = 'a1r2_cvp_checkpoint_v1'
RESULT_SCHEMA = 'a1r2_cvp_result_v1'
AGGREGATE_SCHEMA = 'a1r2_cvp_post_run_aggregate_v1'
MECHANISM_ID = 'a1r2_compact_verified_pending_v1'
EXPERIMENT_ID = 'A1R2_CVP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1'
TASK_SEED = 20260806
GENERATION_SEED = 3407
A1_LIMITS = {'model_calls': 603, 'total_tokens': 3_464_267, 'elapsed_seconds': 14_595.492}
A0_TASKS = (
    'ExpenseDeleteMultiple2',
    'RetroSavePlaylist',
    'SimpleCalendarAddOneEvent',
    'SportsTrackerTotalDurationForCategoryThisWeek',
)
RECIPE_TASK = 'RecipeDeleteMultipleRecipesWithConstraint'
GATE5_TASKS = A0_TASKS + (RECIPE_TASK,)


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return sha256(raw).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop('content_sha256', None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def usage_totals(summaries: list[dict[str, Any]]) -> dict[str, int]:
    totals = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    for summary in summaries:
        for step in summary.get('steps') or []:
            usage = (step.get('model_call') or {}).get('usage') or {}
            for key in totals:
                totals[key] += int(usage.get(key) or 0)
    return totals


def elapsed_seconds(summary: dict[str, Any]) -> float:
    return (
        datetime.fromisoformat(summary['finished_at'])
        - datetime.fromisoformat(summary['started_at'])
    ).total_seconds()


def expected_order() -> list[str]:
    manifest = json.loads(
        (ROOT / 'implementation/configs/androidworld_hard_v2_instances.json').read_text(
            encoding='utf-8'
        )
    )
    original = [
        str(item['task_class'])
        for item in manifest['instances']
        if int(item['task_seed']) == TASK_SEED
    ]
    if len(original) != 19 or len(set(original)) != 19:
        raise RuntimeError('frozen manifest does not contain 19 unique target tasks')
    return list(GATE5_TASKS) + [name for name in original if name not in GATE5_TASKS]


def gate_report(summaries: list[dict[str, Any]], tasks: tuple[str, ...]) -> dict[str, Any]:
    observed = {str(item['task_name']): item for item in summaries}
    rows = [
        {
            'task_name': name,
            'reward': (observed.get(name) or {}).get('evaluator_reward'),
            'pass': bool((observed.get(name) or {}).get('success')),
        }
        for name in tasks
    ]
    count = sum(int(row['pass']) for row in rows)
    return {
        'status': 'pass' if count == len(tasks) else 'fail',
        'success_count': count,
        'required': len(tasks),
        'tasks': rows,
    }


def pairwise(
    summaries: list[dict[str, Any]], reference: dict[str, Any], arm: str
) -> dict[str, int | float]:
    current = {str(item['task_name']): item for item in summaries}
    refs = {str(item['task_name']): item[arm] for item in reference['tasks']}
    if set(current) != set(refs):
        raise RuntimeError(f'paired {arm} task identity mismatch')
    deltas = [
        int(bool(current[name]['success'])) - int(bool(refs[name]['success']))
        for name in current
    ]
    usage = usage_totals(summaries)
    elapsed = sum(elapsed_seconds(item) for item in summaries)
    base = reference['summaries'][arm]
    return {
        'wins': sum(delta > 0 for delta in deltas),
        'losses': sum(delta < 0 for delta in deltas),
        'ties': sum(delta == 0 for delta in deltas),
        'success_delta': sum(int(bool(item['success'])) for item in summaries)
        - int(base['success_count']),
        'reward_delta': sum(float(item['evaluator_reward']) for item in summaries)
        - float(base['reward_sum']),
        'action_delta': sum(int(item['executed_action_count']) for item in summaries)
        - int(base['executed_actions']),
        'call_delta': sum(int(item['model_call_count']) for item in summaries)
        - int(base['model_calls']),
        'prompt_token_delta': usage['prompt_tokens'] - int(base['prompt_tokens']),
        'completion_token_delta': usage['completion_tokens'] - int(base['completion_tokens']),
        'total_token_delta': usage['total_tokens'] - int(base['total_tokens']),
        'elapsed_delta': elapsed - float(base['valid_elapsed_seconds']),
    }


def load_tokenizer(path: Path):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        str(path), local_files_only=True, trust_remote_code=True
    )


def validate_checkpoint(
    suite_dir: Path, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    errors: list[str] = []
    if checkpoint.get('schema') != CHECKPOINT_SCHEMA:
        errors.append('checkpoint_schema')
    if checkpoint.get('prospective_arm') != 'a1r2':
        errors.append('checkpoint_arm')
    if checkpoint.get('mechanism_id') != MECHANISM_ID:
        errors.append('mechanism_id')
    if checkpoint.get('experiment_id') != EXPERIMENT_ID:
        errors.append('experiment_id')
    summaries = list(checkpoint.get('valid_summaries') or [])
    entries = list(checkpoint.get('a1r2_valid_entries') or [])
    if [str(item.get('task_name')) for item in summaries] != expected_order():
        errors.append('ordered_task_identity')
    if len(summaries) != 19 or len(entries) != 19:
        errors.append('valid_episode_count')
    entry_by_episode = {str(item.get('episode_id')): item for item in entries}
    if len(entry_by_episode) != len(entries):
        errors.append('duplicate_valid_entry')
    signature = json.loads((suite_dir / 'run_signature.json').read_text(encoding='utf-8'))
    signature_sha = canonical_sha256(signature)
    if checkpoint.get('run_signature_sha256') != signature_sha:
        errors.append('run_signature_hash')
    for summary in summaries:
        episode_id = str(summary.get('episode_id'))
        entry = entry_by_episode.get(episode_id) or {}
        episode_path = suite_dir / 'episodes' / episode_id / 'episode.json'
        if not episode_path.is_file():
            errors.append(f'episode_missing:{episode_id}')
            continue
        if file_sha256(episode_path) != entry.get('episode_json_sha256'):
            errors.append(f'episode_hash:{episode_id}')
        if canonical_sha256(summary) != entry.get('summary_sha256'):
            errors.append(f'summary_hash:{episode_id}')
        if entry.get('run_signature_sha256') != signature_sha:
            errors.append(f'entry_run_signature:{episode_id}')
        try:
            reward = float(summary.get('evaluator_reward'))
        except (TypeError, ValueError):
            reward = math.nan
        if not math.isfinite(reward):
            errors.append(f'reward:{episode_id}')
        if summary.get('error') is not None or summary.get('lifecycle_errors'):
            errors.append(f'episode_validity:{episode_id}')
        for step in summary.get('steps') or []:
            attempts = int(
                ((step.get('model_call') or {}).get('raven_meta') or {}).get(
                    'transport_attempts'
                )
                or 0
            )
            if attempts != 1:
                errors.append(f'transport_attempts:{episode_id}:{step.get(step)}')
    invalid_attempts = list(checkpoint.get('invalid_attempts') or [])
    for invalid in invalid_attempts:
        replacement = str(invalid.get('resolved_by_episode_id') or '')
        if replacement not in entry_by_episode:
            errors.append(f'invalid_unresolved:{invalid.get(episode_id)}')
        elif entry_by_episode[replacement].get('task_name') != invalid.get('task_name'):
            errors.append(f'invalid_cross_task_replacement:{invalid.get(episode_id)}')
    if errors:
        raise RuntimeError(f'A1-R2 finalization closure failed: {errors}')
    return summaries


def build_result(
    suite_dir: Path,
    checkpoint: dict[str, Any],
    summaries: list[dict[str, Any]],
    tokenizer_path: Path,
) -> dict[str, Any]:
    reference_path = ROOT / 'evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json'
    reference = json.loads(reference_path.read_text(encoding='utf-8'))
    preflight_path = ROOT / 'evidence/a1r2/A1R2_CVP_ZERO_GENERATION_PREFLIGHT.json'
    preflight = json.loads(preflight_path.read_text(encoding='utf-8'))
    tokenizer = load_tokenizer(tokenizer_path)
    usage = usage_totals(summaries)
    elapsed = sum(elapsed_seconds(item) for item in summaries)
    success_count = sum(int(bool(item['success'])) for item in summaries)
    reward_sum = sum(float(item['evaluator_reward']) for item in summaries)
    total_calls = sum(int(item['model_call_count']) for item in summaries)
    total_actions = sum(int(item['executed_action_count']) for item in summaries)
    total_reads = total_chars = total_memory_tokens = 0
    counters: dict[str, int] = {}
    episode_rows: list[dict[str, Any]] = []
    for summary in summaries:
        read_count = rendered_chars = rendered_tokens = 0
        for step in summary.get('steps') or []:
            text = str((step.get('memory_read') or {}).get('exact_injected_text') or '')
            if text:
                read_count += 1
                rendered_chars += len(text)
                rendered_tokens += len(tokenizer.encode(text, add_special_tokens=False))
        audit = summary.get('memory_mechanism') or {}
        for key, value in (audit.get('counters') or {}).items():
            if isinstance(value, int):
                counters[key] = counters.get(key, 0) + value
        total_reads += read_count
        total_chars += rendered_chars
        total_memory_tokens += rendered_tokens
        episode_path = suite_dir / 'episodes' / str(summary['episode_id']) / 'episode.json'
        episode_rows.append(
            {
                'task_name': summary['task_name'],
                'seed': summary['seed'],
                'episode_id': summary['episode_id'],
                'episode_json_sha256': file_sha256(episode_path),
                'native_max_steps': (summary.get('run_metadata') or {}).get('native_max_steps'),
                'success': bool(summary['success']),
                'reward': float(summary['evaluator_reward']),
                'termination_reason': summary['termination_reason'],
                'model_calls': int(summary['model_call_count']),
                'executed_actions': int(summary['executed_action_count']),
                'token_usage': usage_totals([summary]),
                'elapsed_seconds': elapsed_seconds(summary),
                'memory_active': read_count > 0,
                'active_at_episode_end': bool(audit.get('active')),
                'nonempty_read_count': read_count,
                'rendered_chars': rendered_chars,
                'rendered_tokens': rendered_tokens,
                'write_success_count': int((audit.get('counters') or {}).get('write_success_count') or 0),
                'same_state_refresh_count': int((audit.get('counters') or {}).get('same_state_refresh_count') or 0),
            }
        )
    gate4 = gate_report(summaries, A0_TASKS)
    gate5 = gate_report(summaries, GATE5_TASKS)
    accuracy_pass = success_count > 5 and reward_sum > 5.5 and gate5['status'] == 'pass'
    cost_components = {
        'calls_below_a1': total_calls < A1_LIMITS['model_calls'],
        'tokens_below_a1': usage['total_tokens'] < A1_LIMITS['total_tokens'],
        'elapsed_below_a1': elapsed < A1_LIMITS['elapsed_seconds'],
    }
    cost_pass = all(cost_components.values())
    result = {
        'schema': RESULT_SCHEMA,
        'status': 'COMPLETE',
        'identity': {
            'mechanism_id': MECHANISM_ID,
            'experiment_id': EXPERIMENT_ID,
            'task_seed': TASK_SEED,
            'generation_seed': GENERATION_SEED,
            'implementation_commit': preflight.get('implementation_commit'),
            'source_freeze_content_sha256': preflight.get('source_freeze_content_sha256'),
            'preflight_content_sha256': preflight.get('content_sha256'),
            'preflight_file_sha256': file_sha256(preflight_path),
            'run_signature_sha256': checkpoint['run_signature_sha256'],
            'live_receipt_content_sha256s': checkpoint.get('live_server_receipt_sha256s') or [],
            'paired_reference_sha256': file_sha256(reference_path),
        },
        'closure': {
            'status': 'exact_19_closed',
            'valid_episode_count': len(summaries),
            'invalid_attempt_count': len(checkpoint.get('invalid_attempts') or []),
            'invalid_attempts_resolved': True,
            'ordered_tasks_exact': True,
            'single_transport_per_call': True,
            'generation_calls_during_finalization': 0,
            'source_checkpoint_status': checkpoint.get('status'),
        },
        'gates': {'a0_four': gate4, 'a1_five': gate5},
        'performance': {
            'success_count': success_count,
            'reward_sum': reward_sum,
            'model_calls': total_calls,
            'executed_actions': total_actions,
            'token_usage': usage,
            'valid_elapsed_seconds': elapsed,
        },
        'verdicts': {
            'accuracy': 'PASS' if accuracy_pass else 'FAIL',
            'cost': 'PASS' if cost_pass else 'FAIL',
            'cost_components': cost_components,
            'mechanism': 'NOT_ESTABLISHED_NO_MATCHED_ABLATION',
            'combined': (
                'ACCURACY_PASS_COST_FAIL_MECHANISM_NOT_ESTABLISHED'
                if accuracy_pass and not cost_pass
                else 'SEE_INDEPENDENT_VERDICTS'
            ),
        },
        'pairwise': {
            'versus_a0': pairwise(summaries, reference, 'A0'),
            'versus_a1': pairwise(summaries, reference, 'A1'),
        },
        'memory': {
            'active_episode_count': sum(int(row['memory_active']) for row in episode_rows),
            'nonempty_read_count': total_reads,
            'rendered_chars_total': total_chars,
            'rendered_tokens_total': total_memory_tokens,
            'successful_read_active_tasks': [
                row['task_name'] for row in episode_rows
                if row['success'] and row['nonempty_read_count'] > 0
            ],
            'successful_silent_tasks': [
                row['task_name'] for row in episode_rows
                if row['success'] and row['nonempty_read_count'] == 0
            ],
            'counters': counters,
            'decision_boundary': {
                'extra_model_calls': 0,
                'action_override_count': 0,
                'forced_termination_count': 0,
                'hidden_ui_used_for_decision': False,
                'evaluator_used_for_decision': False,
            },
        },
        'episodes': episode_rows,
        'invalid_attempts': checkpoint.get('invalid_attempts') or [],
        'errors': [],
    }
    result['aggregation_repair'] = {
        'classification': 'evidence_layer_only_no_generation',
        'reason': 'frozen_shared_runner_misroutes_a1r2_to_a12_reference_segments_result_branch',
        'frozen_runner_sha256': file_sha256(
            ROOT / 'implementation/scripts/run_official_qwen_mobile.py'
        ),
        'checkpoint_sha256': file_sha256(suite_dir / 'checkpoint.json'),
        'tokenizer_model_revision': '0cfaf48183f594c314753d30a4c4974bc75f3ccb',
        'transformers_version': version('transformers'),
        'tokenizer_files_sha256': {
            path.name: file_sha256(path)
            for path in sorted(tokenizer_path.iterdir())
            if path.is_file()
        },
    }
    result['content_sha256'] = content_sha256(result)
    aggregate = {
        'schema': AGGREGATE_SCHEMA,
        'suite_id': checkpoint['suite_id'],
        'a1r2_result': result,
        'content_sha256': '',
    }
    aggregate['content_sha256'] = content_sha256(aggregate)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite-dir', type=Path, required=True)
    parser.add_argument('--tokenizer-path', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    suite_dir = args.suite_dir.resolve()
    tokenizer_path = args.tokenizer_path.resolve()
    checkpoint = json.loads((suite_dir / 'checkpoint.json').read_text(encoding='utf-8'))
    summaries = validate_checkpoint(suite_dir, checkpoint)
    aggregate = build_result(suite_dir, checkpoint, summaries, tokenizer_path)
    output = (args.output or (suite_dir / 'aggregate.json')).resolve()
    temporary = output.with_suffix(output.suffix + '.tmp')
    temporary.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    temporary.replace(output)
    print(
        json.dumps(
            {
                'output': str(output),
                'aggregate_sha256': file_sha256(output),
                'content_sha256': aggregate['content_sha256'],
                'performance': aggregate['a1r2_result']['performance'],
                'verdicts': aggregate['a1r2_result']['verdicts'],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
