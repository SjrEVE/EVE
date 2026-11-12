"""P0 SENSES regression — 5 mắt còn mù phải đọc được từ dump thật (không bịa).

Fixture = scratch/live_current_tree.json (IN_SPACE, HUD thật, copy sang tests/fixtures/
ui_tree_p0_senses_inspace.json). Gate của P0 trong SENSES_CHECKLIST:
  speed, cap, module state markers, locked-target bar, drone counts.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402


def eye_from(name: str) -> Eye:
    e = Eye.__new__(Eye)
    e.root = json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
    e._pos = e._pos_root = None
    return e


def ok(n, cond):
    if not cond:
        print(f"[FAIL] {n}")
        raise SystemExit(1)
    print(f"[PASS] {n}")


# --- Mắt tốc độ: speedLabel._setText '243 m/s' (ground từ dump HUD thật) ---
e = eye_from("ui_tree_p0_senses_inspace.json")
ok("speed_mps đọc được (243.0)", e.speed_mps() == 243.0)

# --- Mắt capacitor: pmark alpha decode PyColor -> % ---
cap = e.capacitor_percent()
ok(f"cap % đọc được ({cap})", cap is not None and 0.0 <= cap <= 100.0)

# --- Mắt health: 3 gauge _lastValue ---
hp = e.ship_health()
ok("health shield/armor/structure đọc được",
   hp and hp.get("shield") == 1.0 and hp.get("armor") == 1.0 and hp.get("structure") == 1.0)

# --- Mắt module: 14 nút, slot name + typeID + is_active là None (UNKNOWN) khi HUD không export ---
mods = e.module_buttons()
ok("module_buttons >= 10 nút", len(mods or []) >= 10)
slots = {m.get("slot") for m in mods}
ok("slot names ground (inFlightHighSlot1...)", any(s and "inFlightHighSlot1" in s for s in slots))
unknown_active = [m for m in mods if m.get("is_active") is None]
ok(f"module state UNKNOWN đúng nghĩa (None, không bịa False): {len(unknown_active)}/{len(mods)}",
   len(unknown_active) == len(mods))

# --- Mắt drone: in_space / in_bay tách riêng ---
dr = e.drones_observation()
ok("drone observation: observed + in_bay count", dr.get("observed") is True and dr.get("in_bay") == 10)

# --- Mắt locked target: dump không lock -> None (không bịa), targets_observable False ---
ok("locked_target None khi không lock (không bịa)", e.locked_target() is None)
ok("targets_observable False", e.targets_observable() is False)

# --- docked dump phải phân biệt: HUD docked là skeleton (speed text cũ) — extractor trả giá trị
# dump có (không invent), snapshot chỉ wire khi IN_SPACE (world_snapshot gate).
print("[PASS] P0 senses: 9 checks")
