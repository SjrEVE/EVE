"""Test CLI & LiveDistributionRunner — verify end-to-end integration khong can client.
PYTHONPATH=src python tests/test_cli_and_live.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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


# 1. build_supervisor khong con nem ModeUnavailable cho live distribution.
# Eye that co the nem RuntimeError khi EVE client tat (DLL initialize fail) —
# do la fail-closed dung, khong phai bi chan logic. Chi assert khong co ModeUnavailable.
try:
    sup = build_supervisor("distribution", sim=False, dry=True)
    assert sup is not None
    assert hasattr(sup, "mode") and sup.mode.name == "distribution"
    ok("build_supervisor: distribution LIVE (sim=False) hop le, khong bi chan")
except ModeUnavailable as e:
    raise AssertionError(f"distribution LIVE van bi chan ModeUnavailable: {e}")
except RuntimeError as e:
    ok("build_supervisor: khong con ModeUnavailable; DLL init fail vi EVE client tat (dung)")

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
assert len(res) == 3
assert res[0]["action"] == "click" and res[0]["ok"] is True and res[0]["dry"] is True
assert res[1]["action"] == "hotkey_dock_jump" and res[1]["ok"] is True
ok("LiveDistributionRunner.apply: thuc thi click va hotkey_dock_jump dry-run thanh cong")

# 5. End-to-end integration: DistributionMode FSM + LiveDistributionRunner
mode = DistributionMode()
assert mode.phase == "AGENT"
# Buoc 1: chua co offer -> doi mo agent
w_no_offer = dict(w)
w_no_offer["offer"] = None
acts = mode.tick(w_no_offer)
assert acts[0]["do"] == "open_agent"
# Buoc 2: da co offer -> quyet dinh accept
acts = mode.tick(w)
assert acts[0]["do"] == "click"
assert "accept" in acts[0]["why"]
assert mode.phase == "LOAD"
ok("End-to-End: DistributionMode + LiveDistributionRunner tick qua AGENT -> OFFER -> LOAD dung")

print("\nALL OK test_cli_and_live")
