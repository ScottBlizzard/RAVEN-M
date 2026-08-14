import json
from implementation.scripts.replay_a1r9_run_length_cycle_recovery import replay
from raven_m.official_qwen_mobile import a1r9_contract as c
def test_replay()->None:
 n=replay(c.REPOSITORY_ROOT/"runs/a1r2_cvp/official_qwen_20260814T145307_50081981");f=json.loads(c.OFFLINE_REPLAY_PATH.read_text());
 for k in ("schema","status","errors","generation_calls","mechanism_id","source","totals","sentinel_tasks","episodes"):assert n[k]==f[k]
