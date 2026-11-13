"""Exact objective target resolution — no substring, no first-entry fallback."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.mission_target import resolve_objective_target

from fila_bot.mission import MissionEye

class OverviewStub:
    def overview_entries(self):
        return [{"Name": "Pithi Arrogator", "Type": "Frigate", "center": (12, 34),
                 "Distance": "12 km", "object_id": 30000142}]

live_hostiles = MissionEye(OverviewStub()).hostiles()
assert len(live_hostiles) == 1 and live_hostiles[0].get("object_id") == 30000142
print('[PASS] overview itemID survives hostile classification')

TEXT = ('You need to approach <a href= showinfo:10131//9002321446000117567 >'
        'Fire Cloud</a>')
entries = [
    {"Name": "Fire Cloud", "center": (10, 20), "Distance": "1,200 m"},
    {"Name": "Fire Cloud 2", "center": (30, 40), "Distance": "8 km"},
    {"Name": "Acceleration Gate", "center": (50, 60), "Distance": "0 m"},
]
t = resolve_objective_target(TEXT, entries)
assert t is not None, 'exact Fire Cloud entry must resolve'
assert t['label'] == 'Fire Cloud' and t['center'] == (10, 20), t
assert t['item_id'] == 9002321446000117567 and t['distance_m'] == 1200.0, t
print('[PASS] exact label + showinfo identity + distance resolve')

assert resolve_objective_target(TEXT, [{"Name": "Fire Cloud 2", "center": (1, 2)}]) is None
print('[PASS] substring/suffix label never becomes the objective target')

assert resolve_objective_target(TEXT, [{"Name": "Fire Cloud", "center": (1, 2)},
                                       {"Name": "fire cloud", "center": (3, 4)}]) is None
print('[PASS] duplicate exact labels are ambiguous, not silently first')

assert resolve_objective_target(TEXT, [{"Name": "Fire Cloud", "center": None}]) is None
print('[PASS] entry without a real center cannot authorize a click')

assert resolve_objective_target('You need to activate the Acceleration Gate', entries) is None
print('[PASS] non-approach objective does not select an overview target')

# Ground 13-11: 'AU' parse ĐƯỢC đơn vị (3 AU = 448.8 tỷ m) — FSM tự quyết
# out-of-range; helper không được trả None (unknown) cho distance biết chắc.
assert resolve_objective_target(TEXT, [{"Name": "Fire Cloud", "center": (1, 2),
                                       "Distance": "3 AU"}])['distance_m'] == 3 * 149_597_870_700.0
print('[PASS] AU distance parsed with true unit, FSM decides out-of-range')

print('\nKet qua: 6 PASS / 0 FAIL')
