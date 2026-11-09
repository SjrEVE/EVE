"""Test eye trên UI tree THẬT — fixture dump từ EVE client TQ (2026-11-09, Jita, undocked).

Fixture: tests/fixtures/ui_tree_ground_tq.json — dump thật đã cắt gọn (OverviewWindow +
4 entries, ShipUI + HPGauges/CapacitorContainer/SpeedGauge, SelectedItemWnd).
Mục đích: khoá schema THẬT (khác Sanderling cũ) để eye.py không tái phát tên sai.

Ground facts (2026-11-09):
- Overview window type = "OverviewWindow" (KHÔNG phải "OverView")
- Entry text ở OverviewLabel.attrs["_text"] (KHÔNG phải _setText)
- Selected item = "SelectedItemWnd" (KHÔNG phải "ActiveItem")
- HP gauge = ShipHudSpriteGauge._lastValue (float — DLL cũ trả null vì read_python_type_float rỗng)
- Speed = SpeedGauge → label _name=speedLabel, _setText="600 m/s"
- Cap = pmark._color là PyColor → CHƯA decode được → phải trả None (không đoán 0.0)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


def ground_eye() -> Eye:
    e = Eye.__new__(Eye)
    e.root = json.loads((ROOT / "tests/fixtures/ui_tree_ground_tq.json").read_text(encoding="utf-8"))
    e._pos = None
    e._pos_root = None
    return e


e = ground_eye()

# ---- HP: float thật ----
hp = e.ship_health()
ok("ground_hp_read", hp == {"shield": 1.0, "armor": 1.0, "structure": 1.0}, str(hp))

# ---- cap: PyColor chưa decode → None (KHÔNG bịa 0.0) ----
ok("ground_cap_unknown_none", e.capacitor_percent() is None, str(e.capacitor_percent()))

# ---- speed từ label ----
ok("ground_speed_label", e.speed_mps() == 600.0, str(e.speed_mps()))

# ---- overview: đúng window type + cột theo header ----
ov = e.overview_entries()
ok("ground_overview_count", len(ov) == 4, str(len(ov)))
first = ov[0]
ok("ground_overview_name", first.get("Name") == "Jita II - Sebiestor Tribe Trade Embassy", str(first.get("Name")))
ok("ground_overview_distance", first.get("Distance") == "808 km", str(first.get("Distance")))
ok("ground_overview_type_col", first.get("Type") == "Minmatar Trade Post", str(first.get("Type")))
ok("ground_overview_center_abs",
   700 < first["center"][0] < 1280 and 174 < first["center"][1] < 814, str(first["center"]))
ok("ground_overview_entries_sorted_by_y",
   all(ov[i]["center"][1] < ov[i + 1]["center"][1] for i in range(len(ov) - 1)),
   str([r["center"] for r in ov]))

# ---- selected item ----
sel = e.selected_item()
ok("ground_selected_item", sel is not None and "Jita" in (sel.get("name") or ""), str(sel))
ok("ground_selected_center_abs", sel and sel["center"][0] > 800, str(sel and sel["center"]))

# ---- abs_center cộng dồn cha: label sâu phải nằm trong entry ----
entry_node = None
for n in e.walk(e.root):
    if n.get("type") == "OverviewScrollEntry":
        entry_node = n
        break
label_node = None
for n in e.walk(entry_node):
    if n.get("type") == "OverviewLabel" and (n.get("attrs") or {}).get("_text"):
        label_node = n
        break
ex, ey = e.abs_center(entry_node)
lx, ly = e.abs_center(label_node)
ok("ground_abs_center_nested", ex <= lx <= ex + 428 and ey <= ly <= ey + 24, f"entry={ex},{ey} label={lx},{ly}")
ok("ground_center_xy_local_is_not_abs", Eye.center_xy(label_node)[0] < lx,
   f"local={Eye.center_xy(label_node)[0]} abs={lx}")

# ---- modules: tàu test chưa gắn module → [] (không bịa) ----
ok("ground_no_modules", e.module_buttons() == [], str(e.module_buttons()))

# ---- không có dialog ----
ok("ground_no_confirm", e.confirm_dialog() is None, str(e.confirm_dialog()))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
