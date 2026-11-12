"""Return destination must be the configured home, never the first station."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.live_security import LiveSecurityRunner


class FakeEye:
    dll = None
    def __init__(self, entries):
        self.entries = entries
        self.clicked = []
    def overview_entries(self): return self.entries
    def mission_location_button(self): return None
    def empty_point(self): return (320, 763)
    def context_menus(self): return []
    def send_click(self, *a, **kw): self.clicked.append(a)


def run(entries, profile):
    fe = FakeEye(entries)
    r = LiveSecurityRunner(fe, dry=True, profile=profile).apply([{"do": "warp_home"}])
    return r[0], fe

entries = [
    {"Name": "Perimeter II - Moon 1", "Type": "Station", "center": (11, 22)},
    {"Name": "Exact Base", "Type": "Station", "center": (33, 44)},
]
r, fe = run(entries, {"home_station": "Exact Base"})
assert r["ok"] is True and r.get("verified") is False, r
coords = [(s.get("at") or (s.get("x"), s.get("y"))) for s in r.get("input_log", [])]
assert (33, 44) in coords and (11, 22) not in coords, r
print('[PASS] warp_home selects the exact configured station, not the first entry')

r2, fe2 = run([entries[0]], {"home_station": "Exact Base"})
assert r2["ok"] is False and "Exact Base" in str(r2.get("note")), r2
assert not fe2.clicked
print('[PASS] missing configured home blocks, never docks at a different station')

r3, _ = run(entries, None)
assert r3["ok"] is True, r3
print('[PASS] no configured home keeps the legacy first-station behavior (SIM/legacy only)')

print('\nKet qua: 3 PASS / 0 FAIL')
