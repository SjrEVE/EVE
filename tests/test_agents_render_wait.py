"""An empty agent list right after docking is a render race, not "no agent".

Ground LIVE 2026-11-12 16:48: the ship docked at the home station and the FSM
blocked on the first tick with "Không tìm thấy Security Agent khả dụng trong trạm
này". A fresh read a few seconds later returned four agents, including
`Jitkavaja Ninsen, Security, level 1, available: true` — the station list simply
had not rendered yet. The bot must wait, bounded, before concluding.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.security import AGENTS_RENDER_WAIT_S, SecurityMode

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {msg}")


JITKA = {"name": "Jitkavaja Ninsen", "level": 1, "division": "Security",
         "available": True, "chat_xy": [1562, 611]}
PUROTO = {"name": "Puroto Ichokoda", "level": 2, "division": "Security",
          "available": True, "chat_xy": [1562, 662]}
MINER = {"name": "Aizagenen Arozainen", "level": 1, "division": "Mining",
         "available": True, "chat_xy": [1562, 560]}


def docked(**kw):
    w = {"docked": True, "location_known": True, "snapshot_valid": True,
         "connection_lost": False, "has_active_mission": None,
         "mission_panel_observed": False, "missions": None,
         "ship_health": {"shield": 1.0, "armor": 1.0, "hull": 1.0},
         "agent_dialog_open": False, "agents": [],
         "agent_name": "Jitkavaja Ninsen", "offer": None}
    w.update(kw)
    return w


clock = {"t": 6000.0}
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(docked())
ok("empty agent list after docking waits instead of blocking",
   acts[0]["do"] == "wait" and m.phase != "BLOCKED", f"{m.phase} {acts}")
ok("the wait says it is a render wait",
   "render" in (m.status().get("detail") or "").lower(),
   str(m.status().get("detail")))

# List renders -> open the preferred agent, not just the first security one.
clock["t"] += 3.0
acts = m.tick(docked(agents=[MINER, PUROTO, JITKA]))
ok("once rendered, the preferred level-1 security agent is used",
   acts[0]["do"] == "open_agent_chat" and tuple(acts[0]["at"]) == (1562, 611), str(acts))

# Never renders -> still blocks, with the truthful reason.
m2 = SecurityMode(clock=lambda: clock["t"])
m2.tick(docked())
clock["t"] += AGENTS_RENDER_WAIT_S + 1.0
acts = m2.tick(docked())
ok("a station that really has no security agent still blocks",
   acts[0]["do"] == "blocked" and m2.phase == "BLOCKED", f"{m2.phase} {acts}")

# A mining-only station is a real block, not a wait loop.
m3 = SecurityMode(clock=lambda: clock["t"])
m3.tick(docked(agents=[MINER]))
clock["t"] += AGENTS_RENDER_WAIT_S + 1.0
acts = m3.tick(docked(agents=[MINER]))
ok("mining-only station blocks after the grace",
   acts[0]["do"] == "blocked", str(acts))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
