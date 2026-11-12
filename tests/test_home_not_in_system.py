"""A home station in another system is a navigation gap, not a docking retry.

Ground LIVE 2026-11-12 16:01 (run16): after the mission the ship was left in
another system, so `warp_home` found 0 matching stations and repeated the same
warning every tick for minutes (176 s and counting). That must become a single,
honest BLOCKED: there is no route home, and the bot must not dock some other
station to make progress look good.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.modes.live_security import LiveSecurityRunner
from fila_bot.modes.security import SecurityMode

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


HOME = "Piak III - Moon 6 - Poksu Mineral Group Mineral Reserve"


class ElsewhereEye:
    """In space in another system: no overview entry matches the home station."""

    dll = None

    def __init__(self):
        self._entries = [
            {"Name": "Elonaya - 2% T2 Ice Refinery & Clone", "Type": "Athanor",
             "Distance": "6.6 AU", "center": (1373, 265)},
            {"Name": "Onnamon", "Type": "Stargate (Caldari Region)",
             "Distance": "18 AU", "center": (1373, 553)},
        ]

    def overview_entries(self):
        return list(self._entries)

    def empty_point(self):
        return (396, 720)

    def module_buttons(self):
        return []


runner = LiveSecurityRunner(ElsewhereEye(), dry=True,
                            profile={"home_station": HOME})
runner.win = {"hwnd": 7, "pid": 10}
with patch('fila_bot.modes.live_security.is_foreground', return_value=True):
    r = runner.apply([{"do": "warp_home"}])[0]
ok("no matching home station is reported, not silently docked elsewhere",
   r.get("status") == "HOME_NOT_IN_SYSTEM", str(r))
ok("nothing is clicked when the home station is absent",
   not r.get("input_log"), str(r.get("input_log")))
ok("note names the missing route instead of a station count quibble",
   "route" in (r.get("note") or "").lower(), str(r.get("note")))

m = SecurityMode()
m.on_action_results([r])
ok("the mode stops instead of repeating warp_home every tick",
   m.phase == "BLOCKED", f"{m.phase} {m.blocked}")
ok("the block reason states what the operator must do",
   "route" in (m.blocked or "").lower() and "hệ khác" in (m.blocked or ""),
   m.blocked or "")

# A real home entry must still dock normally.
class HomeEye(ElsewhereEye):
    def __init__(self):
        super().__init__()
        self._entries.append({"Name": HOME, "Type": "Caldari Mining Station",
                              "Distance": "11 AU", "center": (1373, 289)})


runner2 = LiveSecurityRunner(HomeEye(), dry=True,
                             profile={"home_station": HOME})
runner2.win = {"hwnd": 7, "pid": 10}
with patch('fila_bot.modes.live_security.is_foreground', return_value=True):
    r2 = runner2.apply([{"do": "warp_home"}])[0]
ok("an exact home entry still resolves to a dock command (dry)",
   r2.get("status") != "HOME_NOT_IN_SYSTEM"
   and HOME.split(" - ")[0] in (r2.get("note") or ""), str(r2))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
