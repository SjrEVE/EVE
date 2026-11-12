"""Input delivery is not game confirmation. All input is dry or replaced by a spy."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fila_bot import control as ctl
spec=ctl.ActionSpec('probe',[{'do':'click','at':(10,20)}])
r=ctl.execute(spec,dry=True)
assert r['verified'] is False, r
assert r['status']=='DRY_RUN' and r['ok'] is True, r
print('[PASS] unverified dry input is DRY_RUN, not observed game success')
with patch.object(ctl.inp,'send_click',return_value={'ok':False,'fail':'synthetic input failure'}):
    r=ctl.execute(spec,dry=True)
assert not r['ok'] and not r['verified'],r
print('[PASS] low-level failure propagates through control result')

# Production adapter must propagate refusal instead of setting synthetic flags.
import json
from fila_bot.eye import Eye
from fila_bot.modes.live_security import LiveSecurityRunner
ROOT=Path(__file__).resolve().parents[1]
e=Eye.__new__(Eye); e.root=json.loads((ROOT/'tests/fixtures/ui_tree_20261112_runtime.json').read_text(encoding='utf-8')); e._pos=e._pos_root=None
runner=LiveSecurityRunner(e,dry=True); runner.refresh()
with patch.object(ctl,'execute',return_value={'ok':False,'verified':False,'status':'FAILED','fail':'synthetic refusal'}), patch('fila_bot.modes.live_security.time.sleep'):
    r=runner.apply([{'do':'launch_drones'}])
assert r and r[0]['ok'] is False and not runner._drones_out, r
print('[PASS] adapter propagates failed execution and never self-confirms drone launch')
assert runner.apply([{'do':'NOT_A_REAL_ACTION'}])[0]['ok'] is False
print('[PASS] unknown live action fails visibly instead of silent success')
