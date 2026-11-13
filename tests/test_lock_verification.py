"""Lock must be read back from the client's target bar before drones attack.

Ground LIVE 2026-11-12 — the owner's objection: "drone thả ra ko lock target thì
bắn kiểu gì?". It was correct:

- `_verify_locked()` in control.py was hard-coded `return False`, so a lock was
  never confirmed anywhere in the system.
- `engage_drones` sends `F`, which orders drones to attack the target currently
  LOCKED — with nothing locked it is a no-op, so the pocket never cleared.

Evidence used: `TargetInBar` nodes (one per locked target) with a descendant
`ActiveTargetOnBracket` marking the active one — the exact rule Sanderling's
parser uses (`.hermes/research/viir/ParseUserInterface.elm`,
`parseTargetsFromUITreeRoot` / `parseTarget`), and the reader already emits those
type names.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.eye import Eye
from fila_bot.modes.security import LOCK_MAX_ATTEMPTS, LOCK_RETRY_S, SecurityMode

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


def tree(targets):
    """Minimal UI tree: TargetInBar nodes, active one carrying ActiveTargetOnBracket."""
    nodes = []
    for i, (name, active) in enumerate(targets):
        kids = []
        if active:
            kids.append({"type": "ActiveTargetOnBracket", "attrs": {}, "children": []})
        nodes.append({
            "type": "TargetInBar",
            "attrs": {"_name": f"targetInBar{i}", "_displayX": 100, "_displayY": 40 + i * 40,
                      "_displayWidth": 90, "_displayHeight": 36,
                      "_setText": name},
            "children": kids,
        })
    return {"type": "UIRoot", "attrs": {}, "children": nodes}


class BarEye(Eye):
    """Eye with no client attached; only the target bar is real."""
    def __init__(self, ui):
        self.root = ui
        self.dll = None

    def absolute(self, *a, **k):
        return None


e = BarEye(tree([("Pithi Arrogator", True), ("Pithi Invader", False)]))
locked = e.locked_target()
ok("a locked target is read from TargetInBar + ActiveTargetOnBracket",
   locked is not None and "Arrogator" in (locked.get("name") or ""), str(locked))
ok("the non-active entry is not reported as locked",
   all("Invader" not in str(x.get("name")) for x in e.targets_in_bar()
       if x.get("is_active")), str(e.targets_in_bar()))

e2 = BarEye(tree([("Pithi Arrogator", False)]))
ok("targets present but none active -> no lock claimed",
   e2.locked_target() is None, str(e2.locked_target()))

e3 = BarEye(tree([]))
ok("empty bar -> no lock claimed", e3.locked_target() is None, str(e3.locked_target()))

# Live client source: TargetInBar.itemID is stable identity; its child
# ActiveTargetIndicator.state is 1 (UI_DISABLED) when active, 2 (UI_HIDDEN) otherwise.
actual_like = {"type": "TargetInBar", "attrs": {"itemID": 30000142}, "children": [
    {"type": "EveLabelSmall", "attrs": {"_setText": "Pithi Arrogator"}, "children": []},
    {"type": "Transform", "attrs": {}, "children": [
        {"type": "ActiveTargetIndicator", "attrs": {"state": 1}, "children": []}]}]}
id_eye = BarEye({"type": "UIRoot", "attrs": {}, "children": [actual_like]})
id_target = id_eye.locked_target()
ok("target-bar reads source object ID and active state",
   id_target is not None and id_target.get("object_id") == 30000142
   and id_target.get("is_active") is True, str(id_target))

# control.py verification now uses that reading instead of a hard-coded False.
from fila_bot import control  # noqa: E402
ok("lock verification passes when the bar shows an active target",
   control._verify_locked(e) is True)
ok("lock verification fails when nothing is active",
   control._verify_locked(e2) is False)
ok("lock verification requires exact requested object ID",
   control._verify_locked(id_eye, 30000142) is True
   and control._verify_locked(id_eye, 30000143) is False)
nested_target = BarEye({"type": "UIRoot", "attrs": {}, "children": [
    {"type": "TargetInBar", "attrs": {"_sr": {"itemID": 30000142}},
     "children": [{"type": "ActiveTargetIndicator", "attrs": {"state": 1},
                   "children": []}]}]})
ok("nested _sr itemID cannot verify locked target identity",
   control._verify_locked(nested_target, 30000142) is False)


def combat(**kw):
    w = {"docked": False, "location_known": True, "snapshot_valid": True,
         "connection_lost": False,
         "ship_health": {"shield": 1.0, "armor": 1.0, "structure": 1.0},
         "hostiles": [{"name": "Pithi Arrogator", "object_id": 101, "faction": "Guristas", "hull": "Pithi",
                       "priority": 1, "skip": False, "center": (1365, 457),
                       "distance": "12 km"}],
         "missions": ["The Roving Rogue Drones"],
         "active_mission_title": "The Roving Rogue Drones",
         "mission_type_label": "Encounter (Deadspace)", "mission_support": "combat",
         "has_active_mission": True, "mission_panel_observed": True,
         "gates": [], "beacons": [], "empty_xy": (396, 720),
         "drones_out": False, "afterburner_on": True,
         "weapons_active": None, "modules_observed": True,
         "propulsion_slot": 1, "propulsion_observed": None, "defense_modules": [],
         "locked_target": None, "target_bar_supported": True}
    w.update(kw)
    return w


clock = {"t": 400.0}

# Drones just launched, nothing locked yet -> launch, but never F.
m = SecurityMode(clock=lambda: clock["t"])
acts = m.tick(combat())
kinds = [a["do"] for a in acts]
ok("drones launch while no target is locked", "launch_drones" in kinds, str(kinds))
ok("no drone engage command without a lock", "engage_drones" not in kinds, str(kinds))
ok("lock is requested first", "lock_target" in kinds, str(kinds))

# An unsupported target-bar reader gets bounded exact-ID retries, never permission
# to fire or issue drone-attack orders.
clock_unknown = {"t": clock["t"]}
m_unknown = SecurityMode(clock=lambda: clock_unknown["t"])
unknown_acts = m_unknown.tick(combat(target_bar_supported=False, drones_out=True))
unknown_kinds = [a["do"] for a in unknown_acts]
ok("unreadable target bar requests a bounded lock, not offense",
   "lock_target" in unknown_kinds
   and not any(k in unknown_kinds for k in ("fire_weapons", "engage_drones")),
   str(unknown_kinds))
for _ in range(LOCK_MAX_ATTEMPTS + 2):
    clock_unknown["t"] += LOCK_RETRY_S + 0.5
    unknown_acts = m_unknown.tick(
        combat(target_bar_supported=False, drones_out=True))
    unknown_kinds = [a["do"] for a in unknown_acts]
    if m_unknown.phase == "BLOCKED":
        break
ok("unreadable target bar eventually blocks within retry bound",
   m_unknown.phase == "BLOCKED"
   and m_unknown._lock_attempts == LOCK_MAX_ATTEMPTS
   and "unreadable" in (m_unknown.blocked or "").lower()
   and not any(k in unknown_kinds for k in ("fire_weapons", "engage_drones")),
   f"{m_unknown.phase} {m_unknown._lock_attempts} {m_unknown.blocked} {unknown_kinds}")

# Still nothing active after the retry window -> try the lock again; no offensive
# action is authorized until the exact active object is read back.
clock["t"] += LOCK_RETRY_S + 0.5
acts = m.tick(combat(drones_out=True))
kinds = [a["do"] for a in acts]
ok("retries the lock on a new attempt window", "lock_target" in kinds, str(kinds))
ok("the drone order is not repeated every tick",
   kinds.count("engage_drones") <= 1, str(kinds))

# The client reports the lock -> engage the drones, exactly once.
clock["t"] += 1.0
acts = m.tick(combat(drones_out=True,
                     locked_target={"name": "Pithi Arrogator", "object_id": 101,
                                    "texts": ["Pithi Arrogator"], "is_active": True}))
kinds = [a["do"] for a in acts]
ok("an observed lock is accepted as a lock", "lock_target" not in kinds, str(kinds))
clock["t"] += 1.0
kinds = [a["do"] for a in m.tick(combat(drones_out=True,
                                       locked_target={"name": "Pithi Arrogator",
                                                      "texts": ["Pithi Arrogator"],
                                                      "is_active": True}))]
ok("the engage order is never repeated for the same target",
   "engage_drones" not in kinds, str(kinds))

# A same-name lock on a different object ID must not satisfy this target.
m_id = SecurityMode(clock=lambda: clock["t"])
acts = m_id.tick(combat(drones_out=True,
                        locked_target={"name": "Pithi Arrogator", "object_id": 202,
                                       "texts": ["Pithi Arrogator"], "is_active": True}))
by_kind = {a["do"]: a for a in acts}
ok("same name but wrong object ID does not verify lock",
   "lock_target" in by_kind and "fire_weapons" not in by_kind
   and "engage_drones" not in by_kind
   and by_kind["lock_target"].get("target_id") == 101, str(acts))
missing_id = SecurityMode(clock=lambda: clock["t"])
acts = missing_id.tick(combat(
    hostiles=[{"name": "Pithi Arrogator", "faction": "Guristas", "hull": "Pithi",
               "priority": 1, "skip": False, "center": (1365, 457),
               "distance": "12 km"}],
    locked_target={"name": "Pithi Arrogator", "texts": ["Pithi Arrogator"],
                   "is_active": True}))
ok("name-only overview and lock cannot authorize combat without itemID",
   missing_id.phase == "BLOCKED"
   and any(a["do"] == "blocked" for a in acts)
   and not any(a["do"] in ("lock_target", "approach_target", "close_distance",
                            "fire_weapons", "engage_drones", "launch_drones")
               for a in acts), str(acts))

# A lock on the WRONG thing is not good enough.
m2 = SecurityMode(clock=lambda: clock["t"])
acts = m2.tick(combat(locked_target={"name": "Caldari Navy Defense Post",
                                     "texts": ["Caldari Navy Defense Post"],
                                     "is_active": True}))
ok("a lock on a different object does not authorize the drone order",
   "engage_drones" not in [a["do"] for a in acts], str(acts))

# Never locks -> bounded, then blocks with the real reason.
m3 = SecurityMode(clock=lambda: clock["t"])
seen = []
for _ in range(LOCK_MAX_ATTEMPTS + 3):
    seen.append(m3.tick(combat(drones_out=True))[0]["do"])
    clock["t"] += LOCK_RETRY_S + 0.2
    if m3.phase == "BLOCKED":
        break
ok("persistent lock failure blocks with the target-bar reason",
   m3.phase == "BLOCKED" and "lock" in (m3.blocked or "").lower(),
   f"{m3.phase} {m3.blocked}")

# Live executor must refresh overview and resolve exact object ID before Ctrl-click.
from fila_bot.modes.live_security import LiveSecurityRunner
from fila_bot.modes import live_security as live_security_module

class FreshEye:
    dll = None
    rows = []
    def refresh(self):
        self.refresh_count = getattr(self, "refresh_count", 0) + 1
        return {"type": "UIRoot"}
    def overview_entries(self):
        return self.rows

fresh_eye = FreshEye()
fresh_eye.rows = [{"Name": "Pithi Arrogator", "object_id": 30000142,
                    "center": (44, 55)}]
runner = LiveSecurityRunner(fresh_eye, dry=True)
captured = {}
original_act_lock, original_act_approach, original_execute = (
    live_security_module.ctl.act_lock,
    live_security_module.ctl.act_approach,
    live_security_module.ctl.execute)
try:
    def capture_lock(xy, target_id=None):
        captured.update(xy=xy, target_id=target_id)
        return live_security_module.ctl.ActionSpec("test_lock", [])
    def capture_approach(xy):
        captured.update(xy=xy, approach=True)
        return live_security_module.ctl.ActionSpec("test_approach", [])
    def capture_execute(spec, **kwargs):
        return {"ok": True, "verified": False, "status": "SENT"}
    live_security_module.ctl.act_lock = capture_lock
    live_security_module.ctl.act_approach = capture_approach
    live_security_module.ctl.execute = capture_execute
    result = runner.apply([{"do": "lock_target", "at": (1, 2),
                            "target_id": 30000142, "target_name": "Pithi Arrogator"}])
    ok("live lock resolves current row by object ID, not stale coords",
       captured.get("xy") == (44, 55) and captured.get("target_id") == 30000142
       and fresh_eye.refresh_count == 1, str(captured))
    fresh_eye.rows = [{"Name": "Pithi Arrogator", "object_id": 999,
                       "center": (66, 77)}]
    captured.clear()
    result = runner.apply([{"do": "lock_target", "at": (1, 2),
                            "target_id": 30000142, "target_name": "Pithi Arrogator"}])
    ok("live lock refuses row with wrong object ID", not captured
       and result[0].get("status") == "IDENTITY_UNRESOLVED", str(result))
    fresh_eye.rows = [{"Name": "Pithi Arrogator", "object_id": 30000142,
                       "center": (80, 90)}]
    captured.clear()
    runner.apply([{"do": "close_distance", "at": (1, 2),
                   "target_id": 30000142, "target_name": "Pithi Arrogator"}])
    ok("live distance closing refreshes and resolves exact itemID",
       captured.get("xy") == (80, 90) and captured.get("approach") is True
       and fresh_eye.refresh_count == 3, str(captured))
finally:
    live_security_module.ctl.act_lock = original_act_lock
    live_security_module.ctl.act_approach = original_act_approach
    live_security_module.ctl.execute = original_execute

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
