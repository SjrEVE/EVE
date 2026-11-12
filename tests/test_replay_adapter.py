"""Replay recorded UI trees through the production adapter, with no game input."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.eye import Eye
from fila_bot.modes.live_security import LiveSecurityRunner
from fila_bot.modes.security import SecurityMode

ROOT = Path(__file__).resolve().parents[1]

def replay(name):
    eye = object.__new__(Eye)
    eye.root = json.loads((ROOT / 'tests/fixtures' / name).read_text(encoding='utf-8'))
    eye._pos = None
    eye._pos_root = None
    eye.dll = None
    return LiveSecurityRunner(eye, dry=True, profile={
        'agent_name': 'Iji Kiyura', 'home_station': 'X', 'agent_id': '3010891'})

def run(name):
    r = replay(name)
    w = r.refresh()
    acts = SecurityMode().tick(w)
    results = r.apply(acts) if acts else []
    assert all(x.get('status') != 'FAILED' for x in results), results
    assert all(x.get('verified') is False for x in results), results
    return w, acts, results

w, acts, _ = run('ui_tree_e2e_02_offer_loaded.json')
assert w['offer'] and acts and acts[0]['do'] == 'accept_mission'
print('[PASS] replay offer -> accept action, dry execution only')

w, acts, _ = run('ui_tree_e2e_03_accepted_turnin.json')
assert acts and all(a.get('do') != 'complete_mission' for a in acts), acts
assert acts[0]['do'] in ('set_destination', 'blocked', 'wait'), acts
print('[PASS] replay Complete-button capture never clicks Complete without tracker evidence')

w, acts, _ = run('ui_tree_e2e_04_connection_lost.json')
assert acts and acts[0]['do'] == 'estop'
print('[PASS] replay Connection Lost -> E-STOP')

w, acts, _ = run('ui_tree_e2e_03_accepted_turnin.json')
w2, acts2, _ = run('ui_tree_e2e_03_accepted_turnin.json')
assert [a['do'] for a in acts] == [a['do'] for a in acts2]
print('[PASS] replay is deterministic (same capture -> same actions)')

print('\nKet qua: 4 PASS / 0 FAIL')
