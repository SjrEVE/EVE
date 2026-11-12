"""A stale ledger key must not abandon a mission the game already gave us.

Ground LIVE 2026-11-12 17:27 (Piak): the earlier run clicked Complete on 'The
Guristas Spies', but that turn-in could not be counted (the tracker vanished
before the panel read-back), so the ledger kept it active. The next run accepted
'The Roving Rogue Drones' from the agent and only THEN hit
MISSION_IDENTITY_CONFLICT — a mission accepted and abandoned.

Rules pinned here:
1. `reconcile_absent` clears a stale key only when the game shows NO mission at
   all, and it must NOT count a completion (no fabricated success).
2. `confirm_turnin` accepts dialog evidence in place of a rendered panel, because
   EVE removes the tracker after a successful turn-in but the dialog says
   "Objectives Complete".
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.mission_session import MissionSession

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


tmp = Path(tempfile.mkdtemp()) / "sess.json"
s = MissionSession("Kompi Yaken", "3016216", "Piak III - Moon 6", path=tmp)
key_old = s.bind("The Guristas Spies")

# Only one of the two evidence flags is not enough.
# Ground 13-11 (Boss): mission_absent=True ĐỦ để clear — tracker None khi docked
# là bằng chứng mission hết (dock = không có mission đang làm trong space).
ok("clear with mission_absent only (tracker None, panel not rendered)",
   s.reconcile_absent(panel_observed=False, mission_absent=True) is True
   and s.active_key is None, str(s.active_key))

# Re-bind lại key cũ để test phần full-evidence vẫn hoạt động
s.bind("The Blockade")
key_old = s.active_key

# Full evidence clears the key without counting a completion.
ok("stale key cleared when the game lists no mission",
   s.reconcile_absent(panel_observed=True, mission_absent=True) is True
   and s.active_key is None, str(s.active_key))
ok("clearing a stale key never fabricates a completion",
   s.completed == 0 and s._completed_keys == set(), f"{s.completed} {s._completed_keys}")

# A different mission may now be bound without conflict.
key_new = s.bind("The Roving Rogue Drones")
ok("a new mission binds after reconciliation", key_new != key_old, key_new)
ok("ledger on disk reflects the new mission",
   json.loads(tmp.read_text(encoding="utf-8"))["title"] == "The Roving Rogue Drones",
   tmp.read_text(encoding="utf-8"))

# Dialog evidence alone counts a real turn-in.
ok("turn-in counted with dialog evidence instead of a rendered panel",
   s.confirm_turnin(key_new, objective_complete=True, response_confirmed=True,
                    panel_observed=False, mission_absent=True,
                    dialog_evidence=True) is True,
   str(s.completed))
ok("completion is counted exactly once", s.completed == 1, str(s.completed))

# Without dialog evidence the strict path must still refuse.
s2 = MissionSession("K", "1", "S", path=Path(tempfile.mkdtemp()) / "s2.json")
k2 = s2.bind("Furrier Fiasco")
ok("no turn-in counted when only absence is claimed",
   s2.confirm_turnin(k2, objective_complete=True, response_confirmed=True,
                     panel_observed=False, mission_absent=True) is False,
   str(s2.completed))

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
