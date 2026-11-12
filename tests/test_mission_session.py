"""SYNTHETIC context: exact chain identity and owner return destination, not a live result."""
import sys,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
assert importlib.util.find_spec('fila_bot.mission_session') is not None, 'durable mission session missing'
from fila_bot.mission_session import MissionSession
s=MissionSession(character='Pilot',agent_id='3016214',home_station='Exact Base')
key=s.bind('Chain (1 of 5)',agent_id='3016214')
assert key and s.home_station=='Exact Base'
assert s.bind('Chain (1 of 5)',agent_id='3016214')==key
try:
    s.bind('Chain (2 of 5)',agent_id='3016214')
except ValueError: pass
else: raise AssertionError('unconfirmed chain switch must not overwrite active mission')
assert not s.confirm_turnin(key,objective_complete=True,response_confirmed=False,panel_observed=True,mission_absent=True)
assert s.completed==0
assert s.confirm_turnin(key,objective_complete=True,response_confirmed=True,panel_observed=True,mission_absent=True)
assert not s.confirm_turnin(key,objective_complete=True,response_confirmed=True,panel_observed=True,mission_absent=True)
assert s.completed==1 and s.bind('Chain (2 of 5)',agent_id='3016214')!=key
print('[PASS] exact mission session persists through repeated observation, rejects ambiguity, deduplicates verified completion')
