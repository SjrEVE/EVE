"""Test modes/security.py — PYTHONPATH=src python tests/test_security.py"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.modes.security import WAVE_WAIT_S, SecurityMode  # noqa: E402


def ok(n):
    print(f"[PASS] {n}")


class FakeMe:
    def __init__(self):
        self.phase = "DOCKED"
        self.hp = None

    def state(self):
        return SimpleNamespace(phase=self.phase, hp=self.hp)


class FakeRunner:
    def __init__(self):
        self.me = FakeMe()
        self.acts = [{"do": "undock"}]
        self.calls = 0

    def next_actions(self):
        self.calls += 1
        return list(self.acts)


clock = {"t": 0.0}


def mk():
    r = FakeRunner()
    return SecurityMode(r, clock=lambda: clock["t"]), r


# 1. docked -> chuyen cho runner, safe point
m, r = mk()
assert m.tick(None) == [{"do": "undock"}] and m.at_safe_point
ok("DOCKED -> runner.next_actions, safe point")

# 2. hp thap o site -> warp_out, khong goi runner
m, r = mk()
r.me.phase, r.me.hp = "AT_SITE", {"shield": 0.1, "armor": 0.9, "structure": 1.0}
a = m.tick(None)
assert a[0]["do"] == "warp_out" and r.calls == 0
ok("hp < 25% o site -> warp_out")

# 3. wave_wait truoc khi di gate
m, r = mk()
r.me.phase, r.me.hp = "POCKET_CLEAR", {"shield": 1.0}
r.acts = [{"do": "gate", "label": "Acceleration Gate"}]
clock["t"] = 100.0
assert m.tick(None)[0]["do"] == "wait"
clock["t"] = 100.0 + WAVE_WAIT_S - 1
assert m.tick(None)[0]["do"] == "wait" and r.calls == 0
clock["t"] = 100.0 + WAVE_WAIT_S
assert m.tick(None)[0]["do"] == "gate"
ok("POCKET_CLEAR -> cho 18s roi moi gate")

# 4. wave den muon reset dong ho
r.me.phase = "AT_SITE"; m.tick(None)
assert m.clear_since is None
r.me.phase = "POCKET_CLEAR"
assert m.tick(None)[0]["do"] == "wait"
ok("quai quay lai -> reset wave_wait")

# 5. STOP: ngoai space -> warp_home; docked -> dung yen; dang danh -> danh tiep
m, r = mk()
m.request_safe_stop()
r.me.phase = "IN_SPACE"
assert m.tick(None)[0]["do"] == "warp_home"
r.me.phase = "DOCKED"
assert m.tick(None) == [] and m.at_safe_point
r.me.phase, r.acts = "AT_SITE", [{"do": "fight"}]
assert m.tick(None)[0]["do"] == "fight"
ok("STOP: warp_home / dung o dock / dang danh thi danh not")

# 6. runner blocked -> status.blocked
m, r = mk()
r.acts = [{"do": "blocked", "why": "AgentDialogueWindow chua ground"}]
m.tick(None)
assert m.status()["blocked"] == "AgentDialogueWindow chua ground"
ok("runner blocked -> status hien ly do")

print("ALL OK test_security")
