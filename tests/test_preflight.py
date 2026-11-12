"""Preflight refuses LIVE when build/window/world identity is not verified."""
import hashlib
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.mission_profile import preflight_world, verify_build
from fila_bot.win import is_foreground

with tempfile.TemporaryDirectory() as td:
    client = Path(td) / 'exefile.exe'
    reader = Path(td) / 'reader.dll'
    client.write_bytes(b'client-build')
    reader.write_bytes(b'reader-build')
    profile = {"character": "Pilot", "agent_name": "Agent", "home_station": "Base",
               "ship_hull": "Gila", "agent_id": "3016214", "level": 1,
               "accept_policy": "non_anomic",
               "client_sha256": hashlib.sha256(b'client-build').hexdigest(),
               "reader_sha256": hashlib.sha256(b'reader-build').hexdigest()}
    ok_world = {"location_known": True, "connection_lost": False, "ship_hull": "Gila"}
    assert preflight_world(profile, ok_world, "EVE - Pilot") == []
    assert verify_build(profile, client, reader) == []
    print('[PASS] matching profile/build/window/world passes')

    assert any('UNKNOWN' in e for e in preflight_world(profile, dict(ok_world, location_known=None), "EVE - Pilot"))
    print('[PASS] unknown location fails closed')

    assert any('does not contain' in e for e in preflight_world(profile, ok_world, "EVE - Someone Else"))
    print('[PASS] wrong character window fails closed')

    assert any('hull mismatch' in e for e in preflight_world(profile, dict(ok_world, ship_hull="Drake"), "EVE - Pilot"))
    print('[PASS] wrong hull fails closed')

    client.write_bytes(b'tampered')
    assert any('client_sha256 mismatch' in e for e in verify_build(profile, client, reader))
    print('[PASS] changed client binary invalidates the pinned build')

assert is_foreground({"hwnd": 7, "pid": 10}, get_foreground=lambda: 7) is True
assert is_foreground({"hwnd": 7, "pid": 10}, get_foreground=lambda: 9) is False
print('[PASS] foreground ownership is hwnd/pid based (no blind input)')

print('\nKet qua: 6 PASS / 0 FAIL')
