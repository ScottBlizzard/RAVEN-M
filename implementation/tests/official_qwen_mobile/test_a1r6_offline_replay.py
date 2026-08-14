import json
from implementation.scripts.replay_a1r6_goal_anchored_pending import replay
from raven_m.official_qwen_mobile import a1r6_contract as contract
def test_replay_binding() -> None:
    now=replay(contract.REPOSITORY_ROOT/"runs/a1r2_cvp/official_qwen_20260814T145307_50081981"); frozen=json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    for k in ("schema","status","errors","generation_calls","mechanism_id","source","totals","sentinel_tasks","episodes"): assert now[k]==frozen[k]
