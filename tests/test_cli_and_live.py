"""Test CLI & LiveDistributionRunner — verify end-to-end integration khong can client.
PYTHONPATH=src python tests/test_cli_and_live.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.modes.distribution import DistributionMode  # noqa: E402
from fila_bot.modes.live_distribution import LiveDistributionRunner  # noqa: E402
from fila_bot.ui_model import ModeUnavailable, build_supervisor  # noqa: E402

FX = ROOT / "tests" / "fixtures"


def ok(n):
    print(f"[PASS] {n}")


def make_eye(fixture_name: str) -> Eye:
    e = Eye.__new__(Eye)
    for k in ("root", "_pos", "_pos_root"):
        setattr(e, k, None)
    e.root = json.load(open(FX / fixture_name, encoding="utf-8"))
    return e


from unittest import mock

# 1. build_supervisor khong con nem ModeUnavailable cho live distribution.
class _MockEye:
    dll = None
    root = None
    def __init__(self, *args, **kwargs):
        pass
    def refresh(self):
        return None

with mock.patch("fila_bot.eye.Eye", _MockEye):
    try:
        sup = build_supervisor("distribution", sim=False, dry=True)
        assert sup is not None
        assert hasattr(sup, "mode") and sup.mode.name == "distribution"
        ok("build_supervisor: distribution LIVE (sim=False) hop le, khong bi chan")
    except ModeUnavailable as e:
        raise AssertionError(f"distribution LIVE van bi chan ModeUnavailable: {e}")

# 2. LiveDistributionRunner tren ui_tree_agent_offer.json
eye_offer = make_eye("ui_tree_agent_offer.json")
runner = LiveDistributionRunner(eye_offer, dry=True)
w = runner.refresh()
assert w["docked"] is True
assert w["offer"] is not None
assert w["offer"]["title"] == "Rancorous Researcher (1 of 5)"
assert w["offer"]["cargo_m3"] == 0.1
assert w["offer"]["buttons"]["accept"] is not None
ok("LiveDistributionRunner.refresh: doc offer tu fixture ui_tree_agent_offer.json dung")

# 3. LiveDistributionRunner tren ui_tree_connection_lost.json -> E-STOP popup
eye_conn = make_eye("ui_tree_connection_lost.json")
runner_conn = LiveDistributionRunner(eye_conn, dry=True)
w_conn = runner_conn.refresh()
assert w_conn["popup"] is not None
assert "Connection Lost" in w_conn["popup"]
mode = DistributionMode()
acts = mode.tick(w_conn)
assert mode.phase == "BLOCKED"
ok("LiveDistributionRunner: popup Connection Lost -> mode BLOCKED, E-STOP an toan")

# 4. LiveDistributionRunner.apply chuyen action logic -> ActionSpec dry-run
acts_in = [
    {"do": "click", "at": (503, 808)},
    {"do": "hotkey_dock_jump", "at": (914, 148)},
    {"do": "load_cargo"},
]
res = runner.apply(acts_in)
# load_cargo: eye_offer khong co Inventory window -> runner append "mo Inventory truoc"
# (tick sau se chon ItemHangar). 3 action tra ve day du.
assert len(res) == 3, res
assert res[0]["action"] == "click" and res[0]["ok"] is True and res[0]["dry"] is True
assert res[1]["action"] == "hotkey_dock_jump" and res[1]["ok"] is True
assert res[2]["action"] == "load_cargo"
ok("LiveDistributionRunner.apply: thuc thi click va hotkey_dock_jump dry-run thanh cong")

# 5. End-to-end integration: DistributionMode FSM + LiveDistributionRunner
mode = DistributionMode()
assert mode.phase == "AGENT"
# Buoc 1: chua co offer -> doi mo agent
w_no_offer = dict(w)
w_no_offer["offer"] = None
acts = mode.tick(w_no_offer)
assert acts[0]["do"] == "open_agent"
# Buoc 2: co offer nhung CHUA doc duoc cho trong cargo -> mo Inventory, KHONG accept mu
acts = mode.tick(w)
assert acts[0]["do"] == "open_inventory", acts
# Buoc 3: da du du kien (cargo trong + route hisec) -> accept
w_ok = dict(w, cargo_free=50.0, route_hisec=True)
acts = mode.tick(w_ok)
assert acts[0]["do"] == "click", acts
assert "accept" in acts[0]["why"]
assert mode.phase == "LOAD"
ok("End-to-End: DistributionMode + LiveDistributionRunner tick qua AGENT -> OFFER -> LOAD dung")

# 6. Live execution is owned by the exact client PID and releases on terminal return.
from fila_bot import cli  # noqa: E402
class _LockHandle:
    closed = False
    def close(self):
        self.closed = True

handle = _LockHandle()
called = []
window = {"pid": 4242}
with mock.patch.object(cli, "find_client_window", return_value=window), \
     mock.patch.object(cli, "find_all_client_windows", return_value=[]), \
     mock.patch("fila_bot.runtime_lock.acquire", return_value=handle) as acquire:
    result = cli._run_with_client_lock(True, lambda win: called.append(win) or 7)
assert result == 7 and called == [window] and handle.closed
acquire.assert_called_once_with(4242, client_id="eve-pid-4242", owner_pid=os.getpid())
ok("live runner acquires the client-PID OS lock before work and releases it")

called.clear()
with mock.patch.object(cli, "find_client_window", return_value={"pid": 4242}), \
     mock.patch.object(cli, "find_all_client_windows", return_value=[]), \
     mock.patch("fila_bot.runtime_lock.acquire", side_effect=OSError("already owned")):
    result = cli._run_with_client_lock(True, lambda _win: called.append("run") or 7)
assert result == 3 and not called
ok("duplicate live runner is refused before work")

called.clear()
with mock.patch.object(cli, "find_all_client_windows",
                       return_value=[{"pid": 4242}, {"pid": 4343}]), \
     mock.patch.object(cli, "find_client_window", return_value={"pid": 4242}), \
     mock.patch("fila_bot.runtime_lock.acquire", return_value=handle) as acquire:
    multi_rc = cli._run_with_client_lock(True, lambda win: called.append(win) or 7)
assert multi_rc == 3 and not called
acquire.assert_not_called()
ok("live runner refuses ambiguous multiple EVE windows before taking input ownership")

# Every production live command enters the shared ownership gate before a runner is built.
window = {"pid": 4242}
seen_live = []
def invoke_owned(is_live, run):
    seen_live.append(is_live)
    return run(window if is_live else None)
args = SimpleNamespace(live=True, confirm_input=False, max_missions=1,
                       max_hours=1, allow_unknown_sec=False, dll=None, tick=0.1,
                       filament="test", engine="fsm", max_runs=1,
                       profile=None, preflight=False)
with mock.patch.object(cli, "_run_with_client_lock", side_effect=invoke_owned), \
     mock.patch.object(cli, "_distribution_run", return_value=21), \
     mock.patch.object(cli, "_abyss_run", return_value=22), \
     mock.patch.object(cli, "_security_run", return_value=23):
    assert cli.cmd_distribution(args) == 21
    assert cli.cmd_abyss(args) == 22
    assert cli.cmd_security(args) == 23
assert seen_live == [True, True, True], seen_live
ok("distribution/abyss/security all route through client ownership")

with mock.patch.object(cli, "_run_with_client_lock", side_effect=invoke_owned), \
     mock.patch.object(cli, "_opportunities", return_value=24):
    assert cli.cmd_opportunities(SimpleNamespace(open=True)) == 24
ok("input-enabled Opportunities command routes through client ownership")

from fila_bot import mission_cli  # noqa: E402
with mock.patch("fila_bot.cli._run_with_client_lock",
                side_effect=lambda is_live, run: run(window)), \
     mock.patch.object(mission_cli, "_run_with_window", return_value=25) as run_window:
    assert mission_cli.cmd_run(SimpleNamespace(go=True)) == 25
run_window.assert_called_once_with(SimpleNamespace(go=True), window)
ok("legacy mission --go route uses the same ownership gate")

mission_me = mock.Mock()
mission_runner = mock.Mock()
mission_args = SimpleNamespace(dll=None, orbit=2500, go=True, max_rounds=1, wait=0)
mission_window = {"pid": 4242, "title": "EVE", "origin": (0, 0), "size": (100, 100)}
with mock.patch.object(mission_cli, "_open_eye", return_value=object()), \
     mock.patch.object(mission_cli, "MissionEye", return_value=mission_me), \
     mock.patch.object(mission_cli, "MissionRunner", return_value=mission_runner), \
     mock.patch.object(mission_cli, "find_client_window", return_value=None), \
     mock.patch.object(mission_cli, "focus"), \
     mock.patch.object(mission_cli.time, "sleep", return_value=None):
    closed_mission_rc = mission_cli._run_with_window(mission_args, mission_window)
assert closed_mission_rc == 2 and not mission_me.state.called \
    and not mission_runner.next_actions.called, (closed_mission_rc, mission_me, mission_runner)
ok("mission --go stops before reading/acting after client session ends")

print("\nALL OK test_cli_and_live")
