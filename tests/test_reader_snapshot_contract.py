"""Missing snapshot must stay UNKNOWN all the way through production refresh/tick."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.eye import Eye
from fila_bot.modes.live_security import LiveSecurityRunner
from fila_bot.modes.security import SecurityMode

e=Eye.__new__(Eye); e.root=None; e._pos=e._pos_root=None
r=LiveSecurityRunner(e,dry=True)
w=r.refresh()
assert w.get('location_state') == 'UNKNOWN', w
assert w.get('has_active_mission') is None, w
m=SecurityMode(runner=r)
a=m.tick(w)
assert not m._was_in_space and a and a[0]['do'] in ('wait','blocked'), (a,m._was_in_space)
assert not any(x.get('do') in ('undock','warp_to_mission','warp_home') for x in a)
print('[PASS] absent reader data does not become in-space or mission-empty in production')
