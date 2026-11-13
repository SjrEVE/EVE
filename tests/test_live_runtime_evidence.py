"""Read actual drone counts through Eye -> WorldSnapshot -> production adapter."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fila_bot.eye import Eye
from fila_bot.modes.live_security import LiveSecurityRunner

e=Eye.__new__(Eye); e.root=json.loads((ROOT/'tests/fixtures/ui_tree_20261112_runtime.json').read_text(encoding='utf-8')); e._pos=e._pos_root=None
w=LiveSecurityRunner(e,dry=True).refresh()
assert 'capacitor_percent' in w, 'adapter drops the observed capacitor field'
print('[PASS] capacitor observation is exported by production adapter')
assert w['drones_in_space'] == 0, w['drones_in_space']
assert w['drones_out'] is False
assert w['drones_in_bay'] == 10
print('[PASS] recorded actual drone counts reach the live world without assumed defaults')
e.root={}; e._pos=e._pos_root=None
w=LiveSecurityRunner(e,dry=True).refresh()
assert w['drones_in_space'] is None and w['drones_out'] is None
print('[PASS] missing drone panel remains UNKNOWN, not zero')

# A tracker objective header is different from the always-present dialog button.
e.root=json.loads((ROOT/'tests/fixtures/ui_tree_20261112_runtime.json').read_text(encoding='utf-8')); e._pos=e._pos_root=None
w=LiveSecurityRunner(e,dry=True).refresh()
assert w.get('objective_complete') is True, w.get('objective_complete')
assert w.get('mission_agent_id') == '3016214'
print('[PASS] real AllObjectivesComplete tracker state reaches production world with exact agent ID')
e.root=json.loads((ROOT/'tests/fixtures/ui_tree_e2e_03_accepted_turnin.json').read_text(encoding='utf-8')); e._pos=e._pos_root=None
w=LiveSecurityRunner(e,dry=True).refresh()
assert w.get('objective_complete') is not True, 'dialog Complete button is not objective evidence'
print('[PASS] Complete dialog button does not imply tracker objective completion')

e.root=json.loads((ROOT/'tests/fixtures/ui_tree_20261112_runtime.json').read_text(encoding='utf-8')); e._pos=e._pos_root=None
w=LiveSecurityRunner(e,dry=True).refresh()
assert w.get('weapons_active') is False, w.get('weapons_active')
print('[PASS] live module slots yield observed weapon state (not a self-set flag)')
