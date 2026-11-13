"""Production-world integration regressions; synthetic scenarios, not live proof."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import SecurityMode


def battle(rows, **kw):
    w = dict(docked=False, location_known=True, snapshot_valid=True,
             ship_health={'shield': 1., 'armor': 1., 'structure': 1.},
             hostiles=rows, missions=['Gone Berserk'], active_mission_title='Gone Berserk',
             mission_type_label='Encounter (Deadspace)', mission_panel_observed=True,
             has_active_mission=True, drones_out=True, modules_observed=True,
             weapons_active=True, target_bar_supported=True,
             locked_target={'texts': ['EoM Imp']})
    w.update(kw)
    return w


def npc(name, distance, priority, xy):
    object_id = {"EoM Fiend": 1001, "EoM Imp": 1002}.get(name, 1000)
    return dict(name=name, object_id=object_id, faction='EoM', skip=False, distance=distance,
                priority=priority, center=xy)


rows = [npc('EoM Fiend', '10 km', 1, (10, 10)),
        npc('EoM Imp', '15 km', 6, (20, 20))]
m = SecurityMode(clock=lambda: 100.)
w = battle(rows, mission_level=1)
a = m.tick(w)
assert m._locked_target != 'EoM Fiend', a
assert not any(x['do'] == 'lock_target' and x.get('at') == (10, 10) for x in a), a
print('[PASS] production lowercase hostiles prioritize non-trigger')
for _ in range(4):
    a = m.tick(w)
    assert not any(x['do'] == 'lock_target' and x.get('at') == (10, 10) for x in a), a
print('[PASS] planning does not rotate to trigger while Imp remains alive')

m = SecurityMode(clock=lambda: 100.)
a = m.tick(battle([npc('EoM Imp', '40 km', 6, (20, 20))]))
assert any(x['do'] == 'recall_drones' for x in a), a
assert not any(x['do'] in ('engage_drones', 'launch_drones') for x in a), a
print('[PASS] production target outside leash recalls without contradictory launch/engage')
a = m.tick(battle([npc('EoM Imp', '40 km', 6, (20, 20))]))
assert not any(x['do'] == 'recall_drones' for x in a), a
print('[PASS] recall waits for readback instead of spamming every tick')

m = SecurityMode(clock=lambda: 100.)
a = m.tick(battle(rows, locked_target=None, weapons_active=False))
assert not any(x['do'] in ('fire_weapons', 'engage_drones') for x in a), a
print('[PASS] absent confirmed target never authorizes offensive input')
m = SecurityMode(clock=lambda: 100.)
a = m.tick(battle(rows, mission_level=1,
                   locked_target={'texts': ['EoM Imp'], 'object_id': 1002,
                                  'is_active': True}, weapons_active=None))
assert any(x['do'] == 'fire_weapons' for x in a), a
print('[PASS] weapon activation resumes after delayed lock readback')
