"""Session ledger survives restart; a foreign/corrupt file is never trusted."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.mission_session import MissionSession

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / 'session.json'
    s = MissionSession('Pilot', '3016216', 'Base', path=path)
    key = s.bind('Chain (1 of 5)')
    assert path.exists()

    s2 = MissionSession('Pilot', '3016216', 'Base', path=path)
    assert s2.active_key == key and s2.title == 'Chain (1 of 5)' and s2.completed == 0
    print('[PASS] active mission identity survives a restart')

    assert s2.confirm_turnin(key, objective_complete=True, response_confirmed=True,
                             panel_observed=True, mission_absent=True)
    s3 = MissionSession('Pilot', '3016216', 'Base', path=path)
    assert s3.completed == 1 and s3.active_key is None
    assert not s3.confirm_turnin(key, objective_complete=True, response_confirmed=True,
                                 panel_observed=True, mission_absent=True)
    assert s3.completed == 1
    print('[PASS] completed count persists and cannot be counted twice')

    bad = Path(td) / 'other.json'
    bad.write_text(json.dumps({'character': 'Someone', 'agent_id': '3016216',
                               'home_station': 'Base', 'completed': 99}), encoding='utf-8')
    try:
        MissionSession('Pilot', '3016216', 'Base', path=bad)
    except ValueError as exc:
        assert 'identity mismatch' in str(exc)
    else:
        raise AssertionError('foreign session file must be rejected')
    print('[PASS] session file from another character/owner is rejected')

    corrupt = Path(td) / 'corrupt.json'
    corrupt.write_text('{not json', encoding='utf-8')
    try:
        MissionSession('Pilot', '3016216', 'Base', path=corrupt)
    except ValueError:
        pass
    else:
        raise AssertionError('corrupt session file must be rejected')
    print('[PASS] corrupt ledger fails closed instead of counting from zero')

print('\nKet qua: 4 PASS / 0 FAIL')
