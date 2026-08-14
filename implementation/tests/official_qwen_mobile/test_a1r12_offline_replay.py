import json
from implementation.scripts.replay_a1r12_compacted_history_pending import replay
from raven_m.official_qwen_mobile import a1r12_contract as c
def test_replay()->None:
 now=replay(c.REPOSITORY_ROOT/"runs/a1r2_cvp/official_qwen_20260814T145307_50081981");frozen=json.loads(c.OFFLINE_REPLAY_PATH.read_text())
 for key in ("schema","status","errors","generation_calls","mechanism_id","source","totals","sentinel_tasks","episodes"):assert now[key]==frozen[key]
